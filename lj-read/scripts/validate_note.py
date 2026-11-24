#!/usr/bin/env python3
"""Validate the deterministic parts of an lj-read book companion and coverage map.

Supports both the portable v2 schema (`genre: book`, `# 读者增量 / Reader Delta`)
and legacy `lj-book` companions (`genre: 拆书 (lj-book)`, `# Juan 的 delta：`).
"""
import argparse
import pathlib
import re

CORE_SECTIONS = ["# x：", "# f：", "# f(x)：", "# 迁移与边界", "# 资料校准"]
DELTA_RE = re.compile(r"(?m)^#\s*(?:读者增量|Reader\s+Delta|Juan\s*的\s*delta)\s*[：:]?")
ZONES = ["Introduction/front matter", "Early setup", "Middle mechanism", "Late findings", "Ending/boundaries"]
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b", re.I)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("note")
    parser.add_argument("--coverage", required=True)
    args = parser.parse_args()
    note = pathlib.Path(args.note).read_text(encoding="utf-8")
    coverage = pathlib.Path(args.coverage).read_text(encoding="utf-8")
    errors = []

    if "type: reading-companion" not in note:
        errors.append("missing frontmatter token: type: reading-companion")
    if not re.search(r"(?m)^genre:\s*(?:book|拆书\s*\(lj-read\)|拆书\s*\(lj-book\))\s*$", note):
        errors.append("missing frontmatter token: genre (expected book / 拆书 (lj-read))")
    for field in ("book:", "author:", "source:", "created:"):
        if field not in note:
            errors.append(f"missing frontmatter token: {field}")

    for label in ("- **x**：", "- **f**：", "- **f(x)**："):
        if len(re.findall(re.escape(label), note)) != 1:
            errors.append(f"expected exactly one {label}")
    for section in CORE_SECTIONS:
        if section not in note:
            errors.append(f"missing section: {section}")
    if not DELTA_RE.search(note):
        errors.append("missing delta section (# 读者增量： / # Reader Delta:)")

    for zone in ZONES:
        if zone not in coverage:
            errors.append(f"coverage missing zone: {zone}")
    components = len(re.findall(r"(?m)^\| C\d+ \|", coverage))
    if components < 1:
        errors.append("coverage needs at least one candidate component")
    status = re.search(r"(?m)^status:\s*(complete|partial|hypothesis)\s*$", note)
    if not status:
        errors.append("note status must be complete, partial, or hypothesis")
    material = re.search(r"(?mi)^- Material status:\s*(full text|substantial excerpts|thin/partial)\s*$", coverage)
    if not material:
        errors.append("coverage verdict lacks a valid Material status")
    if "## Coverage verdict" not in coverage:
        errors.append("coverage missing ## Coverage verdict")
    if status and status.group(1) == "complete" and (not material or material.group(1).lower() != "full text"):
        errors.append("status complete requires coverage Material status: full text")
    for source_name, text in (("note", note), ("coverage", coverage)):
        if PLACEHOLDER.search(text) or "| | |" in text:
            errors.append(f"{source_name} contains template placeholders")
    for line_no, line in enumerate(note.splitlines(), 1):
        if len(line) > 100 and re.match(r"^[ |+\-<>v^]+$", line):
            errors.append(f"ASCII line {line_no} exceeds 100 characters")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print("PASS: mechanical book contract OK (reading quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
