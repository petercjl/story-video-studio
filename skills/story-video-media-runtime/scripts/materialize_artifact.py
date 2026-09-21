#!/usr/bin/env python3
"""Download a provider artifact atomically, without replacing an existing target."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path


def looks_like_html(prefix: bytes, content_type: str) -> bool:
    head = prefix.lstrip().lower()
    return "text/html" in content_type.lower() or head.startswith(b"<!doctype html") or head.startswith(b"<html")


def materialize(url: str, output: Path, expected_kind: str) -> dict:
    if output.exists():
        return {"ok": False, "error": {"code": "TARGET_EXISTS", "message": f"Target already exists: {output}"}}
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "story-video-media-runtime/1.0"})
    temp_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content_type = response.headers.get_content_type() or "application/octet-stream"
            fd, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".partial", dir=output.parent)
            temp_path = Path(name)
            digest = hashlib.sha256()
            size = 0
            prefix = b""
            with os.fdopen(fd, "wb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    if len(prefix) < 512:
                        prefix += chunk[: 512 - len(prefix)]
                    target.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                target.flush()
                os.fsync(target.fileno())
        if size == 0 or looks_like_html(prefix, content_type):
            raise ValueError("Provider returned an empty or HTML error artifact.")
        if expected_kind == "image" and not (content_type.startswith("image/") or prefix.startswith((b"\x89PNG", b"\xff\xd8\xff", b"RIFF"))):
            raise ValueError(f"Expected image content, received {content_type}.")
        if expected_kind == "video" and not (content_type.startswith("video/") or b"ftyp" in prefix[:64]):
            raise ValueError(f"Expected video content, received {content_type}.")
        os.replace(temp_path, output)
        temp_path = None
        return {"ok": True, "source_url": url, "path": str(output.resolve()), "sha256": digest.hexdigest(), "bytes": size, "content_type": content_type}
    except Exception as exc:
        return {"ok": False, "error": {"code": "OUTPUT_CONTRACT_FAILED", "message": str(exc)}, "source_url": url}
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-kind", choices=["image", "video", "audio", "any"], default="any")
    args = parser.parse_args()
    result = materialize(args.url, Path(args.output), args.expected_kind)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
