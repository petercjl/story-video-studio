#!/usr/bin/env python3
"""Bind approved asset-package images into a Higgsfield prompt and Seedance input map."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from reference_request import split_draft_prompt


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def asset_record(package: Path, asset_id: str, image: Path) -> tuple[dict, str]:
    data = json.loads(package.read_text(encoding="utf-8"))
    if data.get("schema") != "ai-video-reference-asset-package":
        raise ValueError(f"Invalid asset package: {package}")
    matches = [a for a in data.get("assets", []) if a.get("asset_id") == asset_id]
    if len(matches) != 1:
        raise ValueError(f"Asset {asset_id} absent or ambiguous in {package}")
    asset = matches[0]
    if asset.get("status") != "approved" or asset.get("approval", {}).get("status") != "approved":
        raise ValueError(f"Asset {asset_id} is not user approved")
    output = asset.get("output")
    if not isinstance(output, str) or not output:
        raise ValueError(f"Asset {asset_id} package output must be a relative image path string")
    allowed = {output: None}
    for panel in asset.get("panel_spec", []):
        if panel.get("crop_path"):
            allowed[panel["crop_path"]] = panel.get("crop_sha256")
    relative = image.resolve().relative_to(package.parent.resolve()).as_posix()
    if relative not in allowed:
        raise ValueError(f"Image is not a package output or declared crop: {image}")
    actual = sha(image)
    expected = allowed[relative]
    if expected and expected != actual:
        raise ValueError(f"Crop hash mismatch: {image}")
    if relative == output:
        selected = [a for a in asset.get("attempts", []) if a.get("selected")]
        if selected and selected[-1].get("result", {}).get("sha256") != actual:
            raise ValueError(f"Master image hash mismatch: {image}")
    return asset, actual


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("request", "draft", "bindings", "output-dir"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--model", help="Optional exact model override. Omit it to let seedancecli route automatically.")
    p.add_argument("--duration", type=int, required=True)
    p.add_argument("--ratio", default="16:9")
    p.add_argument("--resolution", default="720p")
    args = p.parse_args(argv)
    try:
        request_path, bindings_path, draft_path = (x.resolve() for x in (args.request, args.bindings, args.draft))
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if request.get("schema") != "ai-video-reference-asset-request":
            raise ValueError("Invalid reference request")
        source = request.get("source", {})
        if source.get("prompt_sha256") and sha(draft_path) != source["prompt_sha256"]:
            raise ValueError("Draft prompt hash differs from request source")
        assets = {a["asset_id"]: a for a in request["assets"]}
        bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
        entries = bindings["images"]
        if not entries:
            raise ValueError("No images supplied")
        counts = {asset_id: sum(e.get("asset_id") == asset_id for e in entries) for asset_id in assets}
        output_dir = args.output_dir.resolve()
        out_names = ("seedance-with-assets.md", "seedance-provider-ready.txt", "input-map.json")
        if any((output_dir / name).exists() for name in out_names):
            raise ValueError("Output files already exist; use a new version directory")
        active, image_map, coverage, by_shot = [], [], set(), {}
        for index, entry in enumerate(entries, 1):
            asset_id = entry.get("asset_id")
            if asset_id not in assets:
                raise ValueError(f"Unknown asset ID: {asset_id}")
            package = (bindings_path.parent / entry["package"]).resolve()
            image = (bindings_path.parent / entry["path"]).resolve()
            if not package.is_file() or not image.is_file():
                raise ValueError(f"Missing binding file for {asset_id}")
            _, image_hash = asset_record(package, asset_id, image)
            classification = entry.get("classification")
            if classification not in {"human", "normal"}:
                raise ValueError(f"Invalid image classification: {asset_id}")
            if counts[asset_id] > 1 and "consumer_shots" not in entry:
                raise ValueError(f"Multiple views of {asset_id} require explicit per-image consumer_shots")
            shots = entry.get("consumer_shots", assets[asset_id]["consumer_shots"])
            if not shots or any(s not in assets[asset_id]["consumer_shots"] for s in shots):
                raise ValueError(f"Invalid shot use: {asset_id}")
            description = entry.get("description", assets[asset_id]["name"])
            tag = f"@image{index}"
            active.append(f"{tag}: Approved {description}. Follow this reference for its assigned visual role.")
            for shot in shots:
                by_shot.setdefault(shot, []).append(tag)
            image_map.append({
                "index": index, "provider_tag": f"图片{index}", "higgsfield_tag": tag,
                "asset_id": asset_id, "role": description, "classification": classification,
                "path": os.path.relpath(image, output_dir), "sha256": image_hash,
                "package": os.path.relpath(package, output_dir), "package_sha256": sha(package),
                "consumer_shots": shots,
            })
            coverage.add(asset_id)
        missing = set(assets) - coverage
        if missing:
            raise ValueError("Unbound assets: " + ", ".join(sorted(missing)))
        use = "\n".join(f"{shot}: {', '.join(tags)}" for shot, tags in by_shot.items())
        first, rest = split_draft_prompt(draft_path)
        final = first + "\n\nACTIVE REFERENCES\n" + "\n".join(active) + "\nReference use by shot:\n" + use + "\n\n" + rest
        provider = re.sub(r"@image(\d+)", lambda m: f"图片{m.group(1)}", final)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / out_names[0]).write_text("```text\n" + final + "\n```\n", encoding="utf-8")
        (output_dir / out_names[1]).write_text(provider + "\n", encoding="utf-8")
        manifest = {
            "schema": "story-video-input-map", "schema_version": "1.0.0",
            "status": "ready-for-dry-run", "provider": "ark",
            "duration_seconds": args.duration, "aspect_ratio": args.ratio, "resolution": args.resolution,
            "prompt_path": out_names[1], "prompt_sha256": sha(output_dir / out_names[1]),
            "source_request": os.path.relpath(request_path, output_dir), "source_request_sha256": sha(request_path),
            "images": image_map,
        }
        if args.model:
            manifest["model"] = args.model
        (output_dir / out_names[2]).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "output_dir": str(output_dir), "image_count": len(entries)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
