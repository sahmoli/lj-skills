# Deep Paper Reading Engine (`Paper`)

Apply only the checks needed for the reading goal; never turn deep reading into a fill-in-the-blanks ritual.

## 1. Portable Companion Schema (When Saving a Structured Companion)
```yaml
---
type: reading-companion
genre: paper
reading_status: complete | parked | halted
paper: "Full paper title"
authors: "First Author et al."
venue: "Journal (YYYY)"
source: "DOI or local page-anchored path"
created: YYYY-MM-DD
---
```
- Use `parked` only when the reader explicitly defers the paper; use `halted` only for blocked sections while preserving verified findings. Run `scripts/validate_companion.py` on saved schema files.
- Optional reading sequence: when author framing risks anchoring judgment, inspect **metadata → figures/tables (load-bearing evidence) → methods/results → discussion → abstract** (adapting Keshav 2007 as needed).

## 2. Artifact Inventory & Load-Bearing Evidence Trace
1. **Artifact Inventory First:** Explicitly record what is in hand (main text, figures/tables, Supplementary Information, raw/processed data, code) vs. absent. Missing SI or code caps coverage — never treat `unreported` or `unread SI` as proof that a control was omitted (`unreported ≠ unexecuted`).
2. **Evidence Chain:** For each claim that matters, trace:
   `claim → evidence role → estimand → repeating unit → uncertainty target → inference boundary`
3. **Quantitative & Visual Consistency:** Verify exact `n`, denominators/exclusions, interval meanings (SD vs SE vs CI), test-statistic/df/*p*-value arithmetic, main-text ↔ table/figure ↔ SI agreement, and multi-panel axes/scales panel-by-panel (with physical PDF page anchors when available).
4. **Jargon-Free Mechanism Test:** Restate the core mechanism without field-insider jargon. If stripping terminology leaves only a label, record `named, not explained` as an explicit boundary.

## 3. Hidden Assumptions & Anti-Performative Red-Team
- **Load-Bearing Premise:** Identify the unstated assumption (external-validity leap, stationarity, proxy-as-construct, or ignored Gould–Lewontin rival process) whose failure would collapse or narrow the conclusion, and state a concrete `falsifier` / weakening observation. Label diagnoses `grounded` (authors state it) vs `speculative` (reader inference).
- **Anti-Performative Critique Gate:** Separate presentation/wording issues from genuine methodological defects. Every major critique must state:
  1. Exact page, figure/table, equation, or SI locator;
  2. Concrete counterexample or testable repair;
  3. Why the critique itself could be mistaken (e.g., standard domain convention or unread SI).

## 4. Citation Lineage (`confirmed` vs `inferred`)
When intellectual lineage matters, check local full texts first, trace only claim-relevant backward foundations and forward updates/refutations, and label every citation edge `confirmed` (verified in read text) vs `inferred` / `lead` (never fabricate citation relationships from unread titles).
