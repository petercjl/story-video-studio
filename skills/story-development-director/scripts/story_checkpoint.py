#!/usr/bin/env python3
"""Validate and approve a story-development@1 checkpoint."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


def text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value


def validate(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema") != "story-development" or data.get("schema_version") != 1:
        raise ContractError("schema must be story-development version 1")
    for field in ("story_id", "title", "premise", "story_text", "emotional_intent", "opening_question"):
        text(data.get(field), field)
    events = data.get("visible_events")
    if not isinstance(events, list) or not events:
        raise ContractError("visible_events must be a non-empty array")
    for index, event in enumerate(events):
        text(event, f"visible_events[{index}]")
    for field in ("continuity_facts", "logic_decisions", "dialogue", "unresolved"):
        if not isinstance(data.get(field), list):
            raise ContractError(f"{field} must be an array")
    for index, item in enumerate(data["logic_decisions"]):
        if not isinstance(item, dict):
            raise ContractError(f"logic_decisions[{index}] must be an object")
        for field in ("topic", "decision", "reason"):
            text(item.get(field), f"logic_decisions[{index}].{field}")
    for index, item in enumerate(data["dialogue"]):
        if not isinstance(item, dict):
            raise ContractError(f"dialogue[{index}] must be an object")
        text(item.get("speaker"), f"dialogue[{index}].speaker")
        if item.get("mode") not in {"spoken", "inner_voice", "narration", "on_screen_text"}:
            raise ContractError(f"dialogue[{index}].mode is invalid")
        text(item.get("text"), f"dialogue[{index}].text")
    duration = data.get("duration")
    if not isinstance(duration, dict) or duration.get("status") not in {"deferred", "estimated", "approved"}:
        raise ContractError("duration.status must be deferred, estimated, or approved")
    natural = duration.get("natural_range_seconds")
    if not isinstance(natural, list) or len(natural) != 2 or not all(isinstance(value, (int, float)) and value > 0 for value in natural) or natural[0] > natural[1]:
        raise ContractError("duration.natural_range_seconds must be an ascending positive pair")
    if duration["status"] == "approved" and not isinstance(duration.get("approved_seconds"), (int, float)):
        raise ContractError("approved duration requires approved_seconds")
    text(duration.get("basis"), "duration.basis")
    review = data.get("review")
    if not isinstance(review, dict) or review.get("status") not in {"draft", "approved"}:
        raise ContractError("review.status must be draft or approved")
    digest = hashlib.sha256(data["story_text"].encode("utf-8")).hexdigest()
    if review["status"] == "approved":
        if review.get("story_sha256") != digest:
            raise ContractError("approved review.story_sha256 does not match story_text")
        text(review.get("approved_at"), "review.approved_at")
    return {"ok": True, "story_id": data["story_id"], "review_status": review["status"], "story_sha256": digest, "duration_status": duration["status"]}


def load(filename: Path) -> dict[str, Any]:
    try:
        value = json.loads(filename.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"file not found: {filename}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ContractError("document root must be an object")
    return value


def atomic_write(filename: Path, data: dict[str, Any]) -> None:
    temporary = filename.with_name(f".{filename.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, filename)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("validate", "approve"))
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        data = load(args.file)
        if args.action == "approve":
            data.setdefault("review", {})
            data["review"].update({
                "status": "approved",
                "approved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "story_sha256": hashlib.sha256(text(data.get("story_text"), "story_text").encode("utf-8")).hexdigest(),
            })
            atomic_write(args.file, data)
        result = validate(data)
    except ContractError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
