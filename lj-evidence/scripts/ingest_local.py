#!/usr/bin/env python3
"""Safe local PDF ingestor for user-downloaded or Zotero-exported papers (lj-evidence v2.1).

Closes the manual "downloaded into Downloads/ or Zotero" loop cleanly:
  1. Scans an opt-in source folder (e.g., ~/Downloads or Zotero export dir), skipping
     incomplete browser downloads (`.crdownload`, `.part`, `.tmp`).
  2. Default mode is read-only COPY (never mutates/moves originals unless `--move` is explicitly
     passed AND path is NOT inside a Zotero storage directory).
  3. Extracts DOI + first-2-page text from each PDF, deduplicates by SHA-256 against
     `_provenance.jsonl` and existing files in `--out-dir`.
  4. Matches against unchecked `[ ]` entries in `--wanted-note` / `--scan-inbox`:
     - Exact DOI match: runs three-state `verify_pdf.py` -> copies to canonical `{slug}.pdf`
       (never silently overwrites a different SHA-256) -> converts via `pdf_to_md.py` ->
       appends `_provenance.jsonl` -> ONLY AFTER all succeed, atomically (`os.replace`)
       marks `[ ]` -> `[x]` in the wanted note!
     - Fuzzy title-only match (no exact DOI): copies into `_pending_match/` for human confirmation
       and NEVER auto-checks `[x]`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fetch_oa import default_inbox_dir, default_papers_dir, parse_wanted_note  # noqa: E402
from pdf_to_md import convert_one  # noqa: E402
from verify_pdf import clean_doi, extract_pdf_head_info, normalize_text, title_tokens, validate as validate_pdf  # noqa: E402

INCOMPLETE_SUFFIXES = (".crdownload", ".part", ".tmp", ".download")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_zotero_storage(path: Path) -> bool:
    parts = [p.lower() for p in path.resolve().parts]
    return "zotero" in parts and "storage" in parts


def load_known_hashes(out_dir: Path) -> dict[str, str]:
    """Return {sha256: slug} from `_provenance.jsonl` and existing PDFs."""
    known: dict[str, str] = {}
    ledger = out_dir / "_provenance.jsonl"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                h = obj.get("sha256") or obj.get("pdf_sha256")
                if h:
                    known[h] = obj.get("slug") or obj.get("pdf_file") or ""
            except Exception:
                continue
    return known


def atomic_check_off_wanted(note_path: Path, slug: str, doi: str) -> bool:
    """Atomically mark `- [ ]` -> `- [x]` for an exact verified DOI + slug match."""
    raw = note_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw.splitlines()
    changed = False
    target_doi = clean_doi(doi).lower()

    doi_pat = re.compile(rf"(?<![0-9A-Za-z./-]){re.escape(target_doi)}(?![0-9A-Za-z._/-])", re.I) if target_doi else None
    for i, line in enumerate(lines):
        if not re.match(r"^\s*-\s*\[\s*\]\s+", line):
            continue
        end = i + 1
        while end < len(lines) and not re.match(r"^\s*-\s*\[", lines[end]) and not lines[end].startswith("#"):
            end += 1
        block = "\n".join(lines[i:end])
        slug_hit = bool(slug and (f"`{slug.lower()}.pdf`" in line.lower() or f"**{slug.lower()}.pdf**" in line.lower()))
        doi_hit = bool(doi_pat and doi_pat.search(block))
        if doi_hit and (slug_hit or not slug):
            lines[i] = re.sub(r"^(\s*-\s*)\[\s*\]", r"\1[x]", line, count=1)
            changed = True
            break

    if not changed:
        return False

    tmp = note_path.with_suffix(note_path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, note_path)
    return True


def find_match(
    detected_dois: list[str],
    head_norm: str,
    wanted_items: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    """Return ('exact_doi' | 'fuzzy_title' | 'none', matched_item)."""
    det_set = {clean_doi(d).lower() for d in detected_dois if d}
    # 1. Exact DOI match (safe for auto-checkoff)
    for w in wanted_items:
        wdoi = clean_doi(w.get("doi") or "").lower()
        if wdoi and wdoi in det_set:
            return "exact_doi", w
        # Strict exact DOI match against detected header DOIs only
        if wdoi and wdoi in det_set:
            return "exact_doi", w

    # 2. Fuzzy title-only match (NEVER auto-checkoff; route to _pending_match/)
    best_cov = 0.0
    best_item: dict[str, Any] | None = None
    for w in wanted_items:
        toks = title_tokens(w.get("title") or "")
        if len(toks) < 3:
            continue
        hit = sum(1 for t in toks if t in head_norm)
        cov = hit / len(toks)
        if cov > best_cov:
            best_cov = cov
            best_item = w
    if best_cov >= 0.70 and best_item is not None:
        return "fuzzy_title", best_item

    return "none", None


def main() -> int:
    ap = argparse.ArgumentParser(description="Safely ingest user-downloaded / Zotero PDFs into papers dir (lj-evidence v2.1).")
    ap.add_argument("--from-dir", type=Path, default=Path.home() / "Downloads", help="Source directory to scan (default: ~/Downloads)")
    ap.add_argument("--pdf", action="append", default=[], help="Explicit PDF file(s) to ingest (repeatable)")
    ap.add_argument("--out-dir", type=Path, default=Path(default_papers_dir()), help="Target papers dir (default: $LJ_PAPERS_DIR or ./papers)")
    ap.add_argument("--wanted-note", action="append", default=[], help="Wanted note(s) to match and check off")
    ap.add_argument("--scan-inbox", action="store_true", help="Match against all *wanted*.md files in --inbox-dir")
    ap.add_argument("--inbox-dir", type=Path, default=Path(default_inbox_dir()), help="Inbox dir for --scan-inbox")
    ap.add_argument("--move", action="store_true", help="Move instead of copy (FORBIDDEN inside Zotero/storage)")
    ap.add_argument("--engine", choices=["pymupdf", "docling"], default="pymupdf", help="Markdown conversion engine")
    ap.add_argument("--dry-run", action="store_true", help="Preview matches without copying, converting, or editing wanted notes")
    ap.add_argument("--include-unmatched", action="store_true", help="Also ingest PDFs with a detected DOI even if not in any wanted note")
    args = ap.parse_args()

    if args.move and is_zotero_storage(args.from_dir):
        print("ERROR: --move is forbidden inside Zotero/storage to prevent corrupting Zotero's local index. Use copy mode.", file=sys.stderr)
        return 2

    wanted_items: list[dict[str, Any]] = []
    for wn in args.wanted_note:
        wp = Path(wn)
        if wp.exists():
            wanted_items.extend(parse_wanted_note(wp))
    if args.scan_inbox and args.inbox_dir.is_dir():
        for wp in sorted(args.inbox_dir.glob("*wanted*.md")):
            wanted_items.extend(parse_wanted_note(wp))

    source_pdfs: list[Path] = []
    if args.pdf:
        for p in args.pdf:
            pp = Path(p)
            if pp.is_file():
                source_pdfs.append(pp)
    elif args.from_dir.is_dir():
        for p in sorted(args.from_dir.glob("*.pdf")):
            if any(p.name.lower().endswith(suf) for suf in INCOMPLETE_SUFFIXES):
                continue
            source_pdfs.append(p)

    if not source_pdfs:
        print(f"No PDFs found to inspect in {args.from_dir}.")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    known_hashes = load_known_hashes(args.out_dir)
    ledger = args.out_dir / "_provenance.jsonl"
    pending_dir = args.out_dir / "_pending_match"
    review_dir = args.out_dir / "_needs_review"

    ingested = 0
    duplicates = 0
    pending = 0
    skipped = 0

    for src in source_pdfs:
        if args.move and is_zotero_storage(src.parent):
            print(f"[GUARD] Refusing --move on Zotero file {src.name}; skipping.")
            skipped += 1
            continue

        digest = sha256_file(src)
        if digest in known_hashes:
            known_slug = Path(known_hashes[digest]).stem
            if not args.dry_run:
                for w in wanted_items:
                    if w.get("slug") == known_slug and w.get("doi") and w.get("wanted_note"):
                        atomic_check_off_wanted(Path(w["wanted_note"]), known_slug, w["doi"])
            print(f"[DUP]   {src.name} already in corpus as `{known_hashes[digest]}` (sha256={digest[:12]})")
            duplicates += 1
            continue

        head = extract_pdf_head_info(src)
        if head["error"]:
            print(f"[SKIP]  {src.name}: {head['error']}")
            skipped += 1
            continue

        head_norm = normalize_text(head["head_text"] + " " + head["pdf_title_meta"])
        mtype, match = find_match(head["detected_dois"], head_norm, wanted_items)

        if mtype == "none":
            if not args.include_unmatched or not head["detected_dois"]:
                skipped += 1
                continue
            slug = re.sub(r"[^a-z0-9-]+", "-", src.stem.lower()).strip("-") or f"paper-{digest[:8]}"
            match = {"slug": slug, "doi": head["detected_dois"][0], "title": head["pdf_title_meta"] or slug, "authors_year": "", "venue": ""}
            mtype = "unmatched_doi"

        assert match is not None
        slug = match.get("slug") or re.sub(r"[^a-z0-9-]+", "-", src.stem.lower()).strip("-")

        if mtype == "fuzzy_title":
            print(f"[PEND]  {src.name} -> fuzzy title match `{slug}` (no exact DOI); routing to _pending_match/ (will NOT auto-check wanted)")
            if not args.dry_run:
                pending_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, pending_dir / f"{slug}__from__{src.name}")
            pending += 1
            continue

        # Exact DOI match (or --include-unmatched)
        v = validate_pdf(
            src,
            title=match.get("title") or "",
            doi=match.get("doi") or "",
            authors_year=match.get("authors_year") or "",
        )
        if v["status"] != "verified":
            print(f"[REV]   {src.name} matched `{slug}` but verify_pdf={v['status']} ({v['reason']}); routing to _needs_review/")
            if not args.dry_run:
                review_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, review_dir / f"{slug}__from__{src.name}")
            pending += 1
            continue

        target_pdf = args.out_dir / f"{slug}.pdf"
        if target_pdf.exists():
            existing_sha = sha256_file(target_pdf)
            if existing_sha != digest:
                print(f"[COLLISION] {target_pdf.name} already exists with different SHA-256; routing {src.name} to _pending_match/ to prevent overwrite.")
                if not args.dry_run:
                    pending_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, pending_dir / f"{slug}__collision__{src.name}")
                pending += 1
                continue

        if args.dry_run:
            print(f"[DRY]   {src.name} -> {target_pdf.name} ({mtype}, doi={match.get('doi')}, {v['pages']}p)")
            ingested += 1
            continue

        # 1) Copy (or move if explicitly requested outside Zotero)
        if args.move:
            shutil.move(str(src), str(target_pdf))
        else:
            shutil.copy2(src, target_pdf)

        # 2) Convert to page-anchored Markdown BEFORE checking off wanted note
        conv = convert_one(
            target_pdf,
            {
                "slug": slug,
                "title": match.get("title") or slug,
                "authors_year": match.get("authors_year") or "",
                "venue": match.get("venue") or "",
                "doi": match.get("doi") or "",
                "why_read": match.get("why_read") or "",
            },
            overwrite=False,
            engine=args.engine,
        )
        if conv.get("status") not in ("converted", "skipped"):
            print(f"[ERR]   Markdown conversion failed for {target_pdf.name}; wanted note NOT checked off.", file=sys.stderr)
            continue

        # 3) Write provenance ledger BEFORE checking off wanted note
        rec = {
            "slug": slug,
            "doi": match.get("doi") or "",
            "source_format": "pdf",
            "title": match.get("title") or "",
            "authors_year": match.get("authors_year") or "",
            "venue": match.get("venue") or "",
            "pdf_file": target_pdf.name,
            "pages": v["pages"],
            "sha256": digest,
            "bytes": target_pdf.stat().st_size,
            "source_url": f"local-ingest://{src.name}",
            "source_api": "local-ingest",
            "oa_status": "user-provided",
            "version": "user-downloaded",
            "license": "local-research-copy",
            "verification": {"status": v["status"], "doi_found": v["doi_found"], "title_coverage": v["title_coverage"]},
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "redistribution_note": "Local research copy ingested by user; do not redistribute.",
        }
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        known_hashes[digest] = slug

        # 4) Atomically check off wanted note ONLY for exact DOI match after copy + md + provenance succeeded
        checked = False
        if mtype == "exact_doi" and match.get("wanted_note"):
            checked = atomic_check_off_wanted(Path(match["wanted_note"]), slug, match.get("doi") or "")
        print(f"[INGEST] {src.name} -> {target_pdf.name} ({v['pages']}p, wanted_checked={checked})")
        ingested += 1

    print(f"\nIngest summary: ingested={ingested}, duplicates={duplicates}, pending_review={pending}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
