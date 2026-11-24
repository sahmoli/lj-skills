#!/usr/bin/env python3
"""Static, mode-aware validation for an lj-talk outline."""

from __future__ import annotations

import pathlib
import re
import sys


MODE_ALIASES = {
    "conference": "conference", "会议报告": "conference",
    "lecture": "lecture", "教学讲课": "lecture",
    "defense": "defense", "答辩": "defense",
}
ALLOWED_TYPES = {"data", "concept", "transition", "backup", "title", "acknowledgement",
                 "references", "conclusion"}
TOPIC_TITLE = re.compile(r"^(?:methods?|results?|introduction|background|discussion|方法|结果|背景|讨论)\b", re.I)
REQUIRED = ["【模式】", "【受众状态】", "【核心论弧】", "【Ghost Deck】", "【逐页大纲】",
            "【QA报告】"]
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b", re.I)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_outline.py OUTLINE.md", file=sys.stderr)
        return 2
    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    errors = [f"missing {token}" for token in REQUIRED if token not in text]
    if "【渲染状态】" not in text and "【不替你渲染】" not in text:
        errors.append("missing an honest rendering-status declaration")
    mode_match = re.search(r"【模式】\s*([^\s|]+)", text)
    mode = MODE_ALIASES.get(mode_match.group(1)) if mode_match else None
    if not mode:
        errors.append("mode must be conference, lecture, or defense")

    slides = list(re.finditer(
        r"(?m)^\s*\[(\d+)\]\s*【标题】(.+?)\s*\[type:\s*([a-z]+)(?:,\s*([^\]]+))?\]\s*$", text
    ))
    if not slides:
        errors.append("expected at least one slide record")
    records = []
    for index, match in enumerate(slides):
        start = match.start()
        end = slides[index + 1].start() if index + 1 < len(slides) else len(text)
        block = text[start:end]
        number, title, slide_type, qualifiers = match.group(1), match.group(2).strip(), match.group(3), match.group(4) or ""
        if slide_type not in ALLOWED_TYPES:
            errors.append(f"slide {number} has invalid type: {slide_type}")
        if slide_type not in {"title", "acknowledgement", "references", "concept"} and TOPIC_TITLE.search(title):
            errors.append(f"slide {number} uses topic-label title: {title}")
        body_match = re.search(r"(?m)^正文要点:\s*(.+)$", block)
        if not body_match:
            errors.append(f"slide {number} missing body")
            body = ""
        else:
            body = body_match.group(1).strip()
        source = re.search(r"(?m)^数值来源:\s*(.+)$", block)
        if re.search(r"\d", title + " " + body) and not source:
            errors.append(f"slide {number} contains a numeric claim without a source")
        elif source and re.search(r"\d", title + " " + body) and source.group(1).strip().lower() in {"n/a", "none", "无"}:
            errors.append(f"slide {number} contains a numeric claim without a source")
        records.append((number, slide_type))

    if PLACEHOLDER.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: mechanical talk contract OK for {mode} ({len(slides)} slides; rendered QA pending)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
