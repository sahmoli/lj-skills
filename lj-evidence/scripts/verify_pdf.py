#!/usr/bin/env python3
"""Three-state semantic PDF verifier for lj-evidence (v2.1).

Prevents false successes (Cloudflare HTML, truncated downloads, publisher media kits,
wrong articles, and correction/erratum notices masquerading as the target paper)
without falsely discarding valid 1-page letters, image-only scans, or postprints.

Outcomes (`status`):
  - `verified`:     structure valid + semantic match + not a correction/retraction notice.
  - `needs-review`: structure valid, but uncertain identity (low text layer / scan,
                    possible correction/erratum notice, missing text match on postprint,
                    or ambiguous short document). Route to `_needs_review/`, never silently
                    file as verified.
  - `rejected`:     not a PDF, too small (<20 KB), truncated (missing `%%EOF`), unreadable,
                    or clear wrong article (e.g., publisher media kit with rich text and
                    near-zero title/DOI/author overlap). Route to `_rejected/`.

Exit code:
  0 -> verified
  1 -> rejected
  3 -> needs-review (caller can distinguish review vs reject)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

STOPWORDS = {
    "the", "a", "an", "of", "on", "in", "for", "and", "to", "is", "are", "was", "were",
    "with", "from", "by", "at", "as", "or", "via", "into", "their", "its", "this", "that",
    "using", "study", "analysis", "effects", "effect", "review", "towards", "toward",
}

CORRECTION_RE = re.compile(
    r"(?:^|\n|\s)(?:author\s+correction|publisher\s+correction|corrigendum|erratum|"
    r"retraction\s+note|retraction\s+notice|expression\s+of\s+concern|addendum\s+to)\b",
    re.IGNORECASE,
)

MEDIA_KIT_RE = re.compile(
    r"\b(?:media\s+kit|advertising\s+rates|rate\s+card|sponsorship\s+opportunities|"
    r"editorial\s+calendar|circulation\s+and\s+readership)\b",
    re.IGNORECASE,
)

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>\]\)]+", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """NFKC-normalize, heal line-break hyphenations, and lowercase alphanumerics."""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text)
    s = s.replace("\u00ad", "").replace("\u2010", "-").replace("\u2011", "-")
    # Rejoin hyphenated line wraps such as "conser-\nvation" -> "conservation"
    s = re.sub(r"([A-Za-z])-\s*\n\s*([A-Za-z])", r"\1\2", s)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s.lower()).strip()


def clean_doi(doi: str) -> str:
    s = (doi or "").strip()
    s = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", s, flags=re.I)
    return s.strip().rstrip(".,;)")


def title_tokens(title: str) -> list[str]:
    normed = normalize_text(title)
    toks = [w for w in normed.split() if len(w) > 4 and w not in STOPWORDS]
    if not toks:
        toks = [w for w in normed.split() if len(w) >= 3 and w not in STOPWORDS]
    return list(dict.fromkeys(toks))


def extract_author_surname(authors_year: str) -> str:
    s = (authors_year or "").strip()
    if not s:
        return ""
    # Handle "Smith et al. (2025)", "Smith, J. 2025", "Smith 2025"
    first = re.split(r"\s+et\s+al\.?|[,(&\d]", s, maxsplit=1)[0].strip()
    parts = [p for p in normalize_text(first).split() if len(p) >= 2]
    return parts[-1] if parts else ""


def extract_year(authors_year: str, year: str | int | None = None) -> str:
    if year:
        m = re.search(r"\b(19|20)\d{2}\b", str(year))
        if m:
            return m.group(0)
    m = re.search(r"\b(19|20)\d{2}\b", authors_year or "")
    return m.group(0) if m else ""


def extract_pdf_head_info(pdf: Path) -> dict[str, Any]:
    """Extract first-2-page text and any embedded DOI/title candidates for ingestion/verification."""
    info: dict[str, Any] = {
        "pages": 0,
        "head_text": "",
        "first_page_top": "",
        "extracted_chars": 0,
        "detected_dois": [],
        "pdf_title_meta": "",
        "error": "",
    }
    try:
        import pymupdf  # type: ignore
    except ImportError:
        info["error"] = "pymupdf-missing"
        return info

    try:
        doc = pymupdf.open(pdf)
        info["pages"] = len(doc)
        meta = doc.metadata or {}
        info["pdf_title_meta"] = (meta.get("title") or "").strip()
        chunks: list[str] = []
        for i in range(min(2, len(doc))):
            txt = doc[i].get_text("text") or ""
            chunks.append(txt)
            if i == 0:
                info["first_page_top"] = txt[:900]
        doc.close()
        head = "\n".join(chunks)
        info["head_text"] = head
        info["extracted_chars"] = len(re.sub(r"\s+", "", head))
        found_dois = [clean_doi(m.group(0)) for m in DOI_RE.finditer(head)]
        info["detected_dois"] = list(dict.fromkeys(d for d in found_dois if d))
    except Exception as exc:
        info["error"] = f"unreadable: {exc}"
    return info


def validate(
    pdf: Path,
    title: str = "",
    doi: str = "",
    authors_year: str = "",
    year: str | int | None = None,
    min_pages: int = 1,
    min_bytes: int = 20_000,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "status": "rejected",  # verified | needs-review | rejected
        "pdf": str(pdf),
        "bytes": 0,
        "pages": 0,
        "magic": False,
        "eof": False,
        "extracted_chars": 0,
        "doi_found": False,
        "title_coverage": None,
        "author_found": False,
        "year_found": False,
        "possible_correction": False,
        "short_paper": False,
        "detected_dois": [],
        "reason": "",
    }
    if not pdf.exists():
        result["reason"] = "missing-file"
        return result

    data = pdf.read_bytes()
    result["bytes"] = len(data)
    result["magic"] = data[:5] == b"%PDF-"
    result["eof"] = b"%%EOF" in data[-4096:]

    if not result["magic"]:
        result["reason"] = "not-pdf"
        return result
    if len(data) < min_bytes:
        result["reason"] = f"too-small ({len(data)} bytes)"
        return result
    if not result["eof"]:
        result["reason"] = "truncated-no-eof"
        return result

    head_info = extract_pdf_head_info(pdf)
    if head_info["error"]:
        result["reason"] = head_info["error"]
        return result

    pages = int(head_info["pages"])
    result["pages"] = pages
    result["extracted_chars"] = int(head_info["extracted_chars"])
    result["detected_dois"] = head_info["detected_dois"]
    result["short_paper"] = pages == 1

    if pages < min_pages:
        result["reason"] = f"too-few-pages ({pages})"
        return result

    head_raw = head_info["head_text"]
    first_top = head_info["first_page_top"]
    # Explicit media-kit / ad brochure check (always reject unless target title explicitly mentions media kit)
    if MEDIA_KIT_RE.search(first_top) and "media kit" not in (title or "").lower():
        result["reason"] = "wrong-article (publisher media kit)"
        return result

    # Low text layer (likely scanned legacy PDF): NEVER falsely reject as wrong-article!
    if result["extracted_chars"] < 100:
        result["status"] = "needs-review"
        result["reason"] = f"needs-ocr-review (low text layer: {result['extracted_chars']} chars)"
        return result

    # Detect Correction / Erratum / Corrigendum / Retraction notices on page 1 top
    target_is_correction = bool(CORRECTION_RE.search(title or ""))
    if CORRECTION_RE.search(first_top[:600]) and not target_is_correction:
        result["possible_correction"] = True

    hn = normalize_text(head_raw + " " + head_info["pdf_title_meta"])
    target_doi = clean_doi(doi)
    if target_doi:
        det_lower = {d.lower() for d in head_info["detected_dois"]}
        dehyph = re.sub(r"-\s*\n\s*", "-", head_raw + " " + head_info["pdf_title_meta"])
        exact_pat = re.compile(rf"(?<![0-9A-Za-z./-]){re.escape(target_doi)}(?![0-9A-Za-z._/-])", re.I)
        result["doi_found"] = (target_doi.lower() in det_lower) or bool(exact_pat.search(dehyph))

    toks = title_tokens(title)
    coverage: float | None = None
    if toks:
        hit = sum(1 for t in toks if t in hn)
        coverage = round(hit / len(toks), 3)
        result["title_coverage"] = coverage

    surname = extract_author_surname(authors_year)
    yr = extract_year(authors_year, year)
    if surname:
        result["author_found"] = surname in hn
    if yr:
        result["year_found"] = yr in hn

    # If correction/erratum notice detected for a non-correction target, always route to needs-review
    if result["possible_correction"]:
        result["status"] = "needs-review"
        result["reason"] = "possible-correction-notice (correction/erratum header detected on page 1)"
        return result

    # If no metadata was supplied at all, structural checks passed -> verified
    has_expectations = bool(target_doi or toks or surname)
    if not has_expectations:
        result["ok"] = True
        result["status"] = "verified"
        result["reason"] = "ok (structure-only; no metadata supplied)"
        return result

    # Flexible semantic pass criteria:
    # 1) DOI matched AND (no title supplied OR title coverage >= 0.35)
    # 2) Title token coverage >= 0.55 (handles postprints/preprints without publisher DOI)
    # 3) Author surname + year matched AND title coverage >= 0.35
    doi_pass = result["doi_found"] and (coverage is None or coverage >= 0.35)
    title_pass = coverage is not None and coverage >= 0.55
    author_year_pass = (
        result["author_found"]
        and result["year_found"]
        and (coverage is None or coverage >= 0.35)
    )

    if doi_pass or title_pass or author_year_pass:
        result["ok"] = True
        result["status"] = "verified"
        result["reason"] = "ok"
        return result

    # Distinguish uncertain / borderline match from clear wrong-article
    if result["doi_found"] or (coverage is not None and coverage >= 0.30) or (result["author_found"] and result["year_found"]):
        result["status"] = "needs-review"
        result["reason"] = (
            f"uncertain-identity (doi_found={result['doi_found']}, "
            f"title_coverage={coverage}, author={result['author_found']}, year={result['year_found']})"
        )
        return result

    result["status"] = "rejected"
    result["reason"] = (
        f"wrong-article (doi_found={result['doi_found']}, "
        f"title_coverage={coverage if coverage is not None else 'n/a'})"
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Three-state semantic PDF verifier for lj-evidence (v2.1).")
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--title", default="")
    ap.add_argument("--doi", default="")
    ap.add_argument("--authors-year", default="")
    ap.add_argument("--year", default="")
    ap.add_argument("--min-pages", type=int, default=1)
    ap.add_argument("--min-bytes", type=int, default=20_000)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    res = validate(
        args.pdf,
        title=args.title,
        doi=args.doi,
        authors_year=args.authors_year,
        year=args.year or None,
        min_pages=args.min_pages,
        min_bytes=args.min_bytes,
    )
    text = json.dumps(res, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    if res["status"] == "verified":
        return 0
    if res["status"] == "needs-review":
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
