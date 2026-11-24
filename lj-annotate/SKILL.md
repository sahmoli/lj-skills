---
name: lj-annotate
description: Build or audit an offline, single-record HTML workbench for assisted or blind human annotation.
---

# lj-annotate

Build or audit a local, one-record-at-a-time HTML annotation workbench for assisted review or blind human coding (never a public web portal or generic dashboard).

- **Measurement integrity:** keep AI drafts, human decisions, and blind conditions strictly separated. An untouched answer is not a negative answer. A changed input packet must not silently inherit prior confirmations.
- **Offline & fail-closed:** zero external network dependencies, no unsafe HTML injection, and no leakage of strata, hidden AI notes, or prior answers in blind mode. Full export unlocks only when all required records have human confirmation; partial export preserves blanks and flags AI-only items.
- **Deterministic build & browser QA:** read [interface contract](references/interface-contract.md) and run [build_annotation_html.py](scripts/build_annotation_html.py), [validate_annotation_html.py](scripts/validate_annotation_html.py), [selftest.py](scripts/selftest.py), Playwright geometry/interaction/export checks ([browser_qa.sh](scripts/browser_qa.sh)), and [finalize_receipt.py](scripts/finalize_receipt.py) before claiming visual or interactive pass. Never reduce human confirmation to save clicks.

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Explicit output paths and read-only/no-save instructions take precedence.
