#!/usr/bin/env python3
"""Validate the compact daily blind-spot section."""

import argparse
import pathlib
import re
import sys


FIELDS = ["窗口", "判断", "证据", "被遮住的东西", "反方解释", "今日反制动作"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--mode", choices=("daily", "weekly"), default="daily")
    args = parser.parse_args()
    text = args.report.read_text(encoding="utf-8")
    heading = "今日盲区镜" if args.mode == "daily" else "本周盲区镜"
    match = re.search(rf"(?ms)^## {heading}\s*$\n(.*?)(?=^## |\Z)", text)
    if not match:
        print(f"FAIL: missing ## {heading}")
        return 1
    block = match.group(1)
    errors = [f"missing field: {field}" for field in FIELDS if f"**{field}**" not in block]
    judgments = len(re.findall(r"(?m)^- \*\*判断\*\*", block))
    if judgments != 1:
        errors.append(f"expected exactly one judgment field; found {judgments}")
    if re.search(r"<[^>]+>|\b(?:TODO|TBD)\b", block, re.I):
        errors.append("template placeholder remains")
    evidence = re.search(r"(?m)^- \*\*证据\*\*：(.+)$", block)
    if not evidence or not evidence.group(1).strip():
        errors.append("evidence field is empty")
    action = re.search(r"(?m)^- \*\*今日反制动作\*\*：(.+)$", block)
    if not action or not action.group(1).strip():
        errors.append("counter-move field is empty")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print("PASS: mechanical blind-spot contract OK (diagnosis quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
