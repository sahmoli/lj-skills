# Workflow 03 · Deep Reading → Concept Note, Deck, or Book Chapter

> **Purpose:** Transform primary papers, books, and cross-disciplinary concepts into durable, source-anchored notes, teaching slides, or book chapters while protecting human authorship (`My Take`) and primary-source boundaries.
> **Skills composed:** `lj-evidence` → `lj-read` (+ optional `lj-concept` / `lj-backbone`) → `lj-write` / `lj-talk`.

---

## Stage 1 · Primary Full-Text & Coverage Grounding (`lj-evidence` + `lj-read`)
- **Input:** Target paper(s), book, or focal concept/principle.
- **Action:** Retrieve verified legal full texts (`lj-evidence/scripts/fetch_oa.py` or `ingest_local.py`) and record an explicit **artifact/coverage inventory** (`lj-read`). Trace `claim → estimand → unit → evidence → hidden assumption / falsifier`, keeping author framing separate from verified data.
- **Optional Concept / Field Lens:** Invoke `lj-concept` when isolating a single transferable concept/principle (criteria, nearest confusable twin, computed thought experiment, breakdown boundary), or `lj-backbone` when mapping a whole chapter's dependency graph.

## Stage 2 · Human Judgment & Scope Gate
- **Hard Gate (Human Authorship & Release Subset):**
  - The researcher writes or confirms their own core judgment (`My Take` / chapter thesis) — AI never fabricates first-person conviction.
  - Separate **original work authorship** from **note/chapter authorship**, cap claims at actual coverage (`partial` if SI or book chapters are unread), and confirm permissions for any third-party figures.

## Stage 3 · Downstream Synthesis (`lj-write` / `lj-talk` / Visual Renderer)
- **Book / Essay Branch (`lj-write`):** Draft prose from the locked thesis and verified primary passages; run `check_drift.py` on quantitative/cited claims.
- **Teaching / Talk Branch (`lj-talk`):** Build a structured deck plan (`lj-talk/references/deck-plan.md`, `validate_outline.py`) and editable `.pptx` slide deck preserving provenance and active student predictions.
- **Visual Note Branch:** Export a clean, verified content brief (definition, discriminating contrast, computed metric, dated lineage, debates, and public-only links) to the user's chosen visual note renderer, requiring human sign-off on the rendered preview before publication.
