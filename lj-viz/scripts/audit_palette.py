#!/usr/bin/env python3
"""Audit declared semantic colour pairs under normal and simulated vision."""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

from colour_accessibility import CVD_MATRICES, delta_e76
from validate_manifest import load_manifest

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
sys.path.insert(0, str(ASSET_DIR))
from theme_publication import PALETTE_CRITICAL_PAIRS, PALETTE_PROFILES  # noqa: E402

CVD_FAIL_DELTA_E = 12.0
CVD_WARN_DELTA_E = 20.0


def rgb(value: str) -> tuple[int, int, int]:
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"expected six-digit hex colour: {value}")
    return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def channel(value: int) -> float:
    encoded = value / 255
    return encoded / 12.92 if encoded <= 0.04045 else ((encoded + 0.055) / 1.055) ** 2.4


def luminance(colour: tuple[int, int, int]) -> float:
    red, green, blue = (channel(value) for value in colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def lstar(colour: tuple[int, int, int]) -> float:
    value = luminance(colour)
    delta = 6 / 29
    transformed = value ** (1 / 3) if value > delta ** 3 else value / (3 * delta ** 2) + 4 / 29
    return 116 * transformed - 16


def audit(manifest: dict) -> tuple[list[str], list[str], list[str]]:
    visual = manifest.get("visual_design") or {}
    palette = visual.get("palette") or {}
    paper = rgb(str(palette.get("paper", "#FFFFFF")))
    errors: list[str] = []
    warnings: list[str] = []
    facts: list[str] = []
    thresholds = {"ink": 4.5}
    parsed: dict[str, tuple[int, int, int]] = {}
    for role in ("ink", "context"):
        parsed[role] = rgb(str(palette[role]))
        ratio = contrast(parsed[role], paper)
        facts.append(f"{role} contrast against paper={ratio:.2f}:1")
        if role in thresholds and ratio < thresholds[role]:
            errors.append(f"{role} contrast {ratio:.2f}:1 is below the {thresholds[role]:.1f}:1 role threshold")
    semantic = palette.get("semantic") or {}
    for role, value in semantic.items():
        parsed[role] = rgb(str(value))
        ratio = contrast(parsed[role], paper)
        facts.append(f"semantic.{role} contrast against paper={ratio:.2f}:1")
        if ratio < 2.0:
            warnings.append(
                f"semantic.{role} is a light fill, not a safe text/keyline colour ({ratio:.2f}:1); "
                "pair it with ink outline, position, shape, or direct label"
            )
    for first, second in itertools.combinations(semantic, 2):
        delta = abs(lstar(parsed[first]) - lstar(parsed[second]))
        facts.append(f"{first}/{second} grayscale delta-L*={delta:.1f}")
        if delta < 10:
            warnings.append(f"{first} and {second} are close in grayscale (delta-L* {delta:.1f}); retain shape/position/keylines")
    raw_pairs = palette.get("critical_pairs")
    pairs = list(itertools.combinations(semantic, 2)) if raw_pairs is None else []
    if raw_pairs is not None:
        for item in raw_pairs:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                errors.append("visual_design.palette.critical_pairs entries must be two-role lists")
                continue
            first, second = str(item[0]), str(item[1])
            if first not in semantic or second not in semantic:
                errors.append(f"critical colour pair references undeclared roles: {first}/{second}")
                continue
            pairs.append((first, second))
    encoding = manifest.get("encoding") or {}
    sole = encoding.get("colour_is_sole_carrier") is True
    redundant = str(encoding.get("redundant_channel", "")).strip().lower()
    has_redundancy = redundant not in {"", "none", "not-applicable", "unknown"}
    for first, second in pairs:
        values = {"normal": delta_e76(str(semantic[first]), str(semantic[second]))}
        values.update({
            name.lower(): delta_e76(str(semantic[first]), str(semantic[second]), matrix)
            for name, matrix in CVD_MATRICES.items()
        })
        worst_name, worst = min(values.items(), key=lambda item: item[1])
        facts.append(
            f"{first}/{second} min simulated delta-E76={worst:.1f} ({worst_name})"
        )
        if worst < CVD_FAIL_DELTA_E and (sole or not has_redundancy):
            errors.append(
                f"{first}/{second} collapses under {worst_name} (delta-E76 {worst:.1f}); "
                "colour cannot be the sole carrier"
            )
        elif worst < CVD_WARN_DELTA_E:
            warnings.append(
                f"{first}/{second} is tight under {worst_name} (delta-E76 {worst:.1f}); "
                f"verify the declared redundant channel: {redundant or 'none'}"
            )
    return errors, warnings, facts


def audit_builtins() -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    facts: list[str] = []
    for namespace, pairs in PALETTE_CRITICAL_PAIRS.items():
        palette = PALETTE_PROFILES[namespace]
        if not pairs:
            facts.append(f"{namespace}: no universal critical pairs; explicit mapping required")
            continue
        for first, second in pairs:
            values = {"normal": delta_e76(palette[first], palette[second])}
            values.update({
                name.lower(): delta_e76(palette[first], palette[second], matrix)
                for name, matrix in CVD_MATRICES.items()
            })
            worst_name, worst = min(values.items(), key=lambda item: item[1])
            facts.append(f"{namespace}.{first}/{second} min delta-E76={worst:.1f} ({worst_name})")
            if worst < CVD_FAIL_DELTA_E:
                errors.append(
                    f"built-in {namespace}.{first}/{second} collapses under {worst_name} "
                    f"(delta-E76 {worst:.1f})"
                )
            elif worst < CVD_WARN_DELTA_E:
                warnings.append(
                    f"built-in {namespace}.{first}/{second} is tight under {worst_name} "
                    f"(delta-E76 {worst:.1f}); retain redundancy"
                )
    return errors, warnings, facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("--builtin", action="store_true")
    args = parser.parse_args()
    try:
        if args.builtin:
            errors, warnings, facts = audit_builtins()
        elif args.manifest:
            errors, warnings, facts = audit(load_manifest(args.manifest))
        else:
            parser.error("provide a manifest or --builtin")
    except (KeyError, ValueError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 2
    for item in facts:
        print(f"FACT: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    for item in errors:
        print(f"FAIL: {item}")
    if errors:
        print(f"RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        return 1
    print(f"RESULT: PASS ({len(warnings)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
