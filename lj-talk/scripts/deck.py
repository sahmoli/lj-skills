#!/usr/bin/env python3
"""Build small, editable PowerPoint decks from an agent-authored JSON plan.

The builder deliberately has no network or generation integration.  It makes
native PowerPoint text and pictures; a caller supplies every local asset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from PIL import Image
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.util import Inches, Pt
except ImportError as exc:  # keep --help usable in a bare Python install
    raise SystemExit("deck.py needs python-pptx and Pillow: " + str(exc))


VERSION = 1
W, H = Inches(13.333333), Inches(7.5)
PAPER, INK, MUTE, BLUE, RULE, WHITE = (
    RGBColor(244, 244, 237), RGBColor(20, 20, 18), RGBColor(110, 108, 100),
    RGBColor(36, 64, 110), RGBColor(220, 218, 208), RGBColor(255, 255, 255),
)
SERIF, MONO, CJK = "Palatino Linotype", "Consolas", "Microsoft YaHei"


class PlanError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def state_path(output: Path) -> Path:
    return output.with_name(output.name + ".deck-state.json")


def require_pptx_output(output: Path) -> Path:
    output = output.resolve()
    if output.suffix.lower() != ".pptx":
        raise PlanError("output must use the .pptx suffix")
    return output


def protect_build_inputs(plan_path: Path, records: list[dict[str, Any]], output: Path) -> None:
    """Keep plan and original evidence inputs read-only from this invocation."""
    targets = {output, state_path(output).resolve()}
    inputs = {plan_path.resolve()}
    for record in records:
        inputs.update(Path(dep["path"]).resolve() for dep in record["dependencies"])
    conflict = targets.intersection(inputs)
    if conflict:
        raise PlanError("output or its state file would overwrite an input: " + ", ".join(map(str, sorted(conflict))))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanError(f"cannot read JSON {path}: {exc}") from exc


def asset_path(value: str, plan_path: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (plan_path.parent / path).resolve()


def require_string(record: dict[str, Any], field: str, where: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{where}.{field} must be a non-empty string")
    return value


def validate_plan(plan: Any, plan_path: Path) -> list[dict[str, Any]]:
    if not isinstance(plan, dict):
        raise PlanError("plan root must be an object")
    require_string(plan, "deck_id", "plan")
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        raise PlanError("plan.slides must be a non-empty list")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for number, raw in enumerate(slides, 1):
        where = f"slides[{number}]"
        if not isinstance(raw, dict):
            raise PlanError(f"{where} must be an object")
        slide = dict(raw)
        sid = require_string(slide, "id", where)
        if sid in seen:
            raise PlanError(f"duplicate stable slide id: {sid}")
        seen.add(sid)
        if slide.get("section", "main") not in {"main", "appendix"}:
            raise PlanError(f"{where}.section must be main or appendix")
        if slide.get("kind", "content") not in {"title", "content", "section"}:
            raise PlanError(f"{where}.kind must be title, content, or section")
        require_string(slide, "title", where)
        body = slide.get("body", [])
        if not isinstance(body, (str, list)) or isinstance(body, list) and not all(isinstance(x, str) for x in body):
            raise PlanError(f"{where}.body must be a string or list of strings")
        if "notes" in slide and not isinstance(slide["notes"], str):
            raise PlanError(f"{where}.notes must be a string")
        sources = slide.get("sources", [])
        if not isinstance(sources, list):
            raise PlanError(f"{where}.sources must be a list")
        for source_index, source in enumerate(sources, 1):
            sw = f"{where}.sources[{source_index}]"
            if not isinstance(source, dict):
                raise PlanError(f"{sw} must be an object")
            if source.get("missing") is True:
                continue
            require_string(source, "citation", sw)
            require_string(source, "locator", sw)
            if "path" in source:
                source_file = asset_path(require_string(source, "path", sw), plan_path)
                if not source_file.is_file():
                    raise PlanError(f"required source path is missing: {source_file}")
        images = slide.get("images", [])
        if not isinstance(images, list):
            raise PlanError(f"{where}.images must be a list")
        image_ids: set[str] = set()
        for image_index, image in enumerate(images, 1):
            iw = f"{where}.images[{image_index}]"
            if not isinstance(image, dict):
                raise PlanError(f"{iw} must be an object")
            image_id = require_string(image, "id", iw)
            if image_id in image_ids:
                raise PlanError(f"duplicate image id in {where}: {image_id}")
            image_ids.add(image_id)
            if image.get("fit", "contain") not in {"contain", "crop"}:
                raise PlanError(f"{iw}.fit must be contain or crop")
            validate_geometry(image, iw)
            if image.get("role", "evidence") not in {"evidence", "illustrative"}:
                raise PlanError(f"{iw}.role must be evidence or illustrative")
            if image.get("missing") is not True:
                image_file = asset_path(require_string(image, "path", iw), plan_path)
                if not image_file.is_file():
                    raise PlanError(f"required image path is missing: {image_file}")
            if "generation_prompt" in image and image.get("role") != "illustrative":
                raise PlanError(f"{iw}.generation_prompt is only valid for illustrative assets")
        elements = slide.get("elements", [])
        if not isinstance(elements, list):
            raise PlanError(f"{where}.elements must be a list")
        element_ids: set[str] = set()
        for element in elements:
            if not isinstance(element, dict) or element.get("type") not in {"text", "box"}:
                raise PlanError(f"{where}.elements supports text or box objects")
            eid = require_string(element, "id", where + ".elements")
            if eid in element_ids:
                raise PlanError(f"duplicate element id in {where}: {eid}")
            element_ids.add(eid)
            validate_geometry(element, where + ".elements")
        layout = slide.get("layout", {})
        if not isinstance(layout, dict):
            raise PlanError(f"{where}.layout must be an object")
        for name in ("title", "body"):
            if name in layout:
                if not isinstance(layout[name], dict): raise PlanError(f"{where}.layout.{name} must be an object")
                validate_geometry(layout[name], f"{where}.layout.{name}")
        normalized.append(slide)
    return normalized


def validate_geometry(record: dict[str, Any], where: str) -> None:
    keys = {"x", "y", "w", "h"}
    present = keys.intersection(record)
    if present and present != keys:
        raise PlanError(f"{where} geometry needs x, y, w, and h together")
    if present:
        try: x, y, w, h = (float(record[k]) for k in ("x", "y", "w", "h"))
        except (TypeError, ValueError) as exc: raise PlanError(f"{where} geometry must be numeric") from exc
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 13.334 or y + h > 7.501:
            raise PlanError(f"{where} geometry must fit the 13.333 × 7.5 inch slide")


def add_text(slide, name: str, text: str, x: float, y: float, w: float, h: float,
             size: float, color=INK, font=SERIF, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.name = name
    tf = box.text_frame
    tf.clear(); tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.name = font; run.font.size = Pt(size); run.font.color.rgb = color; run.font.bold = bold
    # Explicitly set East-Asian face while retaining all Unicode source text.
    rpr = run._r.get_or_add_rPr()
    for tag, face in (("a:latin", font), ("a:ea", CJK), ("a:cs", font)):
        child = rpr.find(qn(tag))
        if child is None:
            from lxml import etree
            child = etree.SubElement(rpr, qn(tag))
        child.set("typeface", face)
    return box


def add_rect(slide, name: str, x: float, y: float, w: float, h: float, fill=RULE):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.name = name; shape.line.fill.background(); shape.fill.solid(); shape.fill.fore_color.rgb = fill
    return shape


def fit_picture(pic, path: Path, x: float, y: float, w: float, h: float, fit: str) -> None:
    """Fit an image in a box without creating a derived raster asset."""
    with Image.open(path) as opened: iw, ih = opened.size
    image_ratio, box_ratio = iw / ih, w / h
    if fit == "contain":
        if image_ratio > box_ratio:
            pic.height = int(pic.width / image_ratio); pic.top = Inches(y) + int((Inches(h) - pic.height) / 2)
        else:
            pic.width = int(pic.height * image_ratio); pic.left = Inches(x) + int((Inches(w) - pic.width) / 2)
    elif image_ratio > box_ratio:
        crop = (1 - box_ratio / image_ratio) / 2; pic.crop_left = pic.crop_right = crop
    else:
        crop = (1 - image_ratio / box_ratio) / 2; pic.crop_top = pic.crop_bottom = crop


def add_picture(slide, name: str, image: dict[str, Any], plan_path: Path, x: float, y: float, w: float, h: float):
    if image.get("missing") is True:
        add_rect(slide, name + ":missing", x, y, w, h, RGBColor(232, 229, 218))
        add_text(slide, name, "Missing image\n" + image.get("id", "asset"), x + .18, y + .18, w - .36, h - .36, 16, MUTE, MONO)
        return
    path = asset_path(image["path"], plan_path)
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.name = name
    fit_picture(pic, path, x, y, w, h, image.get("fit", "contain"))


def notes_text(slide: dict[str, Any]) -> str:
    notes = slide.get("notes", "").strip()
    sources = []
    for source in slide.get("sources", []):
        if source.get("missing"):
            sources.append("[Source missing by plan]")
        else:
            sources.append(f"{source['citation']} — {source['locator']}")
    return notes + (("\n\nSources\n" if notes else "Sources\n") + "\n".join(sources) if sources else "")


def add_notes(ppt_slide, text: str) -> None:
    if text:
        ppt_slide.notes_slide.notes_text_frame.text = text


def box(layout: dict[str, Any], name: str, default: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    spec = layout.get(name, {})
    return tuple(float(spec.get(k, default[i])) for i, k in enumerate(("x", "y", "w", "h")))


def build_slide(prs, item: dict[str, Any], footer_number: str, plan_path: Path) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6]); sid = item["id"]
    # A light, warm Kami-derived paper is the default; plans can opt into ink.
    dark = item.get("theme") == "ink"
    add_rect(slide, f"{sid}:background", 0, 0, 13.333333, 7.5, BLUE if dark else PAPER)
    fg = WHITE if dark else INK; muted = WHITE if dark else MUTE
    layout = item.get("layout", {})
    add_text(slide, f"{sid}:section", item.get("section", "main").upper(), .72, .38, 5.5, .25, 10, muted, MONO)
    tx, ty, tw, th = box(layout, "title", (.72, .75, 11.85, 1.25))
    add_text(slide, f"{sid}:title", item["title"], tx, ty, tw, th, float(layout.get("title", {}).get("size", 36 if item.get("kind") == "title" else 30)), fg, SERIF, True)
    body = item.get("body", [])
    body_lines = [body] if isinstance(body, str) else body
    if body_lines:
        bx, by, bw, bh = box(layout, "body", (.76, 2.08, 6.0 if item.get("images") else 11.6, 3.9))
        add_text(slide, f"{sid}:body", "\n".join(body_lines), bx, by, bw, bh, float(layout.get("body", {}).get("size", 21)), fg, SERIF)
    for index, image in enumerate(item.get("images", [])):
        count = len(item["images"]); iw = 5.35 / count
        if {"x", "y", "w", "h"}.issubset(image):
            ix, iy, image_w, image_h = (float(image[k]) for k in ("x", "y", "w", "h"))
        elif not body_lines:
            image_w = 11.85 / count - .12; ix, iy, image_h = .72 + index * (image_w + .12), 2.08, 4.75
        else:
            ix, iy, image_w, image_h = 7.15 + index * iw, 2.08, iw - .18, 3.65
        add_picture(slide, f"{sid}:image:{image['id']}", image, plan_path, ix, iy, image_w, image_h)
    for element in item.get("elements", []):
        x, y, w, h = (float(element.get(k, 0)) for k in ("x", "y", "w", "h"))
        name = f"{sid}:element:{element['id']}"
        if element["type"] == "box":
            add_rect(slide, name, x, y, w, h, RGBColor(*element.get("fill_rgb", [220, 218, 208])))
        else:
            add_text(slide, name, element.get("text", ""), x, y, w, h, float(element.get("size", 18)), fg)
    add_text(slide, f"{sid}:footer", footer_number, 11.25, 7.1, 1.35, .2, 9, muted, MONO, align=PP_ALIGN.RIGHT)
    add_notes(slide, notes_text(item))


def dependencies(slide: dict[str, Any], plan_path: Path) -> list[dict[str, str]]:
    deps = []
    for image in slide.get("images", []):
        if image.get("missing") is not True:
            path = asset_path(image["path"], plan_path); deps.append({"path": str(path), "sha256": file_hash(path)})
    for source in slide.get("sources", []):
        if source.get("missing") is not True and source.get("path"):
            path = asset_path(source["path"], plan_path); deps.append({"path": str(path), "sha256": file_hash(path)})
    return deps


def build(plan_path: Path, output: Path) -> int:
    plan_path = plan_path.resolve(); output = require_pptx_output(output)
    plan = load_json(plan_path); slides = validate_plan(plan, plan_path)
    # Asset bytes are build inputs even when the JSON path is unchanged.
    records = []
    main_total = sum(s.get("section", "main") == "main" for s in slides)
    appendix_total = len(slides) - main_total; main_n = appendix_n = 0
    for number, slide in enumerate(slides, 1):
        deps = dependencies(slide, plan_path)
        section = slide.get("section", "main")
        if section == "main":
            main_n += 1; display = footer = f"{main_n} / {main_total}"
        else:
            appendix_n += 1; display = footer = f"A{appendix_n} / A{appendix_total}"
        records.append({"id": slide["id"], "number": number, "section": section, "display_number": display, "footer_number": footer,
                        "dependencies": deps, "dependency_hash": sha256_bytes(canonical({"slide": slide, "deps": deps, "engine": VERSION}).encode("utf-8"))})
    protect_build_inputs(plan_path, records, output)
    plan_hash = sha256_bytes(canonical(plan).encode("utf-8"))
    build_hash = sha256_bytes(canonical({"plan": plan, "records": records, "engine": VERSION}).encode("utf-8"))
    state_file = state_path(output)
    old: dict[str, Any] | None = None
    if output.exists():
        if not state_file.is_file():
            raise PlanError(f"refusing to overwrite existing PPTX without state: {output}; choose a new output")
        old = load_json(state_file)
        if old.get("output_hash") != file_hash(output):
            raise PlanError(f"refusing to overwrite externally modified PPTX: {output}; choose a new output")
        if old.get("direct_edit"):
            raise PlanError("refusing to overwrite a directly edited PPTX; update the authoritative plan or choose a new output")
        if old.get("build_hash") == build_hash and not old.get("direct_edit"):
            print(f"UNCHANGED: {output}"); return 0
    prs = Presentation(); prs.slide_width, prs.slide_height = W, H
    for slide, record in zip(slides, records): build_slide(prs, slide, record["footer_number"], plan_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".pptx", delete=False) as tmp:
        temp_name = tmp.name
    try:
        prs.save(temp_name); shutil.move(temp_name, output)
    finally:
        if os.path.exists(temp_name): os.unlink(temp_name)
    old_hashes = {r.get("id"): r.get("dependency_hash") for r in (old or {}).get("slides", [])}
    changed = [r["id"] for r in records if old_hashes.get(r["id"]) != r["dependency_hash"]]
    if old and not changed: changed = [r["id"] for r in records]  # a direct/manual output is intentionally detached
    state = {"version": VERSION, "deck_id": plan["deck_id"], "plan_hash": plan_hash, "build_hash": build_hash,
             "rebuild_reason": "new-output" if old is None else "changed-plan-or-dependencies", "changed_slide_ids": changed,
             "output_hash": file_hash(output), "slides": records}
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"BUILT: {output} ({len(slides)} slides; changed: {', '.join(changed) or 'none'})"); return 0


def find_slide(prs, state: dict[str, Any] | None, slide_id: str | None, slide_number: int | None):
    if slide_id:
        if not state: raise PlanError("--slide-id needs the adjacent .deck-state.json")
        for record in state.get("slides", []):
            if record.get("id") == slide_id: return prs.slides[record["number"] - 1]
        raise PlanError(f"slide id not found: {slide_id}")
    if not slide_number or not 1 <= slide_number <= len(prs.slides): raise PlanError("invalid --slide-number")
    return prs.slides[slide_number - 1]


def save_edit(prs, input_path: Path, output: Path, source_state: dict[str, Any] | None) -> None:
    output = require_pptx_output(output)
    if output == input_path.resolve(): raise PlanError("direct edits require a distinct --output PPTX")
    if output.exists(): raise PlanError(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True); prs.save(output)
    if source_state is not None:
        copied = dict(source_state); copied["output_hash"] = file_hash(output)
        # A direct edit is intentional but no longer equals the JSON build plan.
        # A later build from that plan may therefore restore the planned display.
        copied["plan_hash"] = None
        copied["direct_edit"] = True
        state_path(output).write_text(json.dumps(copied, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trusted_state(input_path: Path, *, required: bool) -> dict[str, Any] | None:
    path = state_path(input_path)
    if not path.exists(): return None
    state = load_json(path)
    if state.get("output_hash") != file_hash(input_path):
        if required:
            raise PlanError("PPTX differs from its state; --slide-id is unsafe. Review it and use --slide-number for a separate output")
        return None
    return state


def replace_text_preserving_format(shape, text: str) -> None:
    tf = shape.text_frame
    paragraph = tf.paragraphs[0]
    if paragraph.runs:
        first = paragraph.runs[0]
        first.text = text
        for run in list(paragraph.runs[1:]): run._r.getparent().remove(run._r)
    else:
        paragraph.add_run().text = text
    # Keep the first paragraph's properties and its first run's font, and only
    # remove genuinely replaced text paragraphs.
    for extra in list(tf.paragraphs[1:]): extra._p.getparent().remove(extra._p)


def edit(args) -> int:
    input_path, output = Path(args.input), Path(args.output)
    if not input_path.is_file(): raise PlanError(f"input PPTX not found: {input_path}")
    prs = Presentation(input_path); state = trusted_state(input_path, required=bool(args.slide_id))
    slide = find_slide(prs, state, args.slide_id, args.slide_number)
    matches = [shape for shape in slide.shapes if shape.name == args.shape_name]
    if len(matches) != 1: raise PlanError(f"expected one shape named {args.shape_name!r}, found {len(matches)}")
    shape = matches[0]
    if not getattr(shape, "has_text_frame", False): raise PlanError("selected shape has no editable text")
    replace_text_preserving_format(shape, args.text)
    save_edit(prs, input_path, output, state); print(f"EDITED: {output}"); return 0


def replace_image(args) -> int:
    input_path, output, image = Path(args.input), Path(args.output), Path(args.image)
    if not input_path.is_file() or not image.is_file(): raise PlanError("input PPTX and replacement image must exist")
    prs = Presentation(input_path); state = trusted_state(input_path, required=bool(args.slide_id))
    slide = find_slide(prs, state, args.slide_id, args.slide_number)
    matches = [shape for shape in slide.shapes if shape.name == args.shape_name]
    if len(matches) != 1: raise PlanError(f"expected one shape named {args.shape_name!r}, found {len(matches)}")
    old = matches[0]
    if not hasattr(old, "image"): raise PlanError("selected shape is not a picture")
    old_parent = old._element.getparent(); old_index = list(old_parent).index(old._element)
    x, y, w, h = (old.left / Inches(1), old.top / Inches(1), old.width / Inches(1), old.height / Inches(1))
    new = slide.shapes.add_picture(str(image), old.left, old.top, old.width, old.height); new.name = old.name
    if args.fit == "preserve":
        old_w, old_h = old.image.size
        with Image.open(image) as replacement: new_w, new_h = replacement.size
        if abs(old_w / old_h - new_w / new_h) > 1e-6:
            raise PlanError("--fit preserve needs the same image aspect ratio; use --fit contain or --fit crop")
        new.crop_left, new.crop_right, new.crop_top, new.crop_bottom = old.crop_left, old.crop_right, old.crop_top, old.crop_bottom
    else:
        fit_picture(new, image, x, y, w, h, args.fit)
    old_parent.remove(new._element); old_parent.insert(old_index, new._element); old_parent.remove(old._element)
    save_edit(prs, input_path, output, state); print(f"REPLACED IMAGE: {output}"); return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="command", required=True)
    for name in ("check", "build"):
        cmd = sub.add_parser(name); cmd.add_argument("--plan", required=True)
        if name == "build": cmd.add_argument("--output", required=True)
    for name in ("edit", "replace-image"):
        cmd = sub.add_parser(name); cmd.add_argument("--input", required=True); cmd.add_argument("--output", required=True)
        selector = cmd.add_mutually_exclusive_group(required=True); selector.add_argument("--slide-id"); selector.add_argument("--slide-number", type=int)
        cmd.add_argument("--shape-name", required=True)
        if name == "edit": cmd.add_argument("--text", required=True)
        else:
            cmd.add_argument("--image", required=True)
            cmd.add_argument("--fit", choices=("preserve", "contain", "crop"), default="preserve")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "check":
            slides = validate_plan(load_json(Path(args.plan)), Path(args.plan)); print(f"PASS: {len(slides)} slides"); return 0
        if args.command == "build": return build(Path(args.plan), Path(args.output))
        if args.command == "edit": return edit(args)
        return replace_image(args)
    except PlanError as exc:
        print("ERROR: " + str(exc), file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
