---
name: lj-review
description: Critique scientific manuscripts (self-review or authorized peer review) or plan point-by-point reviewer responses; use lj-write for revised prose.
---

# lj-review

Choose self-review, authorized referee review, or response planning. Verify manuscript facts (titles, numbers, table denominators, figure labels, and what is actually written vs omitted) **before** raising critiques. Locate material concerns, distinguish defects from preferences, calibrate severity, and propose the smallest honest repair or claim downgrade. Read [review guidance](references/review-rubric.md) only for the active mode, venue positioning, or explicitly requested multi-reviewer simulation.

Check disputed or changed citations via `lj-evidence` and changed numbers against data, formulas, or outputs. Use `lj-write` for revised manuscript or reply prose after decisions are locked. Verify current venue rules from official sources (`lj-journal` optional).

For third-party unpublished manuscripts or figures under review, establish permission before reading or quoting (public preprint, author consent, or publisher policy permitting this tool). Unclear authorization blocks the material. Include authorization basis and AI-assistance disclosure in authorized referee reports, keeping `【致作者】` and `【致编辑（机密）】` separate. Grant-review material remains strictly out of scope: do not read, quote, search from, summarize, or retain it.

Keep critique reports separate from manuscript edits unless editing is requested. Run [validate_report.py](scripts/validate_report.py) (`--mode review` for self/referee reports, `--mode response` for response plans) on saved schema-based artifacts to verify comment-to-plan ID parity (`C1..Cn`) and source IDs.

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Explicit output paths and read-only/no-save instructions take precedence.
