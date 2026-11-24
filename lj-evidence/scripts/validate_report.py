#!/usr/bin/env python3
"""Structural validator for lj-citecheck reports; does not perform factual verification."""

import argparse
import pathlib
import re


PLACEHOLDER_RE = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b|^\s*—\s*$", re.I | re.M)


def validate_citation(text: str) -> list[str]:
    errors = []
    for token in ("【模式】", "【核了", "【汇总】", "【最危险先修】", "【⚠待核】", "【不替你改稿】"):
        if token not in text:
            errors.append(f"missing {token}")
    cards = re.findall(r"^C\d+:\s*claim=(.+?);\s*cited_as=(.+)$", text, re.M)
    if not cards:
        errors.append("no C<n> citation cards")
    blocks = re.split(r"(?=^C\d+:)", text, flags=re.M)[1:]
    for block in blocks:
        for token in ("存在性:", "元数据:", "支撑性:", "依据:", "修法:"):
            match = re.search(rf"^\s*·\s*{re.escape(token)}\s*(.+)$", block, re.M)
            if not match or not match.group(1).strip():
                errors.append(f"citation card missing non-empty {token}")
        support = re.search(r"支撑性:\s*(.+)", block)
        evidence = re.search(r"依据:\s*(.+)", block)
        if support and "supports" in support.group(1) and evidence:
            if not re.search(r"locator|p\.?\s*\d+|page|section|figure|table|段|页|图|表", evidence.group(1), re.I):
                errors.append("supports verdict lacks a locating detail")
    return errors


def validate_precedent(text: str) -> list[str]:
    errors = []
    for token in ("【模式】precedent", "【新颖性主张】", "【拆解】", "【检索范围】", "【判定】", "【handoff → lj-ask】", "【不背书】"):
        if token not in text:
            errors.append(f"missing {token}")
    verdict = re.search(r"【判定】\s*(FOUND|NOT-FOUND|⚠待核)(.*)", text)
    if not verdict:
        errors.append("missing valid precedent verdict")
    elif verdict.group(1) == "NOT-FOUND":
        scope = re.search(r"【检索范围】(.+)", text)
        if not scope or "未搜:" not in scope.group(1) or "provisional" not in verdict.group(2):
            errors.append("NOT-FOUND must be provisional and state what was not searched")
    elif verdict.group(1) == "FOUND":
        if not re.search(r"exact|near|partial", verdict.group(2)) or not re.search(r"doi|https?://", verdict.group(2), re.I):
            errors.append("FOUND must state closeness and a work locator")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--mode", choices=("citation", "precedent"), required=True)
    args = parser.parse_args()
    text = pathlib.Path(args.report).read_text(encoding="utf-8")
    errors = validate_citation(text) if args.mode == "citation" else validate_precedent(text)
    if args.mode == "citation" and re.search(r"疑编造\s*[1-9]|存在性:.*疑编造", text):
        if not re.search(r"ledger", text, re.I):
            errors.append("suspected-fabrication verdict requires a ledger evidence field")
    if PLACEHOLDER_RE.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: {args.mode} report satisfies the mechanical contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
