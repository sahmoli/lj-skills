---
name: lj-write
description: Draft or edit scientific manuscript prose, figure captions, and reviewer-response letters faithfully from locked evidence (not scientific critique).
---

# lj-write

Render the supplied science faithfully. A local edit needs only the target passage and its constraints; read [prose guidance](references/prose-engine.md) for substantial drafting, restructuring, or sample-based voice calibration.

Preserve numbers, signs, intervals, units, sample sizes/denominators, statistical meaning, causal strength, citation attachment, limitations, terminology, and author decisions unless scientific revision is explicitly authorized. Captions follow the figure's verified evidence and manifest. Do not fill gaps with unrequested analyses, mechanisms, citations, novelty claims, or boilerplate future-work padding.

Mark any unsupported passage as an explicit content gap (`⚠待核`) and complete supported sections. After revising quantitative or cited passages, run [check_drift.py](scripts/check_drift.py) (`--before <orig> --after <rev>`) to verify zero unintended token-level drift in numbers, units, figure/table locators, or citations (and visually confirm group-to-value mapping).

Use `lj-review` when scientific critique or response planning is needed, `lj-evidence` for citation verification, and `lj-viz` for publication figures.

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Explicit output paths and read-only/no-save instructions take precedence.
