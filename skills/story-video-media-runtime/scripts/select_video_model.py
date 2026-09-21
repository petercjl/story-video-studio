#!/usr/bin/env python3
"""Select a semantic Seedance route and a platform-specific model value."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

POLICY = "story-video-seedance-route-2026-09-21"
SEALSEEK_ALIASES = {"seedance-2.0": "doubao-seedance-2-0-fast", "seedance-2.5": "doubao-seedance-2-5"}


def fail(code: str, message: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": message}, "policy": POLICY}


def select(platform: str, request: dict) -> dict:
    explicit = request.get("explicit_model")
    duration = float(request.get("duration_seconds") or 0)
    resolution = str(request.get("resolution") or "").lower()
    task_type = str(request.get("task_type") or "generate").lower()
    signals: list[str] = []
    for key in ("audio_only", "exceeds_2_0_reference_limits", "timestamped_segments", "spoken_performance", "multi_shot_continuity"):
        if request.get(key) is True:
            signals.append(key)
    if duration:
        signals.append(f"duration_seconds={duration:g}")
    if resolution:
        signals.append(f"resolution={resolution}")
    if task_type != "generate":
        signals.append(f"task_type={task_type}")

    if explicit:
        return {"ok": True, "selected_family": "explicit", "selected_model": explicit, "policy": POLICY, "reason": "explicit user override", "signals": signals}
    if duration > 15 and resolution == "1080p":
        return fail("FEATURE_UNSUPPORTED", "No verified route satisfies duration over 15 seconds together with 1080p.")
    if duration > 15:
        family, reason = "seedance-2.5", "duration exceeds Seedance 2.0 limit"
    elif request.get("audio_only") is True:
        family, reason = "seedance-2.5", "audio-only generation"
    elif request.get("exceeds_2_0_reference_limits") is True:
        family, reason = "seedance-2.5", "reference set exceeds Seedance 2.0 limits"
    elif task_type in {"seedance-2.5", "2.5"}:
        family, reason = "seedance-2.5", "explicit Seedance 2.5 task type"
    elif resolution == "1080p":
        family, reason = "seedance-2.0", "1080p requirement"
    elif task_type in {"edit", "editing"}:
        family, reason = "seedance-2.0", "video editing spatial-fidelity policy"
    elif task_type in {"extend", "extension"}:
        family, reason = "seedance-2.5", "video extension"
    elif request.get("timestamped_segments") is True:
        family, reason = "seedance-2.5", "timestamped segment control"
    elif request.get("spoken_performance") is True:
        family, reason = "seedance-2.5", "spoken performance"
    elif request.get("multi_shot_continuity") is True:
        family, reason = "seedance-2.0", "explicit multi-shot continuity"
    else:
        family, reason = "seedance-2.5", "ordinary generation fallback"

    if platform == "codex":
        model = "auto"
    elif platform == "sealseek-openclaw":
        model = SEALSEEK_ALIASES[family]
    else:
        return fail("CAPABILITY_UNAVAILABLE", f"Unsupported platform: {platform}")
    return {"ok": True, "selected_family": family, "selected_model": model, "policy": POLICY, "reason": reason, "signals": signals}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=["codex", "sealseek-openclaw"])
    parser.add_argument("--input", required=True, help="JSON request path, or - for stdin")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    result = select(args.platform, json.loads(raw))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
