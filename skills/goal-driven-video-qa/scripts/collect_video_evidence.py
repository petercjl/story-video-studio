#!/usr/bin/env python3
"""Collect deterministic, goal-selected evidence from a local video.

This script does not judge quality. It probes media metadata and extracts the
frames/audio requested by an Agent's QA plan, then writes a manifest describing
the actual coverage.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        fail(f"required executable not found on PATH: {name}")
    return path


def run(cmd: list[str], *, capture_stderr: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE if capture_stderr else subprocess.DEVNULL,
    )


def probe_video(ffprobe: str, video: Path) -> dict[str, Any]:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(video),
        ]
    )
    return json.loads(result.stdout)


def parse_fraction(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        if float(denominator) == 0:
            return None
        return float(numerator) / float(denominator)
    return float(value)


def stream_duration(stream: dict[str, Any]) -> float | None:
    if stream.get("duration") is not None:
        return float(stream["duration"])
    if stream.get("duration_ts") is not None:
        time_base = parse_fraction(stream.get("time_base"))
        if time_base is not None:
            return float(stream["duration_ts"]) * time_base
    return None


def video_sampling_duration(probe: dict[str, Any]) -> float:
    durations = [
        duration
        for stream in probe.get("streams", [])
        if stream.get("codec_type") == "video"
        for duration in [stream_duration(stream)]
        if duration is not None
    ]
    if durations:
        return max(durations)
    raw = probe.get("format", {}).get("duration")
    if raw is not None:
        return float(raw)
    fail("decodable video duration is unavailable")


def container_duration(probe: dict[str, Any]) -> float | None:
    raw = probe.get("format", {}).get("duration")
    return float(raw) if raw is not None else None


def frame_interval(probe: dict[str, Any]) -> float:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") != "video":
            continue
        fps = parse_fraction(stream.get("avg_frame_rate")) or parse_fraction(stream.get("r_frame_rate"))
        if fps and fps > 0:
            return 1.0 / fps
    return 0.04


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dense_window(value: str) -> tuple[float, float, float]:
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("dense window must be START:END:STEP")
    start, end, step = (float(item) for item in parts)
    if start < 0 or end <= start or step <= 0:
        raise argparse.ArgumentTypeError("require 0 <= START < END and STEP > 0")
    return start, end, step


def clean_timestamp(value: float, duration: float, safe_end: float) -> float:
    if value < 0 or value > duration:
        fail(f"timestamp {value:.3f}s falls outside 0-{duration:.3f}s")
    return min(value, safe_end)


def collect_timestamps(
    args: argparse.Namespace, duration: float, safe_end: float
) -> list[tuple[float, str]]:
    selected: dict[int, tuple[float, set[str]]] = {}

    def add(value: float, source: str) -> None:
        timestamp = clean_timestamp(value, duration, safe_end)
        key = round(timestamp * 1000)
        if key not in selected:
            selected[key] = (timestamp, set())
        selected[key][1].add(source)

    if args.uniform_count:
        for index in range(args.uniform_count):
            add(duration * (index + 0.5) / args.uniform_count, "uniform_count")

    if args.uniform_interval:
        current = 0.0
        while current < duration:
            add(current, "uniform_interval")
            current += args.uniform_interval
        add(safe_end, "uniform_interval")

    for timestamp in args.timestamp:
        add(timestamp, "explicit")

    for start, end, step in args.dense_window:
        if start > duration:
            fail(f"dense window starts after video ends: {start:.3f}s")
        current = start
        while current <= min(end, duration) + 1e-9:
            add(current, f"dense_window:{start:g}:{end:g}:{step:g}")
            current += step

    return [
        (timestamp, "+".join(sorted(sources)))
        for timestamp, sources in sorted(selected.values(), key=lambda item: item[0])
    ]


def extract_frame(ffmpeg: str, video: Path, timestamp: float, output: Path) -> None:
    run(
        [
            ffmpeg,
            "-v",
            "error",
            "-ss",
            f"{timestamp:.6f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-y",
            str(output),
        ]
    )


def extract_scene_frames(
    ffmpeg: str, video: Path, output_dir: Path, threshold: float
) -> list[dict[str, Any]]:
    pattern = output_dir / "scene_%04d.jpg"
    command = [
        ffmpeg,
        "-v",
        "info",
        "-i",
        str(video),
        "-vf",
        f"select='gt(scene,{threshold})',showinfo",
        "-fps_mode",
        "vfr",
        "-q:v",
        "2",
        "-y",
        str(pattern),
    ]
    result = run(command, capture_stderr=True)
    times = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    files = sorted(output_dir.glob("scene_*.jpg"))
    return [
        {
            "kind": "scene_change",
            "timestamp": times[index] if index < len(times) else None,
            "path": str(path.relative_to(output_dir.parent)),
        }
        for index, path in enumerate(files)
    ]


def extract_audio(ffmpeg: str, video: Path, output: Path) -> None:
    run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-y",
            str(output),
        ]
    )


def create_contact_sheet(
    ffmpeg: str, frames_dir: Path, output: Path, columns: int, frame_count: int
) -> None:
    rows = math.ceil(frame_count / columns)
    run(
        [
            ffmpeg,
            "-v",
            "error",
            "-pattern_type",
            "glob",
            "-i",
            str(frames_dir / "frame_*.jpg"),
            "-vf",
            f"scale=360:-1,tile={columns}x{rows}:padding=4:margin=4",
            "-frames:v",
            "1",
            "-y",
            str(output),
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe a video and extract only the evidence selected by a QA plan."
    )
    parser.add_argument("video", type=Path, help="Local input video.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New or empty evidence directory.")
    parser.add_argument("--uniform-count", type=int, default=0, help="Centered samples across duration.")
    parser.add_argument("--uniform-interval", type=float, default=0, help="Sample every N seconds.")
    parser.add_argument("--timestamp", type=float, action="append", default=[], help="Exact timestamp; repeatable.")
    parser.add_argument(
        "--dense-window",
        type=parse_dense_window,
        action="append",
        default=[],
        metavar="START:END:STEP",
        help="Dense sample range; repeatable.",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=None,
        help="Extract scene-change frames using an ffmpeg threshold, commonly 0.2-0.5.",
    )
    parser.add_argument("--extract-audio", action="store_true", help="Extract mono 16 kHz PCM WAV.")
    parser.add_argument(
        "--contact-sheet-columns",
        type=int,
        default=0,
        help="Create contact_sheet.jpg with this many columns; 0 disables it.",
    )
    parser.add_argument("--skip-hash", action="store_true", help="Skip source SHA-256 for very large files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    video = args.video.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not video.is_file():
        fail(f"video not found: {video}")
    if args.uniform_count < 0 or args.uniform_interval < 0:
        fail("sampling values must be non-negative")
    if args.contact_sheet_columns < 0:
        fail("contact sheet columns must be non-negative")
    if args.scene_threshold is not None and not 0 <= args.scene_threshold <= 1:
        fail("scene threshold must be between 0 and 1")
    if output_dir.exists() and any(output_dir.iterdir()):
        fail(f"output directory is not empty: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    ffprobe = require_tool("ffprobe")
    ffmpeg = require_tool("ffmpeg")
    probe = probe_video(ffprobe, video)
    duration = video_sampling_duration(probe)
    safe_end = max(0.0, duration - frame_interval(probe))
    timestamps = collect_timestamps(args, duration, safe_end)
    if args.contact_sheet_columns and not timestamps:
        fail("contact sheet requested but no frame sampling was selected")

    artifacts: list[dict[str, Any]] = []
    for index, (timestamp, source) in enumerate(timestamps, start=1):
        name = f"frame_{index:05d}_t{timestamp:010.3f}.jpg"
        path = frames_dir / name
        extract_frame(ffmpeg, video, timestamp, path)
        artifacts.append(
            {
                "kind": "frame",
                "timestamp": round(timestamp, 6),
                "selection": source,
                "path": str(path.relative_to(output_dir)),
            }
        )

    if args.scene_threshold is not None:
        scene_dir = output_dir / "scene_frames"
        scene_dir.mkdir(exist_ok=True)
        artifacts.extend(extract_scene_frames(ffmpeg, video, scene_dir, args.scene_threshold))

    if args.extract_audio:
        audio_path = output_dir / "audio_mono_16khz.wav"
        extract_audio(ffmpeg, video, audio_path)
        artifacts.append({"kind": "audio", "path": audio_path.name})

    if args.contact_sheet_columns:
        contact_sheet = output_dir / "contact_sheet.jpg"
        create_contact_sheet(
            ffmpeg,
            frames_dir,
            contact_sheet,
            args.contact_sheet_columns,
            len(timestamps),
        )
        artifacts.append({"kind": "contact_sheet", "path": contact_sheet.name})

    manifest = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "path": str(video),
            "size_bytes": video.stat().st_size,
            "sha256": None if args.skip_hash else sha256(video),
        },
        "duration_seconds": duration,
        "container_duration_seconds": container_duration(probe),
        "safe_last_frame_timestamp": safe_end,
        "probe": probe,
        "request": {
            "uniform_count": args.uniform_count,
            "uniform_interval": args.uniform_interval,
            "timestamps": args.timestamp,
            "dense_windows": [list(item) for item in args.dense_window],
            "scene_threshold": args.scene_threshold,
            "extract_audio": args.extract_audio,
            "contact_sheet_columns": args.contact_sheet_columns,
        },
        "coverage": {
            "selected_frame_count": len(timestamps),
            "scene_frame_count": sum(item["kind"] == "scene_change" for item in artifacts),
            "audio_extracted": args.extract_audio,
            "contact_sheet_created": bool(args.contact_sheet_columns),
        },
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(manifest_path),
                "duration_seconds": duration,
                "selected_frames": len(timestamps),
                "scene_frames": manifest["coverage"]["scene_frame_count"],
                "audio_extracted": args.extract_audio,
                "contact_sheet_created": bool(args.contact_sheet_columns),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
