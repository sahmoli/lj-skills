#!/usr/bin/env python3
"""Query and validate Juan's auditable figure-reference corpus."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from validate_manifest import load_manifest, manifest_project_root, missing, resolve_path

DEFAULT_DATASET = (
    Path.home() / "wiki-knowledge/raw/datasets/2026-nature-science-ecology-figure-audit"
)
TABLES = ("deep_visual_coding.tsv", "craft_visual_coding.tsv", "figure_inventory.tsv")


def rows(dataset: Path) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for name in TABLES:
        path = dataset / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                item = {key: str(value or "") for key, value in row.items()}
                item["_table"] = name
                item["source_id"] = item.get("source_id") or item.get("paper_id", "")
                result.append(item)
    return result


def normal_figure(value: str) -> str:
    raw = value.strip().lower().replace("figure", "fig").replace(" ", "")
    if raw.startswith("fig") and not raw.startswith("fig-"):
        raw = "fig-" + raw[3:].lstrip(".-")
    return raw


def searchable(row: dict[str, str]) -> str:
    keys = (
        "source_id", "paper_id", "figure_id", "dominant_architecture_paper_heuristic",
        "panel_evidence_roles", "reading_path", "visual_direction", "strongest_craft_move",
        "chart_types_caption_heuristic", "caption",
    )
    return " ".join(row.get(key, "") for key in keys).casefold()


def _valid_positive_page(val: object) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val >= 1


def _inspect_pdf_page_bound(pdf_path: Path, page_no: int) -> str | None:
    """Validate PDF extension, header/trailer structure, and upper page bound when readable."""
    if pdf_path.suffix.lower() != ".pdf":
        return f"not a .pdf file ({pdf_path.name})"
    try:
        data = pdf_path.read_bytes()
    except OSError as exc:
        return f"unreadable PDF ({exc})"
    if len(data) < 32 or b"%PDF-" not in data[:1024] or b"%%EOF" not in data[-4096:]:
        return f"malformed or truncated PDF ({pdf_path.name})"
    if b"xref" not in data and b"/XRef" not in data:
        return f"PDF missing xref table/stream ({pdf_path.name})"
    counts: list[int] = []
    for chunk in data.split(b">>"):
        if b"<<" in chunk and b"/Pages" in chunk and b"/Count" in chunk:
            d = chunk.rpartition(b"<<")[2]
            if re.search(rb"/Type\s*/Pages\b", d):
                m = re.search(rb"/Count\s+(\d+)", d)
                if m:
                    counts.append(int(m.group(1)))
    if counts:
        total_pages = max(counts)
        if total_pages < 1 or page_no > total_pages:
            return f"pdf_page {page_no} out of range (1..{total_pages}) for {pdf_path.name}"
    return None


def check_manifest(manifest_path: Path, dataset: Path) -> tuple[list[str], list[str]]:
    data = load_manifest(manifest_path)
    proj_root = manifest_project_root(manifest_path, data)
    refs = data.get("reference_board")
    if not isinstance(refs, list) or len(refs) == 0:
        return ["reference_board must be a non-empty list"], []

    needs_corpus = any(
        isinstance(r, dict) and str(r.get("source_kind", "corpus")) == "corpus"
        for r in refs
    )
    keys: set[tuple[str, str]] = set()
    errors: list[str] = []
    facts: list[str] = []

    if needs_corpus:
        if not dataset.is_dir():
            errors.append(f"corpus dataset directory does not exist for corpus reference: {dataset}")
        else:
            inventory = rows(dataset)
            keys = {
                (row.get("source_id", "").casefold(), normal_figure(row.get("figure_id", "")))
                for row in inventory
                if row.get("source_id") and row.get("figure_id")
            }

    for index, reference in enumerate(refs, start=1):
        if not isinstance(reference, dict):
            errors.append(f"reference_board[{index}] is not a mapping")
            continue
        kind = str(reference.get("source_kind", "corpus"))
        source = str(reference.get("source_id", "")).strip()
        figure = str(reference.get("figure_id", "")).strip()
        if kind == "corpus":
            if not source or not figure:
                errors.append(f"reference_board[{index}] corpus requires non-empty source_id and figure_id")
            elif dataset.is_dir():
                if (source.casefold(), normal_figure(figure)) not in keys:
                    errors.append(f"reference_board[{index}] not found in corpus: {source} {figure}")
                else:
                    facts.append(f"reference_board[{index}] corpus hit: {source} {figure}")
        elif kind == "local-pdf":
            raw_ep = reference.get("evidence_path")
            page_no = reference.get("pdf_page")
            resolved = resolve_path(raw_ep, proj_root) if not missing(raw_ep) else None
            if resolved is None or not resolved.is_file() or not _valid_positive_page(page_no):
                errors.append(
                    f"reference_board[{index}] local-pdf requires an existing .pdf file evidence_path and integer pdf_page >= 1"
                )
            else:
                pdf_err = _inspect_pdf_page_bound(resolved, int(page_no))
                if pdf_err:
                    errors.append(f"reference_board[{index}] invalid local-pdf: {pdf_err}")
                else:
                    facts.append(f"reference_board[{index}] local PDF: {resolved} page {page_no}")
        elif kind == "baseline":
            raw_ep = reference.get("evidence_path")
            resolved = resolve_path(raw_ep, proj_root) if not missing(raw_ep) else None
            if resolved is None or not resolved.is_file():
                errors.append(f"reference_board[{index}] baseline requires an existing file evidence_path")
            else:
                facts.append(f"reference_board[{index}] baseline: {resolved}")
        else:
            errors.append(f"reference_board[{index}].source_kind must be corpus, local-pdf, or baseline")
    return errors, facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--query", default="", help="free text across architecture, role, caption and craft fields")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--check-manifest", type=Path)
    args = parser.parse_args()

    if args.check_manifest:
        if not args.check_manifest.is_file():
            print(f"FAIL: manifest file does not exist: {args.check_manifest}")
            return 2
        errors, facts = check_manifest(args.check_manifest, args.dataset)
        for fact in facts:
            print(f"FACT: {fact}")
        for error in errors:
            print(f"FAIL: {error}")
        print(f"RESULT: {'FAIL' if errors else 'PASS'} ({len(errors)} errors)")
        return 1 if errors else 0

    if not args.dataset.is_dir():
        exemplars = Path(__file__).resolve().parent.parent / "references" / "exemplars.md"
        print(
            f"WARN: optional corpus directory not present on this machine ({args.dataset}); "
            f"fall back to bundled exemplars: {exemplars}"
        )
        return 0

    terms = [term.casefold() for term in args.query.split() if term]
    matches = [row for row in rows(args.dataset) if all(term in searchable(row) for term in terms)]
    seen: set[tuple[str, str, str]] = set()
    emitted = 0
    print("source_id\tfigure_id\tpdf_page\ttable\tarchitecture_or_direction\treading_or_craft")
    for row in matches:
        key = (row.get("source_id", ""), row.get("figure_id", ""), row.get("_table", ""))
        if key in seen:
            continue
        seen.add(key)
        descriptor = row.get("dominant_architecture_paper_heuristic") or row.get("visual_direction", "")
        reading = row.get("reading_path") or row.get("strongest_craft_move", "")
        print("\t".join((key[0], key[1], row.get("pdf_page", ""), key[2], descriptor, reading)))
        emitted += 1
        if emitted >= max(1, args.limit):
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
