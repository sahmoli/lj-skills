#!/usr/bin/env python3
"""Detect material text, icon, and page-edge collisions in a rendered PDF.

This is a conservative geometry screen, not an aesthetic judge. It operates on
the final PDF because editor coordinates and zoom do not reveal final-size
collisions. Text spans on the same PDF line are merged before testing so math
glyphs and styled fragments do not create false self-collisions.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

POINTS_PER_MM = 72 / 25.4


@dataclass(frozen=True)
class LabelBox:
    text: str
    rect: fitz.Rect


def _area(rect: fitz.Rect) -> float:
    return max(0.0, rect.width) * max(0.0, rect.height)


def _distance(first: fitz.Rect, second: fitz.Rect) -> float:
    dx = max(first.x0 - second.x1, second.x0 - first.x1, 0.0)
    dy = max(first.y0 - second.y1, second.y0 - first.y1, 0.0)
    return math.hypot(dx, dy)


def _line_boxes(page: fitz.Page) -> list[LabelBox]:
    boxes: list[LabelBox] = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            spans = [span for span in line.get("spans", []) if str(span.get("text", "")).strip()]
            if not spans:
                continue
            text = "".join(str(span.get("text", "")) for span in spans).strip()
            rect = fitz.Rect(spans[0]["bbox"])
            for span in spans[1:]:
                rect |= fitz.Rect(span["bbox"])
            if text and _area(rect) > 0:
                boxes.append(LabelBox(text=text, rect=rect))
    return boxes


def _small_image_boxes(page: fitz.Page) -> list[fitz.Rect]:
    """Return image boxes that plausibly act as icons, not full raster panels."""
    result: list[fitz.Rect] = []
    page_area = _area(page.rect)
    for image in page.get_images(full=True):
        for rect in page.get_image_rects(image[0]):
            fraction = _area(rect) / max(page_area, 1)
            if 0 < fraction <= 0.04 and rect.width <= page.rect.width * 0.28 and rect.height <= page.rect.height * 0.28:
                result.append(rect)
    return result


def parse_pages(value: str, page_count: int) -> list[int]:
    """Parse a one-based page expression such as ``1,3-5``."""
    pages: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", token)
        if not match:
            raise ValueError(f"invalid page expression: {token!r}")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start or end > page_count:
            raise ValueError(f"page range {token!r} is outside 1-{page_count}")
        pages.update(range(start - 1, end))
    if not pages:
        raise ValueError("page selection is empty")
    return sorted(pages)


def check_pdf_layout(
    path: Path,
    *,
    clearance_mm: float = 1.5,
    edge_clearance_mm: float = 1.5,
    check_small_images: bool = True,
    pages: list[int] | None = None,
) -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    document = fitz.open(path)
    if pages is None and len(document) != 1:
        document.close()
        return ["multipage PDF requires an explicit --pages selection"], warnings, {
            "layout_text_lines": "not-checked-multipage",
            "layout_small_images": "not-checked-multipage",
            "layout_pages_checked": 0,
        }
    selected = pages if pages is not None else [0]
    if any(index < 0 or index >= len(document) for index in selected):
        document.close()
        return [f"page selection is outside 1-{len(document)}"], warnings, {"layout_pages_checked": 0}
    clearance = clearance_mm * POINTS_PER_MM
    edge = edge_clearance_mm * POINTS_PER_MM
    overlap_pairs = 0
    clipped_or_edge = 0
    icon_overlaps = 0
    low_clearance = 0
    label_count = 0
    icon_count = 0
    for page_index in selected:
        page = document[page_index]
        prefix = f"page {page_index + 1}: " if len(document) > 1 else ""
        labels = _line_boxes(page)
        icons = _small_image_boxes(page) if check_small_images else []
        label_count += len(labels)
        icon_count += len(icons)
        for index, first in enumerate(labels):
            for second in labels[index + 1:]:
                intersection = first.rect & second.rect
                if intersection.is_empty:
                    continue
                ratio = _area(intersection) / max(1e-9, min(_area(first.rect), _area(second.rect)))
                if ratio >= 0.08:
                    overlap_pairs += 1
                    errors.append(
                        f"{prefix}text overlap ({ratio:.0%} of smaller box): "
                        f"{first.text!r} ↔ {second.text!r}"
                    )
        for label in labels:
            rect = label.rect
            outside = (
                rect.x0 < -0.2 or rect.y0 < -0.2
                or rect.x1 > page.rect.width + 0.2 or rect.y1 > page.rect.height + 0.2
            )
            if outside:
                clipped_or_edge += 1
                errors.append(f"{prefix}text extends outside page: {label.text!r}")
            elif min(rect.x0, rect.y0, page.rect.width - rect.x1, page.rect.height - rect.y1) < edge:
                clipped_or_edge += 1
                warnings.append(
                    f"{prefix}text is within {edge_clearance_mm:g} mm of page edge: {label.text!r}"
                )
        for label in labels:
            for icon_index, icon in enumerate(icons, start=1):
                intersection = label.rect & icon
                if not intersection.is_empty and _area(intersection) > 0.5:
                    icon_overlaps += 1
                    errors.append(f"{prefix}text overlaps small image/icon {icon_index}: {label.text!r}")
                # Allow 0.15 mm for PDF coordinate rounding and raster bounding-box
                # quantisation when the declared gap is exactly one spacing token.
                elif _distance(label.rect, icon) < clearance - 0.15 * POINTS_PER_MM:
                    low_clearance += 1
                    warnings.append(
                        f"{prefix}text–icon clearance is below {clearance_mm:g} mm "
                        f"for icon {icon_index}: {label.text!r}"
                    )
    document.close()
    return errors, warnings, {
        "layout_pages_checked": ",".join(str(index + 1) for index in selected),
        "layout_text_lines": label_count,
        "layout_small_images": icon_count,
        "layout_text_overlap_pairs": overlap_pairs,
        "layout_text_icon_overlaps": icon_overlaps,
        "layout_low_clearance_pairs": low_clearance,
        "layout_edge_flags": clipped_or_edge,
        "layout_edge_clearance_mm": edge_clearance_mm,
        "layout_notice": "geometry screen only; data-mark collisions and visual hierarchy still require pixel review",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--clearance-mm", type=float, default=1.5)
    parser.add_argument("--edge-clearance-mm", type=float, default=1.5)
    parser.add_argument("--pages", help="one-based selection, e.g. 1,3-5")
    args = parser.parse_args()
    if not args.artifact.exists() or args.artifact.suffix.lower() != ".pdf":
        print("FAIL: audit_layout requires an existing PDF")
        return 2
    try:
        document = fitz.open(args.artifact)
        pages = parse_pages(args.pages, len(document)) if args.pages else None
        document.close()
        errors, warnings, facts = check_pdf_layout(
            args.artifact,
            clearance_mm=args.clearance_mm,
            edge_clearance_mm=args.edge_clearance_mm,
            pages=pages,
        )
    except (ValueError, fitz.FileDataError) as exc:
        print(f"FAIL: {exc}")
        return 2
    for key, value in facts.items():
        print(f"FACT: {key}={value}")
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
