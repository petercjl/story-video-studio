#!/usr/bin/env python3
"""Mix a generated BGM master beneath an accepted complete-film soundtrack."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCHEMA = "story-video-final-mix-plan"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def probe(path: Path) -> dict:
    result = run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ])
    data = json.loads(result.stdout)
    video = next((stream for stream in data["streams"] if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in data["streams"] if stream.get("codec_type") == "audio"), None)
    duration = float(data["format"].get("duration") or (video or audio or {}).get("duration") or 0)
    return {
        "duration_seconds": duration,
        "video": None if video is None else {
            "codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"),
            "fps": video.get("avg_frame_rate"), "frames": int(video["nb_frames"]) if video.get("nb_frames") else None,
        },
        "audio": None if audio is None else {
            "codec": audio.get("codec_name"), "sample_rate": int(audio["sample_rate"]),
            "channels": audio.get("channels"),
        },
    }


def resolve(plan_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (plan_path.parent / path).resolve()


def require_input(plan_path: Path, item: dict, label: str) -> Path:
    path = resolve(plan_path, item["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    actual = sha256(path)
    if actual != item.get("sha256"):
        raise ValueError(f"{label} sha256 mismatch: expected {item.get('sha256')}, got {actual}")
    return path


def factor(db: float) -> float:
    return math.pow(10.0, db / 20.0)


def volume_expression(windows: list[dict]) -> str:
    expression = "1"
    for window in reversed(windows):
        start, end = float(window["start_seconds"]), float(window["end_seconds"])
        if start < 0 or end <= start:
            raise ValueError(f"invalid gain window: {window}")
        expression = f"if(between(t\\,{start:.6f}\\,{end:.6f})\\,{factor(float(window['gain_db'])):.8f}\\,{expression})"
    return expression


def measure_loudness(path: Path) -> dict:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json", "-f", "null", "-"
    ], text=True, capture_output=True)
    text = result.stderr
    begin, end = text.rfind("{\n"), text.rfind("}\n")
    if begin < 0 or end < begin:
        return {"status": "unavailable"}
    try:
        values = json.loads(text[begin:end + 1])
        return {
            "status": "measured",
            "integrated_lufs": float(values["input_i"]),
            "true_peak_dbtp": float(values["input_tp"]),
            "loudness_range_lu": float(values["input_lra"]),
        }
    except (KeyError, ValueError, json.JSONDecodeError):
        return {"status": "unavailable"}


def loudnorm_analysis(path: Path, target_lufs: float, peak: float) -> dict:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af", f"loudnorm=I={target_lufs}:LRA=11:TP={peak}:print_format=json", "-f", "null", "-"
    ], text=True, capture_output=True, check=True)
    begin, end = result.stderr.rfind("{\n"), result.stderr.rfind("}\n")
    if begin < 0 or end < begin:
        raise ValueError("unable to parse loudness analysis")
    return json.loads(result.stderr[begin:end + 1])


def build(args: argparse.Namespace) -> int:
    for dependency in ("ffmpeg", "ffprobe"):
        if not shutil.which(dependency):
            raise ValueError(f"missing dependency: {dependency}")

    plan_path = Path(args.plan).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    manifest = Path(args.manifest).expanduser().resolve()
    if not plan_path.is_file():
        raise ValueError(f"plan does not exist: {plan_path}")
    for target in (output, manifest):
        if target.exists():
            raise ValueError(f"refusing to overwrite: {target}")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("schema_version") != "1.0.0":
        raise ValueError("unsupported final-mix plan schema")
    film = require_input(plan_path, plan["film"], "film")
    bgm = require_input(plan_path, plan["bgm"], "bgm")
    film_probe, bgm_probe = probe(film), probe(bgm)
    if not film_probe["video"] or not film_probe["audio"]:
        raise ValueError("film must contain video and its accepted original soundtrack")
    if not bgm_probe["audio"]:
        raise ValueError("BGM must contain audio")

    placement = plan["placement"]
    start = float(placement["film_start_seconds"])
    source_in = float(placement.get("bgm_source_in_seconds", 0))
    film_duration = film_probe["duration_seconds"]
    cue_duration = film_duration - start
    source_out = float(placement.get("bgm_source_out_seconds", source_in + cue_duration))
    if start < 0 or cue_duration <= 0 or source_in < 0 or source_out <= source_in:
        raise ValueError("invalid music placement")
    if source_out > bgm_probe["duration_seconds"] + 0.05:
        raise ValueError("BGM is shorter than the requested source window; regenerate or revise the cue")
    source_out = min(source_out, bgm_probe["duration_seconds"])
    effective_duration = source_out - source_in
    if effective_duration + 0.05 < cue_duration:
        raise ValueError("BGM does not cover the film from its placement point")

    mix = plan["mix"]
    sample_rate = int(mix.get("sample_rate", 48000))
    bgm_lufs = float(mix.get("bgm_normalize_lufs", -24))
    base_gain = float(mix.get("bgm_base_gain_db", 0))
    fade_in = float(mix.get("fade_in_seconds", 0))
    fade_out = float(mix.get("fade_out_seconds", 0))
    if fade_in < 0 or fade_out < 0 or fade_in + fade_out > effective_duration:
        raise ValueError("invalid BGM fades")
    target_lufs = float(mix.get("final_target_lufs", -16))
    peak = float(mix.get("final_true_peak_dbtp", -1.5))
    windows = mix.get("gain_windows", [])
    expression = volume_expression(windows)

    music_filters = [
        f"atrim=start={source_in:.6f}:end={source_out:.6f}", "asetpts=PTS-STARTPTS",
        f"aresample={sample_rate}", f"loudnorm=I={bgm_lufs}:LRA=7:TP=-2",
        f"volume={factor(base_gain):.8f}",
    ]
    if fade_in:
        music_filters.append(f"afade=t=in:st=0:d={fade_in:.6f}")
    if fade_out:
        music_filters.append(f"afade=t=out:st={max(0, effective_duration - fade_out):.6f}:d={fade_out:.6f}")
    music_filters.extend([
        f"adelay={round(start * 1000)}:all=1", f"volume='{expression}':eval=frame",
        "apad", f"atrim=duration={film_duration:.6f}",
    ])
    mix_filter = (
        f"[0:a]aresample={sample_rate}[original];"
        f"[1:a]{','.join(music_filters)}[music];"
        f"[original][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mixed]"
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=output.parent) as temp_dir:
            premix = Path(temp_dir) / "premix.wav"
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(film), "-i", str(bgm),
                "-filter_complex", mix_filter, "-map", "[mixed]", "-c:a", "pcm_s24le", "-ar", str(sample_rate),
                str(premix),
            ])
            stats = loudnorm_analysis(premix, target_lufs, peak)
            loudnorm = (
                f"loudnorm=I={target_lufs}:LRA=11:TP={peak}:"
                f"measured_I={stats['input_i']}:measured_LRA={stats['input_lra']}:"
                f"measured_TP={stats['input_tp']}:measured_thresh={stats['input_thresh']}:"
                f"offset={stats['target_offset']}:linear=true:print_format=summary"
            )
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(film), "-i", str(premix),
                "-filter_complex", f"[1:a]{loudnorm}[mixed]", "-map", "0:v:0", "-map", "[mixed]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(sample_rate),
                "-movflags", "+faststart", "-shortest", str(output),
            ])
    except Exception:
        output.unlink(missing_ok=True)
        raise

    output_probe = probe(output)
    frame_in = film_probe["video"].get("frames")
    frame_out = output_probe["video"].get("frames") if output_probe["video"] else None
    if frame_in is not None and frame_out != frame_in:
        output.unlink(missing_ok=True)
        raise ValueError(f"output frame count changed: {frame_in} -> {frame_out}")
    result = {
        "schema": "story-video-final-mix-manifest", "schema_version": "1.0.0",
        "plan": {"path": str(plan_path), "sha256": sha256(plan_path)},
        "film": {"path": str(film), "sha256": sha256(film), "probe": film_probe},
        "bgm": {"path": str(bgm), "sha256": sha256(bgm), "probe": bgm_probe},
        "effective_placement": {
            "film_start_seconds": start, "bgm_source_window_seconds": [source_in, source_out],
            "fade_in_seconds": fade_in, "fade_out_seconds": fade_out,
            "gain_windows": windows,
        },
        "original_sound_policy": "preserve accepted film soundtrack as primary; mix BGM underneath",
        "output": {"path": str(output), "sha256": sha256(output), "bytes": output.stat().st_size,
                   "probe": output_probe, "loudness": measure_loudness(output)},
    }
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--plan", required=True)
    result.add_argument("--output", required=True)
    result.add_argument("--manifest", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        return build(parser().parse_args(argv))
    except (ValueError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
