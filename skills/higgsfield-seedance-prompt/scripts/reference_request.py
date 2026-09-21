#!/usr/bin/env python3
"""Validate and select Higgsfield-derived reference requests."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


PROMPT_BLOCKS = (
    "LOCATION MAP", "FIRST FRAME / BLOCKING", "FORMAT MODE", "OPTICS", "CAMERA",
    "ACTION", "PERFORMANCE", "PHYSICS", "LIGHTING", "COLOR GRADE", "WARDROBE",
    "AUDIO", "STYLE", "OUTPUT SETTINGS", "POSITIVE LOCKS",
)


def split_draft_prompt(path: Path) -> tuple[str, str]:
    """Find the scene-context block without depending on blank-line formatting."""
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("```text") and text.endswith("```"):
        text = text[7:-3].strip()
    if not text.startswith("SCENE CONTEXT\n"):
        raise ValueError("First-pass draft must start with SCENE CONTEXT")
    if re.search(r"(?m)^ACTIVE REFERENCES\s*$", text):
        raise ValueError("First-pass draft must leave ACTIVE REFERENCES to the binding pass")
    block_pattern = r"(?m)^(?:" + "|".join(re.escape(block) for block in PROMPT_BLOCKS) + r")\s*$"
    match = re.search(block_pattern, text[len("SCENE CONTEXT\n"):])
    if not match:
        raise ValueError("First-pass draft needs a block after SCENE CONTEXT")
    split_at = len("SCENE CONTEXT\n") + match.start()
    first, rest = text[:split_at].strip(), text[split_at:].strip()
    if not first.removeprefix("SCENE CONTEXT").strip():
        raise ValueError("SCENE CONTEXT is empty")
    return first, rest


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "ai-video-reference-asset-request" or data.get("schema_version", "").split(".")[0] not in {"0", "1"}:
        raise ValueError("Unsupported reference request schema")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("assets must be a non-empty array")
    ids, names = set(), set()
    for item in assets:
        asset_id, name = item.get("asset_id"), item.get("name")
        if not isinstance(asset_id, str) or not asset_id or asset_id in ids:
            raise ValueError(f"Invalid or duplicate asset_id: {asset_id}")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError(f"Invalid or duplicate asset name: {name}")
        if item.get("kind") not in {"character", "environment", "prop", "style", "keyframe"}:
            raise ValueError(f"Invalid kind for {asset_id}")
        if not item.get("asset_form") or not item.get("brief") or not item.get("consumer_shots"):
            raise ValueError(f"Incomplete asset: {asset_id}")
        ids.add(asset_id); names.add(name)
    for item in assets:
        for dep in item.get("dependencies", []):
            if dep.get("asset_id") not in ids:
                raise ValueError(f"Unknown dependency for {item['asset_id']}: {dep.get('asset_id')}")
    source = data.get("source", {})
    if data["schema_version"].startswith("1"):
        for field in ("segment_id", "story_path", "story_sha256", "prompt_path", "prompt_sha256"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"1.x request requires source.{field}")
    for key in ("story", "prompt"):
        rel = source.get(f"{key}_path")
        expected = source.get(f"{key}_sha256")
        if rel and expected:
            candidate = (path.parent / rel).resolve()
            if not candidate.is_file() or sha(candidate) != expected:
                raise ValueError(f"Source {key} missing or hash mismatch")
            if key == "prompt" and data["schema_version"].startswith("1"):
                split_draft_prompt(candidate)
    shots = data.get("shots")
    if data["schema_version"].startswith("1"):
        if not isinstance(shots, list) or not shots:
            raise ValueError("1.x request requires shots")
        shot_ids = [shot.get("id") for shot in shots]
        if len(set(shot_ids)) != len(shot_ids) or any(not s for s in shot_ids):
            raise ValueError("Invalid shot IDs")
        for item in assets:
            if any(shot not in shot_ids for shot in item["consumer_shots"]):
                raise ValueError(f"Unknown consumer shot in {item['asset_id']}")
    return data


def select(data: dict, ids: list[str], names: list[str], all_items: bool) -> list[dict]:
    if sum(bool(x) for x in (ids, names, all_items)) != 1:
        raise ValueError("Select exactly one mode: --all, --asset-id, or --asset-name")
    assets = data["assets"]
    if all_items:
        return assets
    key, wanted = ("asset_id", ids) if ids else ("name", names)
    found = [a for a in assets if a[key] in wanted]
    missing = set(wanted) - {a[key] for a in found}
    if missing:
        raise ValueError("Unknown selection: " + ", ".join(sorted(missing)))
    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("validate", "select"):
        q = sub.add_parser(command)
        q.add_argument("--input", type=Path, required=True)
        if command == "select":
            q.add_argument("--all", action="store_true")
            q.add_argument("--asset-id", action="append", default=[])
            q.add_argument("--asset-name", action="append", default=[])
    args = p.parse_args(argv)
    try:
        data = load(args.input.resolve())
        result = {"ok": True, "schema_version": data["schema_version"], "asset_count": len(data["assets"])}
        if args.command == "select":
            result["assets"] = select(data, args.asset_id, args.asset_name, args.all)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
