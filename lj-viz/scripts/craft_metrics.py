#!/usr/bin/env python3
"""Report safe craft measurements; do not turn diagnostic proxies into beauty gates."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import fitz

from audit_layout import check_pdf_layout

MM_PER_POINT = 25.4 / 72
SPACING_TOKENS = (1.5, 2.5, 4.0, 6.0, 9.0)
NUMERIC_TICK = re.compile(r"^[−\-+]?((\d+(\.\d*)?)|(\.\d+))([eE][+\-]?\d+)?%?$")


def cluster(values: list[float], tolerance: float) -> list[float]:
    result: list[float] = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
        else:
            result[-1] = (result[-1] + value) / 2
    return result


def rect_overlap(a: dict, b: dict) -> tuple[float, float]:
    ax0, ay0 = float(a["left_mm"]), float(a["bottom_mm"])
    ax1, ay1 = ax0 + float(a["width_mm"]), ay0 + float(a["height_mm"])
    bx0, by0 = float(b["left_mm"]), float(b["bottom_mm"])
    bx1, by1 = bx0 + float(b["width_mm"]), by0 + float(b["height_mm"])
    return max(0.0, min(ax1, bx1) - max(ax0, bx0)), max(0.0, min(ay1, by1) - max(ay0, by0))


def _pdf_panel_rect(panel: dict, page: fitz.Page, width_mm: float, height_mm: float) -> fitz.Rect:
    sx, sy = page.rect.width / width_mm, page.rect.height / height_mm
    left = float(panel["left_mm"]); bottom = float(panel["bottom_mm"])
    panel_w = float(panel["width_mm"]); panel_h = float(panel["height_mm"])
    return fitz.Rect(
        left * sx, (height_mm - bottom - panel_h) * sy,
        (left + panel_w) * sx, (height_mm - bottom) * sy,
    )


def _text_line_boxes(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    result: list[tuple[str, fitz.Rect]] = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            spans = [span for span in line.get("spans", []) if str(span.get("text", "")).strip()]
            if not spans:
                continue
            rect = fitz.Rect(spans[0]["bbox"])
            for span in spans[1:]:
                rect |= fitz.Rect(span["bbox"])
            result.append(("".join(str(span.get("text", "")) for span in spans).strip(), rect))
    return result


def audit_layout_contract(
    path: Path, width_mm: float, height_mm: float, artifact: Path | None = None,
) -> tuple[list[str], list[str], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    canvas = data.get("canvas") or {}
    if abs(float(canvas.get("width_mm", 0)) - width_mm) > 0.75:
        errors.append("layout canvas width does not match PDF")
    if abs(float(canvas.get("height_mm", 0)) - height_mm) > 0.75:
        errors.append("layout canvas height does not match PDF")
    panels = data.get("panels") or []
    valid_panels: list[dict] = []
    for index, panel in enumerate(panels):
        try:
            left = float(panel["left_mm"]); bottom = float(panel["bottom_mm"])
            panel_w = float(panel["width_mm"]); panel_h = float(panel["height_mm"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"layout panel {index + 1} has invalid geometry")
            continue
        if left < 0 or bottom < 0 or panel_w <= 0 or panel_h <= 0 or left + panel_w > width_mm or bottom + panel_h > height_mm:
            errors.append(f"layout panel {index + 1} falls outside the canvas")
        else:
            valid_panels.append(panel)
        for other in panels[index + 1:]:
            overlap_x, overlap_y = rect_overlap(panel, other)
            if overlap_x > 0.1 and overlap_y > 0.1:
                errors.append(f"layout panels overlap: {panel.get('id')} and {other.get('id')}")
                continue
    # Only nearest aligned neighbours define a gutter. Counting every aligned
    # pair mistakes the span across an intervening panel for a giant gap.
    gaps: list[float] = []
    for panel in valid_panels:
        left = float(panel["left_mm"]); bottom = float(panel["bottom_mm"])
        right = left + float(panel["width_mm"]); top = bottom + float(panel["height_mm"])
        right_gaps: list[float] = []
        upper_gaps: list[float] = []
        for other in valid_panels:
            if other is panel:
                continue
            o_left = float(other["left_mm"]); o_bottom = float(other["bottom_mm"])
            o_right = o_left + float(other["width_mm"]); o_top = o_bottom + float(other["height_mm"])
            vertical_overlap = max(0.0, min(top, o_top) - max(bottom, o_bottom))
            horizontal_overlap = max(0.0, min(right, o_right) - max(left, o_left))
            if o_left >= right and vertical_overlap > min(top - bottom, o_top - o_bottom) * 0.5:
                right_gaps.append(o_left - right)
            if o_bottom >= top and horizontal_overlap > min(right - left, o_right - o_left) * 0.5:
                upper_gaps.append(o_bottom - top)
        if right_gaps:
            gaps.append(min(right_gaps))
        if upper_gaps:
            gaps.append(min(upper_gaps))
    material_gaps = [gap for gap in gaps if gap > 0.1]
    for gap in material_gaps:
        if min(abs(gap - token) for token in SPACING_TOKENS) > 0.3:
            warnings.append(f"declared panel gap {gap:.2f} mm is outside the shared token tolerance")
    decoration_failures: set[tuple] = set()
    if artifact and valid_panels:
        document = fitz.open(artifact)
        page = document[0]
        panel_rects = [_pdf_panel_rect(panel, page, width_mm, height_mm) for panel in valid_panels]
        text_boxes = _text_line_boxes(page)
        for text, rect in text_boxes:
            centre = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
            owner = {
                index for index, panel_rect in enumerate(panel_rects)
                if panel_rect.x0 <= centre.x <= panel_rect.x1 and panel_rect.y0 <= centre.y <= panel_rect.y1
            }
            for index, panel_rect in enumerate(panel_rects):
                if index in owner:
                    continue
                intersection = rect & panel_rect
                ratio = max(0.0, intersection.width) * max(0.0, intersection.height) / max(
                    1e-9, rect.width * rect.height,
                )
                depths = []
                if centre.x < panel_rect.x0 or centre.x > panel_rect.x1:
                    depths.append(max(0.0, intersection.width))
                if centre.y < panel_rect.y0 or centre.y > panel_rect.y1:
                    depths.append(max(0.0, intersection.height))
                intrusion_depth = max(depths or [0.0])
                if ratio >= 0.05 and intrusion_depth >= 1.5 / MM_PER_POINT:
                    key = (round(rect.x0, 2), round(rect.y0, 2), text, "panel", index)
                    if key not in decoration_failures:
                        decoration_failures.add(key)
                        errors.append(
                            f"rendered text intrudes into panel {valid_panels[index].get('id')}: {text!r}"
                        )
        # The centre-based owner inference above cannot identify an outside label
        # whose centre has already crossed into the neighbour. Independently audit
        # every internal gutter: any material text spill from a panel body into that
        # gutter is a collision risk, regardless of inferred ownership.
        threshold_pt = 1.5 / MM_PER_POINT
        neighbour_pairs: list[tuple[int, int]] = []
        for left_index, left_rect in enumerate(panel_rects):
            candidates = []
            for right_index, right_rect in enumerate(panel_rects):
                shared_y = max(0.0, min(left_rect.y1, right_rect.y1) - max(left_rect.y0, right_rect.y0))
                if right_rect.x0 > left_rect.x1 and shared_y > 0.5 * min(left_rect.height, right_rect.height):
                    candidates.append((right_rect.x0 - left_rect.x1, right_index))
            if candidates:
                neighbour_pairs.append((left_index, min(candidates)[1]))
        for left_index, right_index in neighbour_pairs:
            left_rect, right_rect = panel_rects[left_index], panel_rects[right_index]
            shared_y0 = max(left_rect.y0, right_rect.y0)
            shared_y1 = min(left_rect.y1, right_rect.y1)
            for text, rect in text_boxes:
                if NUMERIC_TICK.fullmatch(text.strip()):
                    continue
                vertical = max(0.0, min(rect.y1, shared_y1) - max(rect.y0, shared_y0))
                if vertical < 0.05 * max(1e-9, rect.height):
                    continue
                spill_from_left = (
                    rect.x0 < left_rect.x1
                    and rect.x1 > left_rect.x1 + threshold_pt
                    and rect.x0 < right_rect.x0
                )
                spill_from_right = (
                    rect.x1 > right_rect.x0
                    and rect.x0 < right_rect.x0 - threshold_pt
                    and rect.x1 > left_rect.x1
                )
                if spill_from_left or spill_from_right:
                    key = (round(rect.x0, 2), round(rect.y0, 2), text, "gutter", left_index, right_index)
                    if key in decoration_failures:
                        continue
                    decoration_failures.add(key)
                    errors.append(
                        "rendered text spills across boundary between panels "
                        f"{valid_panels[left_index].get('id')} and {valid_panels[right_index].get('id')}: {text!r}"
                    )
        document.close()
    return errors, warnings, {
        "declared_panel_count": len(panels),
        "declared_gap_values_mm": [round(value, 2) for value in cluster(material_gaps, 0.2)],
        "actual_decoration_intrusions": len(decoration_failures),
    }


def audit(path: Path, layout: Path | None) -> tuple[list[str], list[str], dict]:
    document = fitz.open(path)
    if len(document) != 1:
        document.close()
        return ["craft_metrics requires a single-page figure PDF"], [], {}
    page = document[0]
    width_mm, height_mm = page.rect.width * MM_PER_POINT, page.rect.height * MM_PER_POINT
    fonts: list[float] = []
    families: set[str] = set()
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if str(span.get("text", "")).strip():
                    fonts.append(float(span.get("size", 0)))
                    families.add(str(span.get("font", "unknown")))
    strokes = [
        float(item.get("width", 0)) for item in page.get_drawings()
        if isinstance(item.get("width"), (int, float)) and float(item.get("width", 0)) > 0
    ]
    document.close()
    errors, warnings, layout_facts = check_pdf_layout(path)
    facts = {
        "width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2),
        "font_size_tiers_pt": [round(value, 2) for value in cluster(fonts, 0.2)],
        "font_families": sorted(families),
        "stroke_tiers_pt": [round(value, 2) for value in cluster(strokes, 0.05)],
        **layout_facts,
        "metric_boundary": (
            "hard failures cover geometry and declared contracts only; density, hierarchy, optical balance, "
            "legend economy and icon recognition remain visual judgements"
        ),
    }
    font_tiers = facts["font_size_tiers_pt"]
    if isinstance(font_tiers, list) and len(font_tiers) > 5:
        warnings.append(f"figure uses {len(font_tiers)} material font-size tiers; inspect hierarchy consistency")
    if layout:
        contract_errors, contract_warnings, contract_facts = audit_layout_contract(
            layout, width_mm, height_mm, path,
        )
        errors.extend(contract_errors); warnings.extend(contract_warnings); facts.update(contract_facts)
    return errors, warnings, facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--layout", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if not args.artifact.exists() or args.artifact.suffix.lower() != ".pdf":
        print("FAIL: craft_metrics requires an existing PDF")
        return 2
    try:
        errors, warnings, facts = audit(args.artifact, args.layout)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 2
    if args.json_out:
        args.json_out.write_text(json.dumps({"facts": facts, "warnings": warnings, "errors": errors}, indent=2) + "\n", encoding="utf-8")
    for key, value in facts.items():
        print(f"FACT: {key}={value}")
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"FAIL: {error}")
    print(f"RESULT: {'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
