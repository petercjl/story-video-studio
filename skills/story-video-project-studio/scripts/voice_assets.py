"""Extract an approved speaker sample and register it as a project voice asset."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def inside(root: Path, relative: str) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes project: {relative}")
    return path


def write_new(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def source_video(root: Path, video_id: str) -> tuple[Path, str, dict]:
    state = json.loads((root / "video-project.json").read_text(encoding="utf-8"))
    video = state["videos"].get(video_id)
    if not video or video.get("status") not in {"accepted", "generated", "qa_failed"}:
        raise ValueError("Source video must be a downloaded project video")
    output = video.get("output")
    relative = output.get("path") if isinstance(output, dict) else output
    if not relative:
        raise ValueError("Source video has no output artifact")
    path = inside(root, relative)
    if not path.is_file():
        raise ValueError("Source video file is missing")
    recorded_sha = output.get("sha256") if isinstance(output, dict) else video.get("provider_raw_sha256")
    if recorded_sha and digest(path) != recorded_sha:
        raise ValueError("Source video hash mismatch")
    return path, relative, video


def validate(root: Path, voice_id: str) -> dict:
    state = json.loads((root / "video-project.json").read_text(encoding="utf-8"))
    voice = state["assets"].get(voice_id)
    if not voice or voice.get("kind") != "voice" or voice.get("status") != "approved":
        raise ValueError("Approved voice asset is missing from project state")
    package_ref = voice["approved_package"]
    package_path = inside(root, package_ref["path"] if isinstance(package_ref, dict) else package_ref)
    if not package_path.is_file():
        raise ValueError("Voice package is missing")
    if isinstance(package_ref, dict) and digest(package_path) != package_ref["sha256"]:
        raise ValueError("Voice package hash mismatch")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    matches = [item for item in package.get("assets", []) if item.get("asset_id") == voice_id]
    if len(matches) != 1 or matches[0].get("approval", {}).get("status") != "approved":
        raise ValueError("Voice package lacks speaker approval")
    item = matches[0]
    if voice.get("person_id") != item.get("person_id"):
        raise ValueError("Voice person_id differs from project registry")
    audio = inside(root, item["output"])
    if not audio.is_file() or digest(audio) != item["output_sha256"]:
        raise ValueError("Voice audio missing or hash mismatch")
    with wave.open(str(audio), "rb") as stream:
        duration = stream.getnframes() / stream.getframerate()
        if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or duration <= 0:
            raise ValueError("Voice reference must be nonempty mono 16-bit PCM WAV")
    source_ref = item["source_video"]
    source = inside(root, source_ref["path"] if isinstance(source_ref, dict) else source_ref)
    expected_source_sha = item.get("source_video_sha256") or (source_ref.get("sha256") if isinstance(source_ref, dict) else None)
    if not source.is_file() or not expected_source_sha or digest(source) != expected_source_sha:
        raise ValueError("Voice source video missing or hash mismatch")
    return {"ok": True, "voice_id": voice_id, "person_id": item["person_id"], "audio": item["output"], "sha256": item["output_sha256"], "duration_seconds": duration}


def extract(args: argparse.Namespace) -> dict:
    root = args.project_dir.expanduser().resolve()
    for name in (args.person_id, args.video_id):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
            raise ValueError(f"Invalid ID: {name}")
    if args.start < 0 or args.end <= args.start or not args.transcript.strip() or not args.approval_note.strip():
        raise ValueError("Provide a positive time window, transcript, and explicit speaker approval note")
    video_path, video_relative, video = source_video(root, args.video_id)
    duration = float(video.get("downloaded_duration_seconds") or video.get("delivery_duration_seconds") or 0)
    if duration and args.end > duration + 0.05:
        raise ValueError("Voice time window exceeds source video")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to extract voice audio")
    voice_id = f"VOICE-{args.person_id}"
    folder = root / "assets" / "voices" / args.person_id / f"v{args.version:02d}"
    audio = folder / "reference.wav"
    package_path = folder / "voice-package.json"
    record_path = folder / "project-record.json"
    for target in (audio, package_path, record_path):
        if target.exists():
            raise FileExistsError(f"Voice asset target already exists: {target}")
    folder.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-ss", str(args.start), "-to", str(args.end), "-i", str(video_path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(audio)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not audio.is_file():
        raise RuntimeError(f"ffmpeg voice extraction failed: {result.stderr.strip()[:500]}")
    with wave.open(str(audio), "rb") as stream:
        if stream.getnframes() == 0:
            raise ValueError("Extracted voice audio is empty")
    audio_rel = audio.relative_to(root).as_posix()
    package_rel = package_path.relative_to(root).as_posix()
    package = {
        "schema": "story-video-voice-asset", "schema_version": "1.0.0",
        "assets": [{
            "asset_id": voice_id, "kind": "voice", "person_id": args.person_id,
            "output": audio_rel, "output_sha256": digest(audio),
            "source_video_id": args.video_id, "source_video": video_relative,
            "source_video_sha256": digest(video_path),
            "source_time_window_seconds": [args.start, args.end],
            "transcript": args.transcript,
            "approval": {"status": "approved", "note": args.approval_note},
            "quality_note": args.quality_note or "",
        }],
    }
    write_new(package_path, package)
    record = {
        "status": "approved", "version": args.version, "name": f"{args.person_id} voice reference",
        "kind": "voice", "person_id": args.person_id, "asset_form": "extracted-speech-wav",
        "consumers": [video["segment_id"]], "approved_package": package_rel,
        "output": audio_rel, "source_video": video_relative,
        "source_time_window_seconds": [args.start, args.end],
        "qa": {"technical_result": "pass", "user_approval": args.approval_note},
    }
    write_new(record_path, record)
    project_script = Path(__file__).with_name("video_project.py")
    register = subprocess.run([sys.executable, str(project_script), "record", "--project-dir", str(root), "--kind", "asset", "--id", voice_id, "--data-file", str(record_path)], capture_output=True, text=True)
    if register.returncode:
        raise RuntimeError(f"Project voice registration failed; extracted files were preserved: {register.stdout.strip()} {register.stderr.strip()}")
    return validate(root, voice_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("extract")
    make.add_argument("--project-dir", type=Path, required=True)
    make.add_argument("--video-id", required=True)
    make.add_argument("--person-id", required=True)
    make.add_argument("--start", type=float, required=True)
    make.add_argument("--end", type=float, required=True)
    make.add_argument("--transcript", required=True)
    make.add_argument("--approval-note", required=True)
    make.add_argument("--quality-note")
    make.add_argument("--version", type=int, default=1)
    check = commands.add_parser("validate")
    check.add_argument("--project-dir", type=Path, required=True)
    check.add_argument("--voice-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "extract":
            if args.version < 1:
                raise ValueError("Version must be positive")
            output = extract(args)
        else:
            output = validate(args.project_dir.expanduser().resolve(), args.voice_id)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError, KeyError, RuntimeError, wave.Error) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
