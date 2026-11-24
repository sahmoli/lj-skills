#!/usr/bin/env python3
"""Build a whole-figure, high-resolution detail, grayscale and CVD review pack."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from colour_accessibility import CVD_MATRICES
from render_cvd_preview import simulate


def render_pdf(path: Path, dpi: int, clip: fitz.Rect | None = None) -> Image.Image:
    document = fitz.open(path)
    page = document[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=clip, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    document.close()
    return image


def contact_sheet(original: Image.Image) -> Image.Image:
    preview = original.copy()
    if preview.width > 1400:
        scale = 1400 / preview.width
        preview = preview.resize((1400, round(preview.height * scale)), Image.Resampling.LANCZOS)
    panes = [
        ("Original", preview),
        ("Grayscale", preview.convert("L").convert("RGB")),
        *((name, simulate(preview, matrix)) for name, matrix in CVD_MATRICES.items()),
    ]
    label_h = 30
    columns = 2
    rows = (len(panes) + columns - 1) // columns
    canvas = Image.new("RGB", (preview.width * columns, (preview.height + label_h) * rows), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (label, pane) in enumerate(panes):
        x = (index % columns) * preview.width
        y = (index // columns) * (preview.height + label_h)
        draw.text((x + 8, y + 7), label, fill="#202124")
        canvas.paste(pane, (x, y + label_h))
    return canvas


def layout_clips(layout_path: Path, page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    data = json.loads(layout_path.read_text(encoding="utf-8"))
    canvas = data.get("canvas") or {}
    width_mm = float(canvas["width_mm"])
    height_mm = float(canvas["height_mm"])
    sx, sy = page.rect.width / width_mm, page.rect.height / height_mm
    result = []
    panels = data.get("panels") or []
    pad_x, pad_y = 6 * sx, 6 * sy
    for panel in panels:
        left = float(panel["left_mm"])
        bottom = float(panel["bottom_mm"])
        width = float(panel["width_mm"])
        height = float(panel["height_mm"])
        rect = fitz.Rect(
            left * sx,
            page.rect.height - (bottom + height) * sy,
            (left + width) * sx,
            page.rect.height - bottom * sy,
        )
        rect = fitz.Rect(
            max(0, rect.x0 - pad_x), max(0, rect.y0 - pad_y),
            min(page.rect.width, rect.x1 + pad_x), min(page.rect.height, rect.y1 + pad_y),
        )
        result.append((f"panel-{panel.get('id', len(result) + 1)}", rect))
    # High-resolution gutter strips make cross-panel decoration intrusions
    # visible; panel-only crops can otherwise hide labels outside an axes box.
    boundary_half_x, boundary_half_y = 12 * sx, 12 * sy
    for index, first in enumerate(panels):
        for second in panels[index + 1:]:
            a = _panel_rect_mm(first); b = _panel_rect_mm(second)
            vertical_overlap = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            horizontal_overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            first_id, second_id = first.get("id", index + 1), second.get("id", index + 2)
            horizontal_gap = max(b[0] - a[2], a[0] - b[2], 0.0)
            if vertical_overlap > 0 and 0 < horizontal_gap <= 12:
                boundary_mm = (max(a[0], b[0]) + min(a[2], b[2])) / 2
                boundary_x = boundary_mm * sx
                result.append((
                    f"boundary-{first_id}-{second_id}",
                    fitz.Rect(
                        max(0, boundary_x - boundary_half_x),
                        max(0, page.rect.height - (max(a[3], b[3]) + 3) * sy),
                        min(page.rect.width, boundary_x + boundary_half_x),
                        min(page.rect.height, page.rect.height - (min(a[1], b[1]) - 3) * sy),
                    ),
                ))
            vertical_gap = max(b[1] - a[3], a[1] - b[3], 0.0)
            if horizontal_overlap > 0 and 0 < vertical_gap <= 12:
                boundary_mm = (max(a[1], b[1]) + min(a[3], b[3])) / 2
                boundary_y = page.rect.height - boundary_mm * sy
                result.append((
                    f"boundary-{first_id}-{second_id}",
                    fitz.Rect(
                        max(0, min(a[0], b[0]) * sx - 3 * sx),
                        max(0, boundary_y - boundary_half_y),
                        min(page.rect.width, max(a[2], b[2]) * sx + 3 * sx),
                        min(page.rect.height, boundary_y + boundary_half_y),
                    ),
                ))
    return result


def _panel_rect_mm(panel: dict) -> tuple[float, float, float, float]:
    left = float(panel["left_mm"]); bottom = float(panel["bottom_mm"])
    return (
        left, bottom,
        left + float(panel["width_mm"]), bottom + float(panel["height_mm"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--layout", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.artifact.exists() or args.artifact.suffix.lower() not in {".pdf", ".png"}:
        print("FAIL: review sheet requires an existing PDF or PNG")
        return 2
    if args.artifact.suffix.lower() == ".pdf":
        document = fitz.open(args.artifact)
        page_count = len(document)
        document.close()
        if page_count != 1:
            print("FAIL: review sheet requires a standalone single-page figure PDF; select/extract the intended page")
            return 2
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.force:
        print(f"FAIL: refusing to overwrite non-empty {args.output_dir}; pass --force")
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.artifact.suffix.lower() == ".pdf":
        whole = render_pdf(args.artifact, 180)
        document = fitz.open(args.artifact)
        page = document[0]
        width_mm = page.rect.width * 25.4 / 72
        height_mm = page.rect.height * 25.4 / 72
        clips = layout_clips(args.layout, page) if args.layout else []
        if not clips:
            # Deterministic inspection tiles are for detail, not inferred panels.
            mid_x, mid_y = page.rect.width / 2, page.rect.height / 2
            clips = [
                ("detail-top-left", fitz.Rect(0, 0, mid_x, mid_y)),
                ("detail-top-right", fitz.Rect(mid_x, 0, page.rect.width, mid_y)),
                ("detail-bottom-left", fitz.Rect(0, mid_y, mid_x, page.rect.height)),
                ("detail-bottom-right", fitz.Rect(mid_x, mid_y, page.rect.width, page.rect.height)),
            ]
        document.close()
        for name, clip in clips:
            render_pdf(args.artifact, 600, clip).save(args.output_dir / f"{name}-600dpi.png")
        shutil.copy2(args.artifact, args.output_dir / "print-at-100-percent.pdf")
    else:
        whole = Image.open(args.artifact).convert("RGB")
        width_mm = height_mm = None
        clips = []
    whole.save(args.output_dir / "whole-composition-180dpi.png")
    contact_sheet(whole).save(args.output_dir / "accessibility-contact-sheet.png")
    report = {
        "source": str(args.artifact.resolve()),
        "physical_width_mm": round(width_mm, 2) if width_mm is not None else "unknown",
        "physical_height_mm": round(height_mm, 2) if height_mm is not None else "unknown",
        "whole_review": "composition only",
        "detail_review": "600 dpi crops; not a substitute for deterministic physical-size checks",
        "detail_regions": [name for name, _ in clips],
        "simulations": ["grayscale", *CVD_MATRICES],
    }
    (args.output_dir / "review-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
