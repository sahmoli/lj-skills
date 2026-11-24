#!/usr/bin/env python3
"""Render an approved SVG silhouette to a transparent final-size PNG preview."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    import fitz
except ImportError as exc:
    raise SystemExit("PyMuPDF is required to render an SVG silhouette") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width-mm", type=float, required=True)
    parser.add_argument("--dpi", type=float, default=600)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.source.exists() or args.source.stat().st_size == 0:
        print(f"FAIL: source is missing or empty: {args.source}")
        return 1
    if args.source.suffix.lower() != ".svg":
        print("FAIL: source must be an SVG")
        return 1
    if args.output.suffix.lower() != ".png":
        print("FAIL: output must be a PNG")
        return 1
    if args.output.exists() and not args.force:
        print(f"FAIL: output exists; pass --force only when overwrite is authorised: {args.output}")
        return 1
    if not math.isfinite(args.width_mm) or args.width_mm <= 0:
        print("FAIL: --width-mm must be a positive number")
        return 1
    if not math.isfinite(args.dpi) or args.dpi <= 0:
        print("FAIL: --dpi must be a positive number")
        return 1

    document = fitz.open(args.source)
    if document.page_count != 1:
        document.close()
        print("FAIL: silhouette SVG must contain one page")
        return 1
    page = document[0]
    target_pixels = args.width_mm / 25.4 * args.dpi
    zoom = target_pixels / page.rect.width
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(args.output)
    document.close()
    print(
        f"RESULT: PASS ({args.output}; {pixmap.width}x{pixmap.height}px; "
        f"{args.width_mm:g} mm at {args.dpi:g} dpi)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
