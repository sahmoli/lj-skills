#!/usr/bin/env python3
"""Validate the mode-specific mechanical contract of an lj-read paper companion.

Supports both the portable v2 schema (`genre: paper`, optional `lane`) and legacy
`lj-paper` companions (`genre: 精读 (lj-paper)`, `lane: raw/reading`).
"""
from __future__ import annotations

import pathlib
import re
import sys

REQUIRED_FIELDS = ("paper", "authors", "venue", "source", "created")
LEGACY_MODE_TOKENS = {
    "complete": ["【证据链】", "【解释模型】", "【批判性评估】", "confirmed", "inferred", "falsifier"],
    "parked": ["【PARKED】"],
    "halted": ["【HALTED】", "【概念缺口】"],
}
PORTABLE_MODE_PATTERNS = {
    "complete": [
        r"【证据链】|##\s*(?:Evidence|证据链)",
        r"【解释模型】|##\s*(?:Model|Mechanism|解释模型|核心论断)",
        r"【批判性评估】|##\s*(?:Appraisal|Critique|批判性评估|边界与局限)",
        r"falsifier|weakening observation|证伪|削弱条件",
    ],
    "parked": [r"【PARKED】|\bPARKED\b"],
    "halted": [r"【HALTED】|\bHALTED\b", r"【概念缺口】|missing|缺口"],
}
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b", re.I)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_companion.py COMPANION.md", file=sys.stderr)
        return 2
    path = pathlib.Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    if "type: reading-companion" not in text:
        errors.append("missing token: type: reading-companion")
    if not re.search(r"(?m)^genre:\s*(?:paper|精读\s*\(lj-read\)|精读\s*\(lj-paper\))\s*$", text):
        errors.append("missing or invalid genre (expected `genre: paper` or `genre: 精读 (lj-read)`)")

    is_legacy = "genre: 精读 (lj-paper)" in text
    if is_legacy:
        for tok in ("lane: raw/reading", "status: read-only-input", "【速读卡】", "【→ 下游】"):
            if tok not in text:
                errors.append(f"missing token: {tok}")

    mode_match = re.search(r"(?m)^reading_status:\s*(complete|parked|halted)\s*$", text)
    if not mode_match:
        errors.append("reading_status must be complete, parked, or halted")
        mode = None
    else:
        mode = mode_match.group(1)
        if is_legacy:
            errors.extend(f"missing {mode} token: {tok}" for tok in LEGACY_MODE_TOKENS[mode] if tok not in text)
        else:
            for pat in PORTABLE_MODE_PATTERNS[mode]:
                if not re.search(pat, text, re.I):
                    errors.append(f"missing {mode} pattern: {pat}")

    for field in REQUIRED_FIELDS:
        if not re.search(rf"(?m)^{field}:\s*\S.+$", text):
            errors.append(f"frontmatter field is empty: {field}")

    if mode == "complete" and not any(tok in text for tok in ("grounded", "speculative", "confirmed", "⚠待核")):
        errors.append("complete companion lacks evidence-status language")
    if PLACEHOLDER.search(text):
        errors.append("template placeholder remains")
    if "wiki/sources/" in str(path) or "20_wiki/notes/" in str(path).replace("\\", "/"):
        errors.append("reading companion must not be written directly into durable Wiki notes")

    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: mechanical paper contract OK for reading_status={mode} (reading quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
