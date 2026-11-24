#!/usr/bin/env python3
"""Render original, grayscale, protanopia, and deuteranopia review panes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from colour_accessibility import CVD_MATRICES, linear_to_srgb, simulate_linear, srgb_to_linear


def simulate(image: Image.Image, matrix: np.ndarray) -> Image.Image:
    data = np.asarray(image.convert("RGB"), dtype=np.float32) / 255
    transformed = simulate_linear(srgb_to_linear(data), matrix)
    encoded = linear_to_srgb(transformed)
    return Image.fromarray(np.uint8(np.clip(encoded, 0, 1) * 255), "RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"FAIL: refusing to overwrite {args.output}")
        return 2
    try:
        original = Image.open(args.input).convert("RGB")
    except OSError as exc:
        print(f"FAIL: {exc}")
        return 2
    max_width = 1200
    if original.width > max_width:
        scale = max_width / original.width
        original = original.resize((max_width, round(original.height * scale)), Image.Resampling.LANCZOS)
    panes = [
        ("Original", original),
        ("Grayscale", original.convert("L").convert("RGB")),
        *((name, simulate(original, matrix)) for name, matrix in CVD_MATRICES.items()),
    ]
    label_height = 30
    columns = 2
    rows = (len(panes) + columns - 1) // columns
    canvas = Image.new("RGB", (original.width * columns, (original.height + label_height) * rows), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (label, pane) in enumerate(panes):
        x = (index % columns) * original.width
        y = (index // columns) * (original.height + label_height)
        draw.text((x + 8, y + 7), label, fill="#202124")
        canvas.paste(pane, (x, y + label_height))
    canvas.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
