# Workflow 01 · Idea → 30-Minute Pilot Probe → Proposal

> **Purpose:** Take an early research spark or student discussion to a defensible, right-sized proposal **without** abstract-only gap claims, defensive scope creep, or discovering missing data after writing v2.0.
> **Skills composed:** `lj-question` → `lj-evidence` → `lj-design` → `lj-write` (+ optional `lj-viz`).

---

## Stage 1 · Diverge & Screen Candidates (`lj-question`)
- **Input:** Raw observation, meeting notes, policy shift, or student draft (+ researcher's active portfolio/radar if available).
- **Action:** Generate 2–3 distinct candidate questions (`Explore` / `Select`). State each candidate's observation, repeating unit, spatial/temporal grain, strongest rival explanation (`H_alt`), and discriminating prediction.
- **Guardrail:** Enforce the **30-second elevator test** and tier complexity budget (`course/FYP` vs `summer/pilot` vs `PhD/flagship`). Mark novelty `⚠待核`.

## Stage 2 · Primary Full-Text Grounding (`lj-evidence`)
- **Input:** Top 1–2 candidate questions from Stage 1.
- **Action:** Run `discover_sources.py` (topic + backward/forward snowballing from key seed DOIs), fetch verified legal OA full texts (`fetch_oa.py --convert` / `ingest_local.py`), and inspect actual methods, denominators, canonical terminology/classification standards, and caveats in the nearest 5–8 primary papers (`lj-read` as needed).
- **Hard Gate ① (Human Lock — Question & Story):** Present the surviving gap and a **≤30-second elevator statement** (*question + strongest rival + decisive observation*). **Pause for researcher lock.** Downstream stages may not add defensive sub-questions once locked.

## Stage 3 · 30-Minute Feasibility Probe (`lj-design`)
- **Input:** Locked question + candidate datasets or literature corpus.
- **Action:** Before drafting a full proposal, specify and execute **one ≤30-minute empirical probe** with a **predeclared stop/pivot threshold** recorded *before* viewing results:
  - *Observational / open-data study:* check exact species × repeat-visit / spatial intersection `N`, effort recording on non-detections, and resolution ceiling.
  - *Synthesis / AI-extraction study:* run the extraction schema on 5–10 real full-text papers to verify recall, table/SI coverage, and exclusion edge cases.
- **Hard Gate ② (Human Go / Pivot / Kill):**
  - **Go:** Probe meets threshold → lock minimum-sufficient study design (`lj-design`).
  - **Pivot / Kill:** Sample `N` collapses, effort/denominator is unrecoverable, or extraction fails → return to Stage 1 or archive in an incubation log with the exact blocker recorded. Never write a full proposal over a failed probe.

## Stage 4 · Minimum-Sufficient Proposal (`lj-write` + optional `lj-viz`)
- **Input:** Approved design + pilot probe numbers + verified citations.
- **Action:** Draft a concise proposal clearly separating **verified pilot observations** from **untested full-study assumptions**, check zero numeric/citation drift (`lj-write/scripts/check_drift.py`), and optionally add one causal/design diagram (`lj-viz`).
- **Stop Criterion:** Proposal states question, rival `H_alt`, decisive contrast, probed sample `N`, and explicit limitations; record decisions in your project research log.
