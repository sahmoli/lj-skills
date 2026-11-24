#!/usr/bin/env python3
"""Tolerance-based visual regression for rendered figure previews.

This catches accidental layout/style drift. It does not decide whether the
baseline is beautiful or scientifically correct; baselines require explicit
human approval and source control.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops


def compare(baseline: Path, candidate: Path) -> tuple[float, float, Image.Image]:
    first = Image.open(baseline).convert("RGB")
    second = Image.open(candidate).convert("RGB")
    if first.size != second.size:
        raise ValueError(f"image dimensions differ: {first.size} != {second.size}")
    a = np.asarray(first, dtype=np.float32)
    b = np.asarray(second, dtype=np.float32)
    delta = np.abs(a - b)
    mean_absolute_error = float(delta.mean() / 255)
    changed_fraction = float(np.any(delta > 8, axis=2).mean())
    diff = ImageChops.difference(first, second)
    return mean_absolute_error, changed_fraction, diff


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--max-mae", type=float, default=0.004)
    parser.add_argument("--max-changed", type=float, default=0.03)
    args = parser.parse_args()
    try:
        mae, changed, diff = compare(args.baseline, args.candidate)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    if args.diff:
        if args.diff.exists():
            print(f"FAIL: refusing to overwrite diff image: {args.diff}")
            return 2
        diff.save(args.diff)
    print(f"FACT: mean_absolute_error={mae:.6f}")
    print(f"FACT: changed_pixel_fraction={changed:.6f}")
    if mae > args.max_mae or changed > args.max_changed:
        print("RESULT: FAIL — render changed beyond the approved tolerance")
        return 1
    print("RESULT: PASS — render is within the approved tolerance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
