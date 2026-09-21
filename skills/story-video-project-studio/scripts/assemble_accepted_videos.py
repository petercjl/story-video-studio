#!/usr/bin/env python3
"""Plan and build a frame-recorded assembly from accepted current clips."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


SCHEMA = "story-video-assembly-plan"
VERSION = "1.0.0"


class AssemblyError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path: Path, value: str) -> None:
    if path.exists():
        raise AssemblyError(f"Refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def require_tools() -> None:
    for name in ("ffmpeg", "ffprobe"):
        if not shutil.which(name):
            raise AssemblyError(f"Required executable not found: {name}")


def probe(path: Path) -> dict:
    result = run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels",
        "-of", "json", str(path),
    ])
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video:
        raise AssemblyError(f"No video stream: {path}")
    fps = Fraction(video.get("r_frame_rate") or "0/1")
    if fps <= 0:
        raise AssemblyError(f"Invalid frame rate: {path}")
    duration = float(data.get("format", {}).get("duration") or 0)
    frames_raw = video.get("nb_frames")
    frames = int(frames_raw) if str(frames_raw).isdigit() else round(duration * float(fps))
    if frames <= 0:
        raise AssemblyError(f"Invalid frame count: {path}")
    return {
        "duration_seconds": duration,
        "frames": frames,
        "fps": f"{fps.numerator}/{fps.denominator}",
        "width": int(video["width"]),
        "height": int(video["height"]),
        "video_codec": video.get("codec_name"),
        "audio": bool(audio),
        "audio_codec": audio.get("codec_name") if audio else None,
        "sample_rate": int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None,
        "channels": int(audio["channels"]) if audio and audio.get("channels") else None,
    }


def project_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise AssemblyError(f"Path escapes project: {value}")
    return path


def load_project(root: Path) -> dict:
    state = root / "video-project.json"
    if not state.is_file():
        raise AssemblyError(f"Project state missing: {state}")
    return json.loads(state.read_text(encoding="utf-8"))


def accepted_sources(root: Path, state: dict) -> list[dict]:
    clips: list[dict] = []
    for segment_id, segment in state.get("segments", {}).items():
        video_id = segment.get("current_video_id")
        video = state.get("videos", {}).get(video_id)
        if not video_id or not video:
            raise AssemblyError(f"Segment {segment_id} has no current video")
        if video.get("segment_id") != segment_id or video.get("status") != "accepted" or video.get("review_status") == "needs_review":
            raise AssemblyError(f"Segment {segment_id} current video is not accepted: {video_id}")
        output = video.get("output")
        if not isinstance(output, dict) or not output.get("path") or not output.get("sha256"):
            raise AssemblyError(f"Accepted video lacks recorded output artifact: {video_id}")
        path = project_path(root, output["path"])
        if not path.is_file() or sha256(path) != output["sha256"]:
            raise AssemblyError(f"Accepted video missing or changed: {video_id}")
        media = probe(path)
        clips.append({
            "segment_id": segment_id,
            "video_id": video_id,
            "source": output["path"],
            "source_sha256": output["sha256"],
            "source_probe": media,
            "in_frame": 0,
            "out_frame": media["frames"],
        })
    if not clips:
        raise AssemblyError("Project has no segments")
    return clips


def cmd_plan(args: argparse.Namespace) -> dict:
    require_tools()
    root = args.project_dir.resolve()
    clips = accepted_sources(root, load_project(root))
    first = clips[0]["source_probe"]
    plan = {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "project_state_sha256": sha256(root / "video-project.json"),
        "transition_policy": "hard-cut-with-reviewed-frame-trims",
        "output": {"width": first["width"], "height": first["height"], "fps": first["fps"], "audio_sample_rate": 48000},
        "clips": clips,
    }
    write_new(args.output_plan.resolve(), json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    return {"ok": True, "plan": str(args.output_plan.resolve()), "clips": len(clips)}


def validate_plan(root: Path, plan: dict) -> tuple[list[dict], dict]:
    if plan.get("schema") != SCHEMA or str(plan.get("schema_version", "")).split(".")[0] != "1":
        raise AssemblyError("Unsupported assembly plan")
    state = load_project(root)
    current = {c["segment_id"]: c for c in accepted_sources(root, state)}
    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        raise AssemblyError("Assembly plan clips must be a non-empty list")
    if [c.get("segment_id") for c in clips] != list(state.get("segments", {}).keys()):
        raise AssemblyError("Assembly clips do not match project segment order")
    checked: list[dict] = []
    for clip in clips:
        base = current.get(clip.get("segment_id"))
        if not base or clip.get("video_id") != base["video_id"] or clip.get("source") != base["source"] or clip.get("source_sha256") != base["source_sha256"]:
            raise AssemblyError(f"Plan source is stale or not current: {clip.get('segment_id')}")
        start, end = clip.get("in_frame"), clip.get("out_frame")
        if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > base["source_probe"]["frames"]:
            raise AssemblyError(f"Invalid frame window for {clip.get('segment_id')}: [{start}, {end})")
        checked.append({**base, "in_frame": start, "out_frame": end})
    settings = plan.get("output", {})
    for key in ("width", "height", "fps", "audio_sample_rate"):
        if key not in settings:
            raise AssemblyError(f"Assembly output setting missing: {key}")
    if int(settings["width"]) <= 0 or int(settings["height"]) <= 0 or Fraction(str(settings["fps"])) <= 0 or int(settings["audio_sample_rate"]) <= 0:
        raise AssemblyError("Invalid assembly output settings")
    return checked, settings


def make_join_sheet(video: Path, join_frame: int, output: Path) -> None:
    frames = [max(0, join_frame - 2), max(0, join_frame - 1), join_frame, join_frame + 1]
    expression = "+".join(f"eq(n\\,{frame})" for frame in frames)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", f"select={expression},scale=270:-2,tile=4x1", "-frames:v", "1", "-update", "1", "-y", str(output),
    ])


def cmd_build(args: argparse.Namespace) -> dict:
    require_tools()
    root = args.project_dir.resolve()
    output, manifest, qa_dir = args.output.resolve(), args.manifest.resolve(), args.qa_dir.resolve()
    for path in (output, manifest, qa_dir):
        if path.exists():
            raise AssemblyError(f"Refusing to overwrite: {path}")
    plan_path = args.plan.resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    clips, settings = validate_plan(root, plan)
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs: list[str] = []
    filters: list[str] = []
    concat_inputs: list[str] = []
    out_fps = Fraction(str(settings["fps"]))
    sample_rate = int(settings["audio_sample_rate"])
    effective: list[dict] = []
    cumulative_frames = 0
    joins: list[int] = []
    for index, clip in enumerate(clips):
        path = project_path(root, clip["source"])
        inputs += ["-i", str(path)]
        source_fps = Fraction(clip["source_probe"]["fps"])
        start, end = clip["in_frame"], clip["out_frame"]
        start_seconds, end_seconds = float(Fraction(start, 1) / source_fps), float(Fraction(end, 1) / source_fps)
        filters.append(
            f"[{index}:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS,"
            f"scale={int(settings['width'])}:{int(settings['height'])}:force_original_aspect_ratio=decrease,"
            f"pad={int(settings['width'])}:{int(settings['height'])}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={out_fps.numerator}/{out_fps.denominator},format=yuv420p[v{index}]"
        )
        if clip["source_probe"]["audio"]:
            filters.append(f"[{index}:a]atrim=start={start_seconds:.9f}:end={end_seconds:.9f},asetpts=PTS-STARTPTS,aresample={sample_rate}[a{index}]")
        else:
            filters.append(f"anullsrc=r={sample_rate}:cl=stereo,atrim=duration={end_seconds-start_seconds:.9f},asetpts=PTS-STARTPTS[a{index}]")
        concat_inputs += [f"[v{index}]", f"[a{index}]"]
        output_frames = round((end_seconds - start_seconds) * float(out_fps))
        cumulative_frames += output_frames
        if index < len(clips) - 1:
            joins.append(cumulative_frames)
        effective.append({
            "segment_id": clip["segment_id"], "video_id": clip["video_id"], "source": clip["source"],
            "source_sha256": clip["source_sha256"], "source_fps": clip["source_probe"]["fps"],
            "source_window_frames": [start, end], "source_window_seconds": [start_seconds, end_seconds],
            "output_frames": output_frames,
        })
    filters.append("".join(concat_inputs) + f"concat=n={len(clips)}:v=1:a=1[outv][outa]")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-crf", str(args.crf), "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
    run(command)
    output_probe = probe(output)
    qa_dir.mkdir(parents=True)
    sheets: list[str] = []
    for index, frame in enumerate(joins, 1):
        sheet = qa_dir / f"join-{index:02d}-frame-{frame}.jpg"
        make_join_sheet(output, frame, sheet)
        sheets.append(sheet.relative_to(root).as_posix() if sheet.is_relative_to(root) else str(sheet))
    record = {
        "schema": "story-video-assembly-manifest", "schema_version": VERSION,
        "plan": {"path": plan_path.relative_to(root).as_posix() if plan_path.is_relative_to(root) else str(plan_path), "sha256": sha256(plan_path)},
        "clips": effective, "join_frames": joins, "qa_sheets": sheets,
        "output": {"path": output.relative_to(root).as_posix() if output.is_relative_to(root) else str(output), "sha256": sha256(output), "bytes": output.stat().st_size, "probe": output_probe},
    }
    write_new(manifest, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return {"ok": True, "output": str(output), "manifest": str(manifest), "clips": len(clips), "join_frames": joins}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--project-dir", type=Path, required=True)
    plan.add_argument("--output-plan", type=Path, required=True)
    build = sub.add_parser("build")
    build.add_argument("--project-dir", type=Path, required=True)
    build.add_argument("--plan", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--qa-dir", type=Path, required=True)
    build.add_argument("--crf", type=int, default=18)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = cmd_plan(args) if args.command == "plan" else cmd_build(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (AssemblyError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
