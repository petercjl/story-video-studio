#!/usr/bin/env python3
"""Convert a shot-derived reference request to an asset studio work order."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--asset-id", action="append")
    mode.add_argument("--asset-name", action="append")
    args = p.parse_args(argv)
    try:
        source_path = args.input.resolve()
        request = json.loads(source_path.read_text(encoding="utf-8"))
        if request.get("schema") != "ai-video-reference-asset-request" or str(request.get("schema_version", "")).split(".")[0] not in {"0", "1"}:
            raise ValueError("Unsupported reference request schema")
        assets = request.get("assets")
        if not isinstance(assets, list) or not assets:
            raise ValueError("No assets in request")
        ids = [a.get("asset_id") for a in assets]
        names = [a.get("name") for a in assets]
        if None in ids or len(set(ids)) != len(ids) or None in names or len(set(names)) != len(names):
            raise ValueError("Asset IDs and exact names must be unique")
        for key in ("story", "prompt"):
            rel = request.get("source", {}).get(f"{key}_path")
            expected = request.get("source", {}).get(f"{key}_sha256")
            if rel and expected:
                candidate = (source_path.parent / rel).resolve()
                if not candidate.is_file() or sha(candidate) != expected:
                    raise ValueError(f"Source {key} missing or hash mismatch")
        if args.all:
            selected = assets
        else:
            key, requested = ("asset_id", args.asset_id) if args.asset_id else ("name", args.asset_name)
            selected = [a for a in assets if a.get(key) in requested]
            missing = set(requested) - {a[key] for a in selected}
            if missing:
                raise ValueError("Unknown selection: " + ", ".join(sorted(missing)))
        normalized = []
        for item in selected:
            if item.get("kind") not in {"character", "environment", "prop", "style", "keyframe"}:
                raise ValueError(f"Invalid kind: {item.get('asset_id')}")
            if not item.get("asset_form") or not item.get("brief") or not item.get("consumer_shots"):
                raise ValueError(f"Incomplete asset: {item.get('asset_id')}")
            normalized.append({
                "asset_id": item["asset_id"], "source_task_id": item["asset_id"], "source_name": item["name"],
                "name": item["name"], "kind": item["kind"], "asset_form": item["asset_form"],
                "purpose": item.get("purpose", ""), "consumers": item["consumer_shots"],
                "definition_scope": item["brief"], "dependencies": item.get("dependencies", []),
                "references": item.get("references", []), "acceptance_checks": item.get("acceptance_checks", []),
                "panel_roles": item.get("panel_roles", []), "approval_required": item.get("approval_required", True),
            })
        result = {
            "schema": "ai-video-reference-asset-work-order", "schema_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": {"schema": request["schema"], "schema_version": request["schema_version"], "path": str(source_path), "sha256": sha(source_path)},
            "project": {"title": request.get("project", "")},
            "selection": {"asset_ids": [item["asset_id"] for item in normalized]},
            "assets": normalized, "unresolved_assets": [],
        }
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps({"ok": True, "path": str(output), "asset_count": len(normalized)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
