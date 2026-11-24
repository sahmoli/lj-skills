# Workflow 02 · Draft or Referee Comments → Defensible Manuscript

> **Purpose:** Turn an internal draft or peer-review round into a rigorously verified, proportionate revision — verifying manuscript facts first, separating true defects from reviewer taste, and preventing numeric or citation drift.
> **Skills composed:** `lj-review` → `lj-evidence` → `lj-viz` (if needed) → `lj-write`.

---

## Stage 1 · Fact-First Audit & Triage (`lj-review`)
- **Input:** Manuscript draft, figures/tables, and (if applicable) editor/referee comments.
- **Authorization Gate:** For third-party unpublished manuscripts, verify referee/author permission and publisher AI policy before intake; keep `【致作者】` and `【致编辑（机密）】` strictly separate. Never process grant-review material.
- **Action:** Confirm literal manuscript facts (exact wording, titles, denominators, table totals, figure labels) before critiquing. Classify every issue by ID (`F1..Fn` or `C1..Cn`), severity (`critical / major / minor / preference`), exact locator, and **smallest honest repair** (fix, qualify, narrow claim, or rebut).

## Stage 2 · Primary Evidence & Figure Check (`lj-evidence` + optional `lj-viz`)
- **Input:** Disputed, load-bearing, or newly added citations and quantitative claims.
- **Action:** Run `resolve_citation.py` (existence + Axis 1.5 retractions/preprint drift) and check passage-level support in full text (`search_local_corpus.py` / original PDF page). Invoke `lj-viz` (`preflight_figure.py`) **only** when a figure carries an affected claim or encoding defect.
- **Hard Gate (Human Disposition Lock):** Researcher locks the stance (`agree / partial / rebut`) and approved scope of edits for each major item. Never promise unperformed analyses in a response plan (`validate_report.py --mode response`).

## Stage 3 · Faithful Revision & Drift Check (`lj-write`)
- **Input:** Approved disposition plan + verified citations/figures.
- **Action:** Revise affected manuscript passages and draft direct, non-defensive point-by-point responses (`lj-write`). Run `lj-write/scripts/check_drift.py --before <orig> --after <rev>` to confirm zero unintended token-level changes to numbers, units, signs, figure/table IDs, or citations (and visually verify group-to-value pairing).
- **Stop Criterion:** Every critical/major finding has a verified fix, scope qualification, or evidence-backed rebuttal, and `validate_report.py` / `check_drift.py` pass cleanly.
