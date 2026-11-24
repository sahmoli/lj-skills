#!/usr/bin/env python3
"""Validate the branching mechanical contract of an lj-question Explain report.

Supports both compact Explain reports (without rigid L0..L3 rituals) and legacy `lj-dig` fixtures.
"""
import pathlib
import re
import sys

LEGACY_COMMON = ["【目标】", "【L0 alternatives】", "【L1 level】"]
LEGACY_FULL = ["【L2 mechanism】", "【L3 contingency stop】", "【命门】", "【可及性】", "【一针见血】", "【种子】"]
LEGACY_HALT = ["【HALTED at L2】", "【下一证据】"]
PLACEHOLDER = re.compile(r"<[^>]+>|\b(?:TODO|TBD)\b|^\s*—\s*$", re.I | re.M)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_dig.py REPORT.md", file=sys.stderr)
        return 2
    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    errors: list[str] = []

    is_legacy = "【L0 alternatives】" in text or "【HALTED at L2】" in text or "【L1 level】" in text
    if is_legacy:
        errors.extend(f"missing {token}" for token in LEGACY_COMMON if token not in text)
        halted = "【HALTED at L2】" in text
        required = LEGACY_HALT if halted else LEGACY_FULL
        forbidden = LEGACY_FULL if halted else LEGACY_HALT
        errors.extend(f"missing {token}" for token in required if token not in text)
        errors.extend(f"incompatible branch token: {token}" for token in forbidden if token in text)
        if not halted:
            for token in ("falsifier", "alternative", "opposite prediction", "literature status"):
                if token not in text:
                    errors.append(f"full report missing {token}")
            if not re.search(r"accessible now|accessible with named dependency|not yet accessible", text):
                errors.append("full report lacks accessibility classification")
    else:
        halted = bool(re.search(r"【HALTED】|\bstatus:\s*halted\b", text, re.I))
        if not re.search(r"【目标】|##\s*(?:Target|Pattern|现象与问题)", text, re.I):
            errors.append("missing target pattern section")
        if not re.search(r"alternative|竞争解释|替代机制", text, re.I):
            errors.append("missing competing explanation / alternative process")
        if halted:
            if not re.search(r"【下一证据】|missing evidence|所需证据", text, re.I):
                errors.append("halted report must name the missing evidence required to proceed")
        else:
            if not re.search(r"falsifier|diverg|opposite prediction|判别预测|证伪", text, re.I):
                errors.append("full report missing discriminating prediction / falsifier")
            if not re.search(r"accessible now|accessible with named dependency|not yet accessible", text, re.I):
                errors.append("full report lacks accessibility classification")

    if PLACEHOLDER.search(text):
        errors.append("template placeholder remains")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    branch = "halted" if halted else "full"
    print(f"PASS: {branch} explain report satisfies the mechanical contract (causal quality unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
