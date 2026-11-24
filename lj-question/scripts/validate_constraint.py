#!/usr/bin/env python3
"""Validate the mechanical contract of an lj-constraint report."""

import pathlib
import re
import sys


REQUIRED = ["【完整题面】", "【约束表】", "【解空间】", "【行为回验】", "【假墙候选】",
            "【未知与实时核验】", "【下一步】"]
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b", re.I)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_output.py REPORT.md", file=sys.stderr)
        return 2
    path = pathlib.Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    errors = [f"missing {item}" for item in REQUIRED if item not in text]
    entries = re.findall(r"(?m)^\s*C\d+\..+$", text)
    if not entries:
        errors.append("constraint table has no C<n> record")
    for entry in entries:
        if not re.search(r"\b(?:hard|soft|self-imposed|unknown)\b", entry):
            errors.append(f"constraint lacks hardness value: {entry[:80]}")
    if "若拿掉会改变:" not in text or "反验:" not in text:
        errors.append("constraint record lacks solution-space delta or falsification test")
    if "最强替代预测:" not in text or "待核观察/结果:" not in text:
        errors.append("behavior check lacks competing prediction or not-yet-checked observation")
    if PLACEHOLDER.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print("PASS: mechanical constraint contract OK (classification quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
