#!/usr/bin/env python3
"""Validate the inspectable, report-only contract of a saved lj-weave report."""

import pathlib
import re
import sys


REQUIRED = ["【语料】", "【实际节点数】", "【锚定】", "【节点表】", "【边】", "【写入状态】report-only"]
NODE_FIELDS = [
    "basic_assumption_ceiling", "root_rank_floor", "relation_shape",
    "coordinate_system", "generator", "source",
]
EDGE_RE = re.compile(
    r"^E\d+:\s*type=([^;]+);\s*level=(same-level|cross-level);\s*"
    r"nodes=([^;]+);\s*mechanism=([^;]+);\s*"
    r"evidence=(grounded|inferred|pending);\s*source=(.+)$"
)
PLACEHOLDER_RE = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b|^\s*—\s*$", re.I | re.M)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_weave.py REPORT.md", file=sys.stderr)
        return 2
    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    errors = [f"missing {token}" for token in REQUIRED if token not in text]
    errors.extend(f"node table missing field: {field}" for field in NODE_FIELDS if field not in text)
    count_match = re.search(r"【实际节点数】\s*(\d+)", text)
    if not count_match or int(count_match.group(1)) < 2:
        errors.append("actual node count must be an integer >= 2")
    edge_lines = [line.strip() for line in text.splitlines() if re.match(r"^\s*E\d+:", line)]
    if not edge_lines:
        errors.append("no E<n> edge records")
    for line in edge_lines:
        match = EDGE_RE.fullmatch(line)
        if not match:
            errors.append(f"malformed edge record: {line[:120]}")
            continue
        edge_type, level, nodes, mechanism, evidence, source = match.groups()
        if edge_type not in {"同源", "同构迁移", "派生·尺度", "嵌套", "张力·矛盾"}:
            errors.append(f"unknown edge type: {edge_type}")
        if len([node for node in nodes.split(",") if node.strip()]) != 2:
            errors.append(f"edge must name exactly two nodes: {line[:100]}")
        if len(mechanism.strip()) < 8:
            errors.append(f"mechanism is too thin: {line[:100]}")
        if evidence == "grounded" and re.search(r"unresolved|待核|unknown", source, re.I):
            errors.append(f"grounded edge lacks a readable source: {line[:100]}")
        if level == "cross-level" and not re.search(r"ceiling|root|floor|coordinate|relation", mechanism, re.I):
            errors.append(f"cross-level edge does not name connected levels: {line[:100]}")
    if PLACEHOLDER_RE.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: {len(edge_lines)} edge records satisfy the mechanical report contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
