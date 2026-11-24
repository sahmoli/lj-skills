#!/usr/bin/env python3
"""Convert local private PDFs into Obsidian / D:\\hub\\10_raw\\papers\\ page-anchored Markdown (v2).

Compatible with D:\\hub\\Reading.base and PDF++ (`[[10_raw/papers/<slug>.pdf#page=N|...]]`),
plus stable physical-page HTML anchors (`<!-- pdf-p0001 -->`) and SHA-256 provenance.

Engines:
  - `pymupdf` (default, fast CPU): requires PyMuPDF (`pymupdf`) in D:\\tools\\venvs\\lj-evidence.
  - `docling` (optional high-fidelity): MIT-licensed IBM Docling for complex tables, equations,
    or scanned legacy PDFs (`pip install docling` into the isolated venv on demand).

Markdown output is a search/reading view only; verify critical numbers, denominators, figures,
and qualifiers visually against the original PDF page before finalizing claims.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def default_papers_dir() -> str:
    env_dir = os.environ.get("LJ_PAPERS_DIR", "").strip()
    if env_dir:
        return env_dir
    return str(Path.cwd() / "papers")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pages_pymupdf(pdf_path: Path) -> tuple[list[str], str]:
    try:
        import pymupdf  # type: ignore
    except ImportError:
        print(
            "ERROR: PyMuPDF (`pymupdf`) is not installed in this Python interpreter.\n"
            "Use the isolated evidence venv, e.g.:\n"
            r"  D:\tools\venvs\lj-evidence\Scripts\python.exe pdf_to_md.py ...",
            file=sys.stderr,
        )
        raise SystemExit(2)

    doc = pymupdf.open(pdf_path)
    methods: set[str] = set()
    pages: list[str] = []
    for i in range(len(doc)):
        text = ""
        method = ""
        if hasattr(doc, "to_markdown"):
            try:
                try:
                    md = doc.to_markdown(pages=[i], use_ocr=False)
                except TypeError:
                    md = doc.to_markdown(pages=[i])
                if isinstance(md, str) and md.strip():
                    text = md.strip()
                    method = f"pymupdf-{pymupdf.__version__}:Document.to_markdown"
            except Exception:
                pass
        if not text:
            page = doc[i]
            blocks = page.get_text("blocks", sort=True)
            paras: list[str] = []
            for b in blocks:
                if len(b) >= 5 and isinstance(b[4], str):
                    txt = re.sub(r"[ \t]+\n", "\n", b[4].strip())
                    txt = re.sub(r"(?<!\n)\n(?!\n)", " ", txt)
                    if txt:
                        paras.append(txt)
            if paras:
                text = "\n\n".join(paras)
                method = f"pymupdf-{pymupdf.__version__}:blocks-sort"
            else:
                text = page.get_text("text").strip()
                method = f"pymupdf-{pymupdf.__version__}:text"
        methods.add(method)
        pages.append(text)
    doc.close()
    return pages, ", ".join(sorted(methods))


def extract_pages_docling(pdf_path: Path) -> tuple[list[str], str]:
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except ImportError:
        print(
            "ERROR: `--engine docling` requested, but `docling` is not installed in this venv.\n"
            "Install it on demand in the isolated evidence venv:\n"
            r"  D:\tools\venvs\lj-evidence\Scripts\python.exe -m pip install docling",
            file=sys.stderr,
        )
        raise SystemExit(2)

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document
    page_nos = sorted(doc.pages.keys()) if hasattr(doc, "pages") and doc.pages else [1]
    pages: list[str] = []
    for pno in page_nos:
        try:
            md = doc.export_to_markdown(page_no=pno)
        except TypeError:
            md = doc.export_to_markdown() if pno == page_nos[0] else ""
        pages.append((md or "").strip())
    return pages, "docling:DocumentConverter"


def yaml_quote(val: str) -> str:
    escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def convert_one(
    pdf_path: Path,
    meta: dict[str, Any],
    rel_prefix: str = "10_raw/papers",
    overwrite: bool = False,
    engine: str = "pymupdf",
) -> dict[str, Any]:
    slug = meta.get("slug") or pdf_path.stem
    md_path = pdf_path.with_suffix(".md")
    if md_path.exists() and not overwrite:
        print(f"[SKIP]  {md_path.name} already exists (pass --overwrite to regenerate)")
        return {"slug": slug, "status": "skipped", "md_path": str(md_path)}

    pdf_sha = sha256_file(pdf_path)
    if engine == "docling":
        pages, converter_str = extract_pages_docling(pdf_path)
    else:
        pages, converter_str = extract_pages_pymupdf(pdf_path)

    page_count = len(pages)
    total_chars = sum(len(re.sub(r"\s+", "", p)) for p in pages)
    avg_chars = (total_chars / page_count) if page_count else 0.0
    needs_ocr_check = page_count > 0 and avg_chars < 120
    rel_pdf = f"{rel_prefix}/{pdf_path.name}"
    page_sections: list[str] = []
    for i, text in enumerate(pages):
        pno = i + 1
        page_sections.append(
            f"## Page {pno} · [[{rel_pdf}#page={pno}|打开原版 PDF 第 {pno} 页]]\n"
            f"<!-- pdf-p{pno:04d} -->\n\n"
            f"{text or '*(本页无可提取文本，可能为扫描图或纯图形页，请直接核对原版 PDF)*'}\n"
        )

    title = meta.get("title") or slug
    authors_year = meta.get("authors_year") or ""
    venue = meta.get("venue") or ""
    doi = meta.get("doi") or ""
    serves = meta.get("serves") or "visual-notes"
    why_read = meta.get("why_read") or ""
    today = dt.date.today().isoformat()

    fm_lines = [
        "---",
        f"slug: {slug}",
        f"title: {yaml_quote(title)}",
        f"authors_year: {yaml_quote(authors_year)}",
        f"venue: {yaml_quote(venue)}",
        f"doi: {yaml_quote(doi)}",
        "source_format: pdf",
        f"serves: {serves}",
        "read_status: ready",
        "provenance: source",
        "privacy: private",
        f"pdf_file: {yaml_quote(rel_pdf)}",
        f"note_file: {yaml_quote(f'20_wiki/notes/{slug}.md')}",
        f"page_count: {page_count}",
        f"pdf_sha256: {yaml_quote(pdf_sha)}",
        f"converter: {yaml_quote(converter_str)}",
        f"updated: {today}",
    ]
    if needs_ocr_check:
        fm_lines.append("needs_ocr_check: true")
    if why_read:
        fm_lines.append(f"why_read: {yaml_quote(why_read)}")
    fm_lines.append("---")

    header = [
        f"# {authors_year + ' · ' if authors_year else ''}{title}",
        "",
        f"> - 原版文件：[[{rel_pdf}|打开原版 PDF]]（`DOI: {doi or '无'}`，共 {page_count} 页，`SHA-256: {pdf_sha[:12]}`）",
        f"> - 我的笔记：[[20_wiki/notes/{slug}|✍️ 打开 / 新建我的精读笔记]]（按住 Ctrl 点击可右侧分屏配 `PDF++`）",
        "> - **检索视图提醒**：本 Markdown 仅用于全文检索与定位；引用关键数字、分母、图注与限定语前，请点上方页码直链回原版 PDF 视觉复核。",
        "",
        "---",
        "",
    ]

    full_md = "\n".join(fm_lines) + "\n\n" + "\n".join(header) + "\n".join(page_sections)
    md_path.write_text(full_md, encoding="utf-8")
    print(f"[CONV]  {md_path.name} ({page_count} pages, {converter_str})")
    if needs_ocr_check and engine != "docling":
        print(f"[HINT]  {md_path.name}: low text density ({avg_chars:.0f} chars/page) — likely scan; consider `--engine docling --overwrite`")
    return {
        "slug": slug,
        "status": "converted",
        "md_path": str(md_path),
        "page_count": page_count,
        "avg_chars_per_page": round(avg_chars, 1),
        "needs_ocr_check": needs_ocr_check,
        "pdf_sha256": pdf_sha,
        "converter": converter_str,
        "extracted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert local PDFs into page-anchored Obsidian Markdown.")
    ap.add_argument("--pdf", action="append", default=[], help="PDF path to convert (repeatable)")
    ap.add_argument("--manifest", help="Optional JSON manifest matching fetch_oa.py schema")
    ap.add_argument("--papers-dir", default=default_papers_dir(), help="Papers directory (default: $LJ_PAPERS_DIR or ./papers)")
    ap.add_argument("--engine", choices=["pymupdf", "docling"], default="pymupdf", help="Extraction engine (default: pymupdf; use docling for dense tables/equations/scans)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing .md files")
    args = ap.parse_args()

    papers_dir = Path(args.papers_dir)
    ledger = papers_dir / "_provenance.jsonl"
    results: list[dict[str, Any]] = []

    if args.manifest:
        raw = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
        items = raw if isinstance(raw, list) else raw.get("papers", [])
        for item in items:
            slug = item.get("slug")
            if not slug:
                continue
            pdf_path = papers_dir / f"{slug}.pdf"
            if pdf_path.exists():
                res = convert_one(pdf_path, item, overwrite=args.overwrite, engine=args.engine)
                results.append(res)
                if res["status"] == "converted":
                    with ledger.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"event": "pdf_to_md", **res}, ensure_ascii=False) + "\n")

    for p in args.pdf:
        pdf_path = Path(p)
        if pdf_path.exists():
            res = convert_one(pdf_path, {"slug": pdf_path.stem}, overwrite=args.overwrite, engine=args.engine)
            results.append(res)

    print(f"\nConverted={sum(1 for r in results if r['status'] == 'converted')}, Skipped={sum(1 for r in results if r['status'] == 'skipped')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
