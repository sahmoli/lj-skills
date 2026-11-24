#!/usr/bin/env python3
"""Mechanical validator for a saved lj-review report or response plan."""

import argparse
import pathlib
import re
import sys

REQUIRED = ["【模式】", "【稿件 / 目标刊 / 类型】", "【一句话判断】", "【review sources】", "【行动清单】", "【⚠待核】"]
RESPONSE_REQUIRED = ["【模式】", "【稿件 / 目标刊 / 类型】", "【意见分类】", "【回应计划表】", "【⚠待核】"]
COMMENT_LINE = re.compile(
    r"^(C\d+):\s*class=(editorial|scientific|statistical|policy|\[口味\]);\s*"
    r"claim=.+?;\s*stance=(agree|partial|rebut);\s*"
    r"remedy=(cut|qualify|re-scope|clarify|add-analysis);\s*"
    r"location=.+?;\s*fabrication_request=.+$"
)
PLAN_LINE = re.compile(
    r"^(C\d+)\s+意见摘要=.+?→\s*立场=(agree|partial|rebut)\s*→\s*改动=.+?→\s*位置=.+?→\s*措辞要点=.+$"
)
FINDING_LINE = re.compile(
    r"^(F\d+):\s*severity=(critical|major|minor|preference);\s*location=.+?;\s*"
    r"evidence=(S\d+|manuscript|data|calculation);\s*remedy=.+$",
    re.I,
)
LEGACY_ACTION_LINE = re.compile(
    r"(?:^|【行动清单】)\s*[🔴🟠🟡🔵].+?(?:最小修法|修法|修正|删除|限定|降\s*claim|改写).+$",
    re.M,
)
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b|^\s*—\s*$", re.I | re.M)
MANUSCRIPT_DATA_ONLY = re.compile(
    r"^\s*scope=manuscript/data-only;\s*external_sources=none\s*$", re.I | re.M
)
EXTERNAL_SOURCE_TOKEN = re.compile(r"\b(?:doi:|https?://|citation=)\S*", re.I)


def section_body(text: str, heading: str) -> str:
    match = re.search(rf"^{re.escape(heading)}\s*(.*?)(?=^【|\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def validate_review(text: str) -> list[str]:
    errors = [f"missing {token}" for token in REQUIRED if token not in text]
    mode_body = section_body(text, "【模式】")
    mode_line = next((line for line in text.splitlines() if line.startswith("【模式】")), "") + " " + mode_body
    if not re.search(r"自审|self|审稿|referee", mode_line, re.I):
        errors.append("review mode requires 【模式】 to declare self-review/自审 or referee/审稿")
    if re.search(r"审稿|referee", mode_line, re.I):
        if "【保密与授权】" not in text:
            errors.append("referee mode requires 【保密与授权】")
        else:
            gate_body = (re.search(r"【保密与授权】([^\n]*)", text).group(1) if re.search(r"【保密与授权】([^\n]*)", text) else "") + " " + section_body(text, "【保密与授权】")
            if not re.search(r"依据=\s*\S+", gate_body) or not re.search(r"期刊AI政策=\s*\S+", gate_body):
                errors.append("referee confidentiality gate requires non-empty authorization basis and publisher AI-policy status")
            if not re.search(r"披露(?:行)?=|【披露】", text):
                errors.append("referee mode requires an AI-assistance disclosure")
        if "【致作者】" not in text or "【致编辑（机密）】" not in text:
            errors.append("referee mode requires separated 【致作者】 and 【致编辑（机密）】 channels")

    source_body = section_body(text, "【review sources】")
    pending_body = section_body(text, "【⚠待核】")
    sources = re.findall(r"^(S\d+):\s*citation=(.+?);\s*status=(resolved|pending);\s*locator=(.+)$", source_body, re.M)
    declared_sids: set[str] = set()
    if not sources:
        if not MANUSCRIPT_DATA_ONLY.search(source_body):
            errors.append("review sources need S<n> records or explicit manuscript/data-only scope")
        elif EXTERNAL_SOURCE_TOKEN.search(source_body):
            errors.append("manuscript/data-only scope cannot contain external citation records")
    for sid, citation, status, locator in sources:
        if sid in declared_sids:
            errors.append(f"duplicate source ID: {sid}")
        declared_sids.add(sid)
        if status == "resolved" and not re.search(r"doi|https?://", locator, re.I):
            errors.append(f"resolved source lacks DOI/URL: {citation}")
        if status == "pending":
            if not pending_body.strip():
                errors.append(f"pending source {sid} ({citation}) requires a non-empty 【⚠待核】 section")

    findings_matched = [FINDING_LINE.match(line) for line in text.splitlines()]
    findings = [m for m in findings_matched if m is not None]
    for m in findings:
        ev = m.group(3)
        if ev.upper().startswith("S") and ev.upper() not in declared_sids:
            errors.append(f"finding {m.group(1)} references undeclared source ID {ev}")

    if (
        not findings
        and not LEGACY_ACTION_LINE.search(text)
        and "none found in checked scope" not in text
    ):
        errors.append("action list needs a located severity/evidence/remedy finding or an honest no-finding state")
    if re.search(r"成熟度[^\n]*\bC\b", text):
        errors.append("idea-stage maturity C belongs to lj-design")
    return errors


def validate_response(text: str) -> list[str]:
    errors = [f"missing {token}" for token in RESPONSE_REQUIRED if token not in text]
    mode_line = next((line for line in text.splitlines() if line.startswith("【模式】")), "") + " " + section_body(text, "【模式】")
    if not re.search(r"回应|response", mode_line, re.I):
        errors.append("response mode requires 【模式】 to declare 回应/response")

    comment_matches = [m for line in text.splitlines() if (m := COMMENT_LINE.match(line))]
    plan_matches = [m for line in text.splitlines() if (m := PLAN_LINE.match(line))]
    if not comment_matches:
        errors.append("response mode requires numbered C<n>: lines with stance and location")
    if not plan_matches:
        errors.append("response mode requires numbered plan rows with 立场 and 位置")

    if comment_matches and plan_matches:
        c_ids = [m.group(1) for m in comment_matches]
        p_ids = [m.group(1) for m in plan_matches]
        if len(c_ids) != len(set(c_ids)):
            errors.append(f"duplicate comment IDs in 【意见分类】: {c_ids}")
        if len(p_ids) != len(set(p_ids)):
            errors.append(f"duplicate plan IDs in 【回应计划表】: {p_ids}")
        if set(c_ids) != set(p_ids):
            errors.append(f"comment IDs {sorted(set(c_ids))} do not match plan IDs {sorted(set(p_ids))}")
        # Verify stance consistency per comment ID
        c_stance = {m.group(1): m.group(3) for m in comment_matches}
        p_stance = {m.group(1): m.group(2) for m in plan_matches}
        for cid in sorted(set(c_ids) & set(p_ids)):
            if c_stance[cid] != p_stance[cid]:
                errors.append(f"stance mismatch for {cid}: comment={c_stance[cid]} vs plan={p_stance[cid]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a saved lj-review report")
    parser.add_argument("report")
    parser.add_argument("--mode", choices=("review", "response"), default="review")
    args = parser.parse_args()
    text = pathlib.Path(args.report).read_text(encoding="utf-8")
    errors = validate_response(text) if args.mode == "response" else validate_review(text)
    if PLACEHOLDER.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    label = "response plan" if args.mode == "response" else "review report"
    print(f"PASS: {label} satisfies the mechanical contract (review quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
