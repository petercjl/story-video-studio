#!/usr/bin/env python3
"""Replace a half-open frame window with an equal-length candidate window."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(argv):
    p = subprocess.run(argv, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(argv[:2])} failed: {p.stderr[-1500:]}")
    return p.stdout


def media(path):
    raw = run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(path)])
    streams = json.loads(raw)["streams"]
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError(f"No video stream: {path}")
    frames = video.get("nb_read_frames")
    if frames in (None, "N/A"):
        raise ValueError(f"Cannot count video frames: {path}")
    return {
        "frames": int(frames),
        "fps": video["avg_frame_rate"],
        "width": int(video["width"]),
        "height": int(video["height"]),
        "audio": any(s["codec_type"] == "audio" for s in streams),
    }


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_hash(path):
    return run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c:a", "copy", "-f", "hash", "-hash", "sha256", "-"]).strip()


def replace(source, replacement, start, end, replacement_start, output, manifest=None, crf=17):
    for executable in ("ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"CAPABILITY_UNAVAILABLE: {executable}")
    source, replacement, output = map(Path, (source, replacement, output))
    manifest = Path(manifest) if manifest else None
    for path in (output, manifest):
        if path and os.path.lexists(path):
            raise FileExistsError(f"Output already exists: {path}")
    if not source.is_file() or not replacement.is_file():
        raise FileNotFoundError("Source and replacement must be existing files")
    a, b = media(source), media(replacement)
    if (a["fps"], a["width"], a["height"]) != (b["fps"], b["width"], b["height"]):
        raise ValueError("Frame rate and dimensions must match")
    if a["fps"] in ("0/0", "N/A"):
        raise ValueError("Invalid frame rate")
    if not (0 <= start < end <= a["frames"]):
        raise ValueError("Invalid source frame window")
    count = end - start
    replacement_end = replacement_start + count
    if not (0 <= replacement_start < replacement_end <= b["frames"]):
        raise ValueError("Replacement does not contain enough frames")

    parts, labels = [], []
    for input_index, first, last in ((0, 0, start), (1, replacement_start, replacement_end), (0, end, a["frames"])):
        if first == last:
            continue
        label = f"v{len(labels)}"
        parts.append(f"[{input_index}:v:0]trim=start_frame={first}:end_frame={last},setpts=PTS-STARTPTS[{label}]")
        labels.append(label)
    parts.append("".join(f"[{x}]" for x in labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=".shot-splice-", suffix=".mp4", dir=output.parent)
    os.close(handle)
    temp = Path(temp_name)
    temp.unlink()
    try:
        command = ["ffmpeg", "-v", "error", "-nostdin", "-n", "-i", str(source), "-i", str(replacement), "-filter_complex", ";".join(parts), "-map", "[outv]"]
        if a["audio"]:
            command += ["-map", "0:a:0", "-c:a", "copy"]
        command += ["-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp)]
        run(command)
        result = media(temp)
        if (result["frames"], result["fps"], result["width"], result["height"], result["audio"]) != (a["frames"], a["fps"], a["width"], a["height"], a["audio"]):
            raise RuntimeError(f"Output media verification failed: {result}")
        sound_hash = None
        if a["audio"]:
            sound_hash = audio_hash(source)
            if audio_hash(temp) != sound_hash:
                raise RuntimeError("Original audio stream changed")
        report = {
            "schema": "local-shot-splice@1.0.0",
            "source": {"path": str(source), "sha256": sha256(source), **a},
            "replacement": {"path": str(replacement), "sha256": sha256(replacement), **b},
            "source_window_frames": [start, end],
            "replacement_window_frames": [replacement_start, replacement_end],
            "audio_policy": "copy_original_stream" if a["audio"] else "silent",
            "audio_stream_hash": sound_hash,
            "output": {"path": str(output), "sha256": sha256(temp), **result},
        }
        os.link(temp, output)  # Exclusive creation, including against a concurrent writer.
        if manifest:
            try:
                with manifest.open("x", encoding="utf-8") as handle:
                    json.dump(report, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
            except Exception:
                output.unlink()
                raise
        return report
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--replacement", required=True)
    parser.add_argument("--start-frame", type=int, required=True)
    parser.add_argument("--end-frame", type=int, required=True)
    parser.add_argument("--replacement-start-frame", type=int, default=0)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--crf", type=int, default=17)
    args = parser.parse_args()
    try:
        report = replace(args.source, args.replacement, args.start_frame, args.end_frame, args.replacement_start_frame, args.output, args.manifest, args.crf)
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
