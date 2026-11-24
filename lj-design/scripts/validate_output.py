#!/usr/bin/env python3
"""Mechanical validator for a saved lj-design card."""

import pathlib
import re
import sys


REQUIRED = ["【假设】", "【判别预测", "【证伪条件】", "【设计骨架】", "【混杂因子", "【单位对齐】",
            "【可行性】", "【分析 SPEC", "【SPEC冻结】", "【自我批判", "【最小充分性】", "【先读 / 下一步】"]
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b|^\s*—\s*$", re.I | re.M)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_output.py DESIGN.md", file=sys.stderr)
        return 2
    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    errors = [f"missing {token}" for token in REQUIRED if token not in text]
    for token in ("H_alt", "observation", "mechanism", "spatial", "decision", "strongest objection",
                  "honesty scan", "severity", "pass"):
        if token not in text:
            errors.append(f"missing inspectable field: {token}")
    if "⚠待核" not in text and not re.search(r"verified|confirmed", text, re.I):
        errors.append("feasibility has neither verification nor an explicit unknown")
    if PLACEHOLDER.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print("PASS: design card satisfies the mechanical contract (scientific quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
