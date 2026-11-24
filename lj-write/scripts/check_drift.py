#!/usr/bin/env python3
"""Deterministic semantic-drift preflight for lj-write edits (stdlib only).

Compares a source text (`--before`) and a revised text (`--after`) to surface:
  - Missing or added numbers, percentages, p-values, sample sizes (`n=...`), and signs
  - Changed units, figure/table references (`Fig. 1`, `Table S2`), or equation labels
  - Added or dropped in-text / Pandoc / LaTeX citations (`(Smith et al., 2024)`, `[@key]`, `\\cite{...}`)

Exits 0 when no drift is detected (or `--advisory` is set); exits 1 when unapproved
numeric, locator, or citation drift is found so the author/agent inspects every change.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_])([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?|[+-]?\.\d+%?)(?![A-Za-z0-9_])"
)
UNIT_PAIR_RE = re.compile(r"(?<![A-Za-z0-9_])([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(%|km2|km²|km|ha|m2|m²|mm|cm|m|°C|K|kg|g|mg|yr|years?|days?|h|min|s)\b")
FIG_TAB_RE = re.compile(r"\b(?:Fig(?:ure)?s?|Tables?|Appendix|Eq(?:uation)?s?)\.?\s*S?\d+[A-Za-z]?\b", re.I)
CITE_KEY_RE = re.compile(r"@[A-Za-z0-9_.:-]+|\\cite[a-zA-Z]*\{([^}]+)\}")
AUTHOR_YEAR_RE = re.compile(r"\b([A-Z][A-Za-z'-]+(?:\s+et\s+al\.)?,?\s*(?:19|20)\d{2}[a-z]?)\b")


def extract_signals(text: str) -> dict[str, Counter]:
    nums = Counter(m.group(1).replace(",", "") for m in NUMBER_RE.finditer(text))
    locs = Counter(re.sub(r"\s+", " ", m.group(0)).strip() for m in FIG_TAB_RE.finditer(text))
    cites: Counter = Counter()
    for m in CITE_KEY_RE.finditer(text):
        if m.group(1):
            for k in m.group(1).split(","):
                cites[k.strip()] += 1
        else:
            cites[m.group(0)] += 1
    for m in AUTHOR_YEAR_RE.finditer(text):
        cites[re.sub(r"\s+", " ", m.group(1)).strip()] += 1
    units = Counter(f"{m.group(1).replace(',', '')} {m.group(2)}" for m in UNIT_PAIR_RE.finditer(text))
    return {"numbers": nums, "units": units, "locators": locs, "citations": cites}


def diff_counters(before: Counter, after: Counter) -> dict[str, list[str]]:
    dropped = []
    added = []
    for k, cnt in sorted((before - after).items()):
        dropped.append(f"{k} (x{cnt})" if cnt > 1 else k)
    for k, cnt in sorted((after - before).items()):
        added.append(f"{k} (x{cnt})" if cnt > 1 else k)
    return {"dropped": dropped, "added": added}


def compare_texts(before_text: str, after_text: str) -> dict:
    b = extract_signals(before_text)
    a = extract_signals(after_text)
    report = {
        "numbers": diff_counters(b["numbers"], a["numbers"]),
        "units": diff_counters(b["units"], a["units"]),
        "locators": diff_counters(b["locators"], a["locators"]),
        "citations": diff_counters(b["citations"], a["citations"]),
    }
    has_drift = any(v["dropped"] or v["added"] for v in report.values())
    report["ok"] = not has_drift
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Check numeric, locator, and citation drift between before/after prose.")
    ap.add_argument("--before", required=True, type=Path, help="Original source Markdown/text file")
    ap.add_argument("--after", required=True, type=Path, help="Revised Markdown/text file")
    ap.add_argument("--json", action="store_true", help="Output JSON report")
    ap.add_argument("--advisory", action="store_true", help="Always exit 0 even when drift is reported")
    args = ap.parse_args()

    res = compare_texts(
        args.before.read_text(encoding="utf-8", errors="replace"),
        args.after.read_text(encoding="utf-8", errors="replace"),
    )
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if res["ok"]:
            print("PASS: zero numeric, figure/table locator, or citation drift detected.")
        else:
            print("DRIFT DETECTED — verify every item below was intentionally authorized:")
            for cat in ("numbers", "units", "locators", "citations"):
                d = res[cat]
                if d["dropped"] or d["added"]:
                    print(f"  [{cat}] dropped={d['dropped']} | added={d['added']}")
    return 0 if (res["ok"] or args.advisory) else 1


if __name__ == "__main__":
    raise SystemExit(main())
