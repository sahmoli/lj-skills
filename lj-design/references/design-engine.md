# Discriminating Study Design Engine

Companion to `lj-design/SKILL.md`. Before adding any control, covariate, or robustness check, ask: **which named inferential threat does this element test, and what result would change `H` vs `H_alt`, narrow the claim, or trigger a stop/pivot?** Omit anything that is decorative checklist padding.

## 1. Strong Inference Operationalized (Platt 1964)
1. **Rival hypotheses:** Pit `H` against the strongest `H_alt` (often sampling/detection artefact, confounding gradient, demographic sorting, or regression to the mean).
2. **Crucial observation:** Identify an observable contrast where `H` and `H_alt` predict **different or opposite** outcomes. A design whose outcome "would be interesting either way" discriminates nothing.
3. **Falsifier:** State the concrete empirical result that kills or narrows `H`.
4. **Decisive contrast / control:** Choose the cleanest feasible structure that breaks the driver–confounder correlation:
   - Manipulative experiment (random assignment + procedural control)
   - BACI (before–after–control–impact)
   - Natural experiment / exogenous shock
   - Orthogonal spatial gradient (vary focal driver while holding major confounders constant; flag space-for-time assumptions)
   - Observational causal design (matching / stratification / DiD / IV, stating residual confounding plainly)

## 2. Unit-Mismatch, Canonical Taxonomy & Data-Reality Screen
- Check four units separately: **sampling unit**, **mechanism-bearing unit**, **spatial/temporal grain & extent**, and **management/intervention unit**. If obtainable data cannot resolve the mechanism unit, re-scope before drafting protocol details.
- **Canonical taxonomy inheritance:** When defining intervention categories, funding/governance modes, outcome dimensions, causal results chains, or literature-extraction schemas, adopt established community classifications verbatim with citation (e.g., IUCN–CMP conservation actions `Salafsky et al. 2008`, Theory of Change / Results Chains, CEE / ROSES guidelines) rather than inventing rhetorical shorthand or private bucket labels; introduce a sub-split only when an explicit empirical gap in existing standards requires it.
- Ground confounders and resolution limits in the active project's **data dictionary / verified dataset metadata** (or mark unverified dataset properties as `⚠待核` access gaps rather than guessing). Screen premises against [shared inference exclusions](../../_shared/exclusions.md).

## 3. Minimum-Sufficient Analysis Specification (SPEC, Not Unrequested Execution)
Name the simplest adequate model family, its core assumptions, and its primary failure mode:
- **Occupancy / N-mixture / SDM:** imperfect detection vs true occupancy; spatial autocorrelation; presence-only ≠ abundance.
- **Phylogenetic / comparative (PGLS):** tree/branch-length sensitivity; measurement error.
- **Demographic / PVA:** vital-rate uncertainty; density-dependence form.
- **Remote sensing / spatiotemporal:** sensor cross-calibration, QA/cloud masking, native pixel ceiling.
- **Hierarchical / mixed models:** true independent `n` vs pseudoreplication across sites/years/individuals.
- **30-Minute Feasibility Probe (for early-stage ideation):** specify one fast, concrete check on authorized sample data (e.g., intersecting species × repeat-visit footprint `N`, checking whether effort is recorded for non-detections, or testing extraction accuracy on 10 sample papers) and record the **stop/pivot threshold** *before* inspecting the result.

## 4. Ethics & Provenance
Flag real animal-welfare, permit, threatened-taxon location sensitivity, Indigenous/community data governance (CARE), or legal access constraints; skip performative boilerplate when no redline applies. Use `scripts/validate_output.py` when validating saved schema-formatted design cards.
