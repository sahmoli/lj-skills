#!/usr/bin/env python3
"""Local-first full-text evidence search across anchored Markdown papers (lj-evidence v2.1).

Zero third-party dependencies (Python stdlib only).
Searches local private Markdown conversions (default: $LJ_PAPERS_DIR or ./papers)
created by `pdf_to_md.py` or JATS XML ingestion:
  - Physical PDF page anchors (`<!-- pdf-p0001 -->`) -> exact page + Obsidian PDF++ link
  - JATS XML semantic anchors (`<!-- jats-sec:methods -->`) -> section locator (NEVER fabricates PDF page 1)
  - Unanchored Markdown -> explicit `locator_type: "unanchored"`, `page: null`, empty `pdf_link`
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PAGE_ANCHOR_RE = re.compile(r"<!--\s*pdf-p(\d{4})\s*-->")
JATS_ANCHOR_RE = re.compile(r"<!--\s*jats-([a-z0-9_.:-]+)\s*-->", re.IGNORECASE)


def default_papers_dir() -> str:
    env_dir = os.environ.get("LJ_PAPERS_DIR", "").strip()
    if env_dir:
        return env_dir
    return str(Path.cwd() / "papers")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw_fm = text[3:end].strip()
    body = text[end + 4 :]
    meta: dict[str, str] = {}
    for line in raw_fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def split_sections(body: str) -> list[dict[str, Any]]:
    """Split body into anchored chunks without ever fabricating PDF page numbers."""
    pdf_matches = list(PAGE_ANCHOR_RE.finditer(body))
    if pdf_matches:
        out: list[dict[str, Any]] = []
        for idx, m in enumerate(pdf_matches):
            pno = int(m.group(1))
            start = m.end()
            end = pdf_matches[idx + 1].start() if idx + 1 < len(pdf_matches) else len(body)
            out.append({
                "locator_type": "pdf-page",
                "page": pno,
                "section": "",
                "anchor": f"<!-- pdf-p{pno:04d} -->",
                "text": body[start:end].strip(),
            })
        return out

    jats_matches = list(JATS_ANCHOR_RE.finditer(body))
    if jats_matches:
        out = []
        for idx, m in enumerate(jats_matches):
            sec = m.group(1)
            start = m.end()
            end = jats_matches[idx + 1].start() if idx + 1 < len(jats_matches) else len(body)
            out.append({
                "locator_type": "jats-section",
                "page": None,
                "section": sec,
                "anchor": f"<!-- jats-{sec} -->",
                "text": body[start:end].strip(),
            })
        return out

    return [{
        "locator_type": "unanchored",
        "page": None,
        "section": "",
        "anchor": "",
        "text": body.strip(),
    }]


def tokenize_query(query: str) -> tuple[str, list[str]]:
    phrase = re.sub(r"\s+", " ", query.strip().lower())
    terms = [t for t in re.findall(r"[a-z0-9\u4e00-\u9fff]+", phrase) if len(t) >= 2]
    if not terms and phrase:
        terms = [phrase]
    return phrase, list(dict.fromkeys(terms))


def make_snippet(text: str, terms: list[str], phrase: str, max_chars: int = 340) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    low = flat.lower()
    pos = low.find(phrase) if phrase else -1
    if pos == -1:
        for t in terms:
            p = low.find(t)
            if p != -1:
                pos = p
                break
    if pos == -1:
        pos = 0
    start = max(0, pos - 110)
    end = min(len(flat), start + max_chars)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(flat) else ""
    return f"{prefix}{flat[start:end].strip()}{suffix}"


def search_corpus(corpus_dir: Path, query: str, limit: int = 12, slug_filter: str = "") -> list[dict[str, Any]]:
    phrase, terms = tokenize_query(query)
    if not terms:
        return []
    hits: list[dict[str, Any]] = []
    for md_path in sorted(corpus_dir.glob("*.md")):
        if md_path.name.startswith("_"):
            continue
        if slug_filter and slug_filter.lower() not in md_path.stem.lower():
            continue
        try:
            raw = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        meta, body = parse_frontmatter(raw)
        slug = meta.get("slug") or md_path.stem
        pdf_file = meta.get("pdf_file") or ""
        has_pdf = bool(pdf_file) or (corpus_dir / f"{slug}.pdf").exists()
        if not pdf_file and has_pdf:
            pdf_file = f"10_raw/papers/{slug}.pdf"
        source_format = meta.get("source_format") or ("pdf" if has_pdf else "markdown")

        for chunk in split_sections(body):
            chunk_text = chunk["text"]
            low = chunk_text.lower()
            matched_terms = [t for t in terms if t in low]
            if not matched_terms:
                continue
            tf_score = sum(min(low.count(t), 5) for t in matched_terms)
            coverage_bonus = (len(matched_terms) / len(terms)) * 5.0
            phrase_bonus = 6.0 if (len(terms) > 1 and phrase in low) else 0.0
            score = round(tf_score + coverage_bonus + phrase_bonus, 2)

            pno = chunk["page"]
            pdf_link = f"[[{pdf_file}#page={pno}]]" if (chunk["locator_type"] == "pdf-page" and pno is not None and has_pdf) else ""
            hits.append({
                "score": score,
                "slug": slug,
                "title": meta.get("title") or slug,
                "authors_year": meta.get("authors_year") or "",
                "doi": meta.get("doi") or "",
                "source_format": source_format,
                "locator_type": chunk["locator_type"],
                "page": pno,
                "section": chunk["section"],
                "anchor": chunk["anchor"],
                "pdf_link": pdf_link,
                "md_path": str(md_path),
                "matched_terms": matched_terms,
                "snippet": make_snippet(chunk_text, matched_terms, phrase),
            })
    hits.sort(key=lambda h: (h["score"], len(h["matched_terms"])), reverse=True)
    return hits[:limit]


def main() -> int:
    ap = argparse.ArgumentParser(description="Search local anchored Markdown papers before hitting external APIs.")
    ap.add_argument("--query", required=True, help="Search terms or exact phrase")
    ap.add_argument("--dir", default=default_papers_dir(), help="Directory of paper .md files (default: $LJ_PAPERS_DIR or ./papers)")
    ap.add_argument("--slug", default="", help="Optional substring filter on paper filename/slug")
    ap.add_argument("--limit", type=int, default=12, help="Max hits to return (default: 12)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = ap.parse_args()

    corpus_dir = Path(args.dir)
    if not corpus_dir.is_dir():
        print(f"Corpus directory not found: {corpus_dir}", file=sys.stderr)
        return 2

    hits = search_corpus(corpus_dir, args.query, limit=args.limit, slug_filter=args.slug)
    if args.json:
        print(json.dumps({"query": args.query, "corpus_dir": str(corpus_dir), "hits": hits}, ensure_ascii=False, indent=2))
        return 0

    if not hits:
        print(f"No local corpus hits for `{args.query}` in `{corpus_dir}`.")
        return 0

    print(f"### Local Corpus Hits for `{args.query}` ({len(hits)} matches)\n")
    for h in hits:
        doi_str = f" · `DOI: {h['doi']}`" if h["doi"] else ""
        if h["locator_type"] == "pdf-page" and h["page"] is not None:
            loc = f"p.{h['page']}"
            link = f" {h['pdf_link']}" if h["pdf_link"] else ""
        elif h["locator_type"] == "jats-section":
            loc = f"jats:{h['section']} (no PDF page)"
            link = ""
        else:
            loc = "unanchored (no PDF page)"
            link = ""
        print(f"- **{h['slug']}** ({loc}, score={h['score']}){link}{doi_str}")
        print(f"  > {h['snippet']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
