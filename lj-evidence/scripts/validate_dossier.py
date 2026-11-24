#!/usr/bin/env python3
"""Validate the structural contract of a preserved lj-sourcework dossier."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SECTIONS = {
    "问题契约": ("问题契约", "question contract"),
    "本地已有": ("本地已有", "local corpus", "local recall"),
    "领域地图": ("领域地图", "field map"),
    "资料宇宙": ("资料宇宙", "source universe", "source census", "source-system map"),
    "覆盖矩阵": ("覆盖矩阵", "coverage matrix"),
    "搜索日志": ("搜索日志", "search log"),
    "Source Triage": ("source triage", "来源分流", "资料分流"),
    "史料批判": ("史料批判", "source criticism"),
    "停止判断": ("停止判断", "stop decision", "closure"),
    "交付": ("交付", "handoff", "deliverables"),
}

REQUIRED = {
    "map": ("问题契约", "本地已有", "领域地图", "资料宇宙", "覆盖矩阵", "搜索日志", "Source Triage", "停止判断"),
    "build": tuple(SECTIONS),
    "audit": ("问题契约", "本地已有", "资料宇宙", "覆盖矩阵", "Source Triage", "史料批判", "停止判断", "交付"),
    "rolling": ("问题契约", "本地已有", "覆盖矩阵", "Source Triage", "停止判断", "交付"),
}


def normalized_headings(text: str) -> list[str]:
    return [m.group(1).strip().lower() for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.M)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dossier", type=Path)
    parser.add_argument("--mode", choices=tuple(REQUIRED), default="build")
    args = parser.parse_args()
    path = args.dossier.expanduser()
    if not path.is_file():
        parser.error(f"file not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"<[^>]+>|\b(?:TODO|TBD)\b", text, re.I):
        print(f"FAIL ({args.mode}): template placeholder remains")
        return 1
    headings = normalized_headings(text)
    missing = [
        label
        for label in REQUIRED[args.mode]
        if not any(any(v.lower() in heading for v in SECTIONS[label]) for heading in headings)
    ]
    warnings: list[str] = []
    lowered = text.lower()
    if "http://" not in lowered and "https://" not in lowered and "[[" not in text:
        warnings.append("no visible URL or wiki link; provenance may be missing")
    if args.mode == "build" and not any(
        term in lowered for term in ("inaccessible", "wanted", "版权", "不可访问", "获取状态")
    ):
        warnings.append("no explicit access/wanted status")
    if not any(term in lowered for term in ("reopen", "重开", "重新开启", "触发条件")):
        warnings.append("no reopen trigger")
    if not any(term in lowered for term in ("supportable claim", "可支持", "可答", "strongest claim")):
        warnings.append("no strongest supportable claim now")
    if not any(term in lowered for term in ("evidentiary ceiling", "证据上限", "不能证明", "不能支持")):
        warnings.append("no candidate evidentiary ceiling")
    if not any(term in lowered for term in ("reject", "拒绝", "不摄取")):
        warnings.append("no rejected candidate; discovery/admission boundary may be invisible")

    if missing:
        print(f"FAIL ({args.mode}): missing required sections: " + ", ".join(missing))
        for warning in warnings:
            print("WARN: " + warning)
        return 1
    print(f"PASS ({args.mode}): mechanical dossier contract OK; source quality unverified")
    for warning in warnings:
        print("WARN: " + warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
