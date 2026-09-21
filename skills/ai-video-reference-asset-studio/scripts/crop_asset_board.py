#!/usr/bin/env python3
"""Create deterministic panel crops from one approved asset board."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("spec", type=Path, help="JSON array with panel_id, role, and crop_box_normalized")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    image_path = args.image.resolve()
    with args.spec.open("r", encoding="utf-8") as handle:
        panels = json.load(handle)
    if not isinstance(panels, list) or not panels:
        raise ValueError("spec must be a non-empty JSON array")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with Image.open(image_path) as source:
        width, height = source.size
        for panel in panels:
            box = panel.get("crop_box_normalized")
            if not isinstance(box, list) or len(box) != 4 or not all(isinstance(v, (int, float)) for v in box):
                raise ValueError(f"invalid crop box for {panel.get('panel_id')}")
            if not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
                raise ValueError(f"crop box is outside normalized bounds for {panel.get('panel_id')}")
            pixels = (round(box[0] * width), round(box[1] * height), round(box[2] * width), round(box[3] * height))
            output = args.output_dir / f"{panel['panel_id']}-{panel['role']}.png"
            source.crop(pixels).save(output, format="PNG")
            records.append({**panel, "crop_pixels": f"{pixels[2] - pixels[0]}x{pixels[3] - pixels[1]}", "crop_file": output.name, "crop_sha256": sha256_file(output)})
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
