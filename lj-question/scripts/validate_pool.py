#!/usr/bin/env python3
"""Validate inspectable honesty fields in an unranked lj-question Explore pool.

Supports both compact modern Explore records and legacy `lj-roam` records.
"""
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_pool.py POOL.md", file=sys.stderr)
        return 2
    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    errors = []
    if not re.search(r"【候选种子池】|##\s*(?:Candidate\s+Pool|候选问题池|候选种子池)", text, re.I):
        errors.append("missing pool heading (【候选种子池】 or ## Candidate Pool)")
    records = re.split(r"(?m)(?=^[ONC]\d+\.)", text)[1:]
    if not records:
        errors.append("pool needs at least one numbered candidate (e.g. C1. / O1. / N1.)")

    seen_ids: set[str] = set()
    for record in records:
        rid_m = re.match(r"^([ONC]\d+)\.", record)
        if rid_m:
            rid = rid_m.group(1)
            if rid in seen_ids:
                errors.append(f"duplicate candidate ID: {rid}")
            seen_ids.add(rid)
        has_legacy = all(tok in record for tok in ("Move:", "来源:", "共享结构:", "接地状态:", "新颖性: ⚠待核"))
        has_modern = (
            re.search(r"来源:|Source:", record, re.I)
            and re.search(r"共享结构:|Structure:|Relation:", record, re.I)
            and re.search(r"接地状态:|Grounding:", record, re.I)
            and re.search(r"⚠待核|unverified|provisional", record, re.I)
        )
        if not (has_legacy or has_modern):
            errors.append(f"candidate record missing source/structure/grounding/unverified-novelty markers: {record[:45].strip()}")

    if re.search(r"<[^>]+>|\b(?:TODO|TBD)\b", text, re.I):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print("PASS: pool has the required unranked honesty fields (idea quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
