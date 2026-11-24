#!/usr/bin/env python3
"""Technical preflight for PDF, SVG, PNG, JPEG, and TIFF figure artifacts."""

from __future__ import annotations

import argparse
import colorsys
import io
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz
from PIL import Image

from audit_layout import check_pdf_layout
from validate_manifest import load_manifest, manifest_project_root, validate

MM_PER_POINT = 25.4 / 72.0


def figure_family(manifest: dict | None) -> str:
    return str((manifest or {}).get("figure_family", "quantitative"))


def expected_text_labels(manifest: dict | None) -> set[str]:
    """Labels which must survive export as selectable text, not image pixels."""
    data = manifest or {}
    labels = {
        str(panel.get("label", "")).strip()
        for panel in data.get("panels") or []
        if isinstance(panel, dict) and str(panel.get("label", "")).strip()
    }
    if figure_family(data) in {"conceptual", "mixed"}:
        locked = (((data.get("semantic_model") or {}).get("constraints") or {}).get("locked_labels") or {})
        if isinstance(locked, dict):
            labels.update(str(value).strip() for value in locked.values() if str(value).strip())
    return labels


def visual_craft_facts(path: Path) -> tuple[list[str], dict[str, object]]:
    """Return coarse rendered facts; never claim that these certify beauty."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(path)
        pixmap = doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
        doc.close()
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        with Image.open(path) as source:
            image = source.convert("RGB")
    else:
        return [], {
            "visual_density": "not-inspected",
            "edge_occupancy": "not-inspected",
            "saturated_colour_clusters": "not-inspected",
        }

    image.thumbnail((480, 480))
    width, height = image.size
    pixels = list(image.get_flattened_data()) if hasattr(image, "get_flattened_data") else list(image.getdata())
    nonwhite = [max(pixel) < 248 or min(pixel) < 244 for pixel in pixels]
    density = sum(nonwhite) / max(1, len(nonwhite))
    border = max(2, round(min(width, height) * 0.025))
    edge_indices = [
        y * width + x
        for y in range(height)
        for x in range(width)
        if x < border or x >= width - border or y < border or y >= height - border
    ]
    edge_occupancy = sum(nonwhite[index] for index in edge_indices) / max(1, len(edge_indices))

    quantized = image.quantize(colors=48)
    clusters = []
    total = width * height
    palette = quantized.getpalette() or []
    for count, index in quantized.getcolors(maxcolors=48) or []:
        if count / max(1, total) < 0.001:
            continue
        red, green, blue = palette[index * 3:index * 3 + 3]
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        del hue
        if saturation >= 0.42 and 0.22 <= value <= 0.93:
            clusters.append((count, (red, green, blue)))

    warnings: list[str] = []
    if edge_occupancy > 0.28:
        warnings.append(f"rendered content crowds the outer 2.5% of the canvas (edge occupancy {edge_occupancy:.1%})")
    if density > 0.62:
        warnings.append(f"rendered visual density is very high ({density:.1%}); inspect hierarchy and gutters at final size")
    return warnings, {
        "visual_density": f"{density:.1%}",
        "edge_occupancy": f"{edge_occupancy:.1%}",
        "saturated_colour_clusters": len(clusters),
        "visual_craft_notice": "coarse facts only; hierarchy, spacing rhythm and icon meaning require visual review",
    }

def pdf_checks(
    path: Path,
    expected_labels: set[str] | None = None,
) -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    doc = fitz.open(path)
    if len(doc) != 1:
        warnings.append(f"PDF has {len(doc)} pages; a standalone figure normally has one")
    page = doc[0]
    width_mm, height_mm = page.rect.width * MM_PER_POINT, page.rect.height * MM_PER_POINT
    font_sizes, text_values = [], set()
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            line_value = "".join(str(span.get("text", "")) for span in line.get("spans", [])).strip()
            if line_value:
                text_values.add(line_value)
            for span in line.get("spans", []):
                font_sizes.append(float(span.get("size", 0)))
                value = str(span.get("text", "")).strip()
                if value:
                    text_values.add(value)
    if font_sizes and min(font_sizes) < 5:
        warnings.append(f"minimum PDF text size is {min(font_sizes):.2f} pt (<5 pt)")
    image_dpis = []
    for image in page.get_images(full=True):
        xref, width_px, height_px = image[0], image[2], image[3]
        for rect in page.get_image_rects(xref):
            if rect.width > 0 and rect.height > 0:
                image_dpis.append(min(width_px / (rect.width / 72), height_px / (rect.height / 72)))
    if image_dpis and min(image_dpis) < 300:
        warnings.append(f"minimum effective embedded-image resolution is {min(image_dpis):.0f} dpi")
    stroke_widths = [
        float(drawing.get("width", 0))
        for drawing in page.get_drawings()
        if isinstance(drawing.get("width"), (int, float)) and float(drawing.get("width", 0)) > 0
    ]
    if stroke_widths and min(stroke_widths) < 0.24:
        errors.append(f"minimum observable vector stroke is {min(stroke_widths):.2f} pt (<0.25 pt)")
    if stroke_widths and max(stroke_widths) > 1.01:
        errors.append(f"maximum observable vector stroke is {max(stroke_widths):.2f} pt (>1 pt)")
    doc.close()
    if shutil.which("pdffonts"):
        result = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True, check=False)
        for line in result.stdout.splitlines()[2:]:
            # pdffonts uses fixed-width columns, but font types such as "Type 3"
            # contain spaces. Splitting on 2+ spaces preserves the emb/sub/uni
            # flag group and avoids mistaking the object number for `emb`.
            columns = re.split(r"\s{2,}", line.strip())
            if len(columns) >= 4:
                flags = columns[3].split()
                if flags and flags[0].lower() == "no":
                    warnings.append(f"font is not embedded: {columns[0]}")
    observed_labels = sorted((expected_labels or set()) & text_values)
    return errors, warnings, {
        "width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2),
        "min_font_pt": round(min(font_sizes), 2) if font_sizes else "unknown",
        "vector_stroke_pt": (
            f"{min(stroke_widths):.2f}–{max(stroke_widths):.2f}" if stroke_widths else "not-observed"
        ),
        "min_embedded_image_dpi": round(min(image_dpis)) if image_dpis else "not-applicable-or-unknown",
        "panel_labels_observed": ",".join(observed_labels) or "none",
    }

def raster_checks(path: Path, manifest: dict | None) -> tuple[list[str], list[str], dict[str, object]]:
    warnings: list[str] = []
    image = Image.open(path)
    width_mm = ((manifest or {}).get("output") or {}).get("width_mm")
    effective_dpi = image.width / (float(width_mm) / 25.4) if width_mm else None
    if effective_dpi is not None and effective_dpi < 300:
        warnings.append(f"effective raster resolution is {effective_dpi:.0f} dpi at manifest width")
    if width_mm is None:
        warnings.append("manifest output.width_mm is needed to calculate effective DPI")
    return [], warnings, {
        "pixels": f"{image.width}x{image.height}", "dpi_metadata": image.info.get("dpi") or "missing",
        "effective_dpi_at_manifest_width": round(effective_dpi) if effective_dpi else "unknown",
        "colour_mode": image.mode,
    }

def _svg_length_mm(value: str | None) -> float | None:
    if not value:
        return None
    match = re.fullmatch(r"\s*([0-9.]+)\s*(mm|cm|in|pt|px)?\s*", value)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2) or "px"
    factors = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": MM_PER_POINT, "px": 25.4 / 96}
    return amount * factors[unit]


def _svg_font_size_pt(node: ET.Element, user_unit_pt: float) -> float | None:
    value = node.attrib.get("font-size")
    if value is None:
        match = re.search(r"(?:^|;)\s*font-size\s*:\s*([0-9.]+)\s*(pt|px)?", node.attrib.get("style", ""))
        if not match:
            return None
        value = match.group(1) + (match.group(2) or "px")
    match = re.fullmatch(r"\s*([0-9.]+)\s*(pt|px)?\s*", value)
    if not match:
        return None
    amount = float(match.group(1))
    return amount if match.group(2) == "pt" else amount * user_unit_pt


def svg_checks(path: Path, manifest: dict | None) -> tuple[list[str], list[str], dict[str, object]]:
    root = ET.parse(path).getroot()
    text_nodes = [node for node in root.iter() if node.tag.endswith("text")]
    values = {"".join(node.itertext()).strip() for node in text_nodes}
    expected_labels = expected_text_labels(manifest)
    observed_labels = sorted(expected_labels & values)
    width_mm = _svg_length_mm(root.attrib.get("width"))
    height_mm = _svg_length_mm(root.attrib.get("height"))
    view_box = root.attrib.get("viewBox", "").replace(",", " ").split()
    user_unit_pt = 72 / 96
    if width_mm is not None and len(view_box) == 4:
        try:
            view_width = float(view_box[2])
            if view_width > 0:
                user_unit_pt = width_mm / MM_PER_POINT / view_width
        except ValueError:
            pass
    font_sizes = [
        size for node in text_nodes
        if (size := _svg_font_size_pt(node, user_unit_pt)) is not None
    ]
    errors: list[str] = []
    warnings: list[str] = []
    expected = (manifest or {}).get("output") or {}
    for key, actual in (("width_mm", width_mm), ("height_mm", height_mm)):
        target = expected.get(key)
        if isinstance(target, (int, float)):
            if actual is None:
                errors.append(f"SVG physical {key} cannot be resolved")
            elif abs(actual - float(target)) > 0.75:
                errors.append(f"SVG {key}={actual:.2f} does not match manifest {target}")
    if font_sizes and min(font_sizes) < 5:
        warnings.append(f"minimum SVG text size is {min(font_sizes):.2f} pt (<5 pt)")
    if len(expected_labels) > 1:
        missing_labels = expected_labels - set(observed_labels)
        if missing_labels:
            errors.append("panel labels not observed in SVG: " + ", ".join(sorted(missing_labels)))
    if figure_family(manifest) in {"conceptual", "mixed"}:
        if not text_nodes:
            errors.append("conceptual SVG must retain labels as editable <text> elements")
        vector_tags = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
        vector_count = sum(node.tag.rsplit("}", 1)[-1] in vector_tags for node in root.iter())
        image_count = sum(node.tag.rsplit("}", 1)[-1] == "image" for node in root.iter())
        if image_count and vector_count == 0:
            errors.append("conceptual SVG is a raster wrapper; retain editable vector nodes and edges")
    return errors, warnings, {
        "width": root.attrib.get("width", "unknown"), "height": root.attrib.get("height", "unknown"),
        "width_mm": round(width_mm, 2) if width_mm is not None else "unknown",
        "height_mm": round(height_mm, 2) if height_mm is not None else "unknown",
        "view_box": root.attrib.get("viewBox", "unknown"),
        "text_nodes": len(text_nodes), "min_font_pt": round(min(font_sizes), 2) if font_sizes else "unknown",
        "panel_labels_observed": ",".join(observed_labels) or "none",
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    if not args.artifact.exists() or args.artifact.stat().st_size == 0:
        print("FAIL: artifact is missing or empty")
        return 2
    manifest, errors, warnings = None, [], []
    if args.manifest:
        try:
            manifest = load_manifest(args.manifest)
            root = manifest_project_root(args.manifest.resolve(), manifest, args.project_root)
            manifest_errors, manifest_warnings = validate(manifest, root)
            errors.extend(manifest_errors)
            warnings.extend(manifest_warnings)
        except Exception as exc:
            errors.append(f"manifest could not be read: {exc}")
    else:
        warnings.append("no manifest supplied; scientific/provenance checks are incomplete")
    suffix = args.artifact.suffix.lower()
    if suffix == ".pdf":
        expected_pdf_labels = expected_text_labels(manifest)
        artifact_errors, artifact_warnings, facts = pdf_checks(args.artifact, expected_pdf_labels)
        icon_mode = (((manifest or {}).get("visual_design") or {}).get("icons") or {}).get("mode")
        placement = ((manifest or {}).get("visual_design") or {}).get("placement") or {}
        # With a manifest, only treat small embedded rasters as icons when the
        # figure declares semantic icons. This prevents ordinary microscopy or
        # photograph panels from being misclassified. A standalone audit keeps
        # the conservative heuristic because it lacks that semantic context.
        layout_errors, layout_warnings, layout_facts = check_pdf_layout(
            args.artifact,
            clearance_mm=float(placement.get("label_icon_clearance_mm", 1.5)),
            edge_clearance_mm=float(placement.get("edge_clearance_mm", 1.5)),
            check_small_images=manifest is None or icon_mode == "semantic",
        )
        artifact_errors.extend(layout_errors)
        artifact_warnings.extend(layout_warnings)
        facts.update(layout_facts)
    elif suffix == ".svg":
        artifact_errors, artifact_warnings, facts = svg_checks(args.artifact, manifest)
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        artifact_errors, artifact_warnings, facts = raster_checks(args.artifact, manifest)
    else:
        print(f"FAIL: unsupported artifact type: {suffix}")
        return 2
    errors.extend(artifact_errors)
    warnings.extend(artifact_warnings)
    craft_warnings, craft_facts = visual_craft_facts(args.artifact)
    warnings.extend(craft_warnings)
    facts.update(craft_facts)
    if manifest and isinstance(facts.get("saturated_colour_clusters"), int):
        visual = manifest.get("visual_design") or {}
        palette = visual.get("palette") or {}
        encoding = manifest.get("encoding") or {}
        role = str(encoding.get("colour_role", "")).lower()
        category_count = int(palette.get("categorical_count") or 0)
        expected_max = max(4, category_count + 2)
        if role not in {"sequential", "diverging", "continuous"} and facts["saturated_colour_clusters"] > expected_max:
            warnings.append(
                f"rendered figure has {facts['saturated_colour_clusters']} material saturated colour clusters "
                f"(manifest suggests about {expected_max}); review accent budget and palette roles"
            )
    if manifest and suffix == ".pdf":
        expected = manifest.get("output") or {}
        for key in ("width_mm", "height_mm"):
            target, actual = expected.get(key), facts.get(key)
            if isinstance(target, (int, float)) and isinstance(actual, (int, float)) and abs(actual - target) > 0.75:
                errors.append(f"PDF {key}={actual} does not match manifest {target}")
        expected_labels = expected_text_labels(manifest)
        # A single-panel figure may legitimately omit a part label. For a
        # multi-panel figure, absent labels break caption-to-panel routing.
        if len(expected_labels) > 1 or figure_family(manifest) in {"conceptual", "mixed"}:
            observed = set(str(facts.get("panel_labels_observed", "")).split(","))
            observed.discard("none")
            missing_labels = expected_labels - observed
            if missing_labels:
                errors.append("panel labels not observed in PDF: " + ", ".join(sorted(missing_labels)))
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
