# Ecology Figure architectures from Juan's Nature/Science corpus

## Evidence boundary

This reference is grounded in the local audit under
`wiki-knowledge/raw/datasets/2026-nature-science-ecology-figure-audit/`: a census of 2021–2026 PDFs and a
stratified visual sample. It describes observable published practice, not a causal recipe for acceptance.
Implementation is `paper-stated`, `PDF-observed`, or `unknown`; never infer software from style.

## Six recurring architectures

### 1. Spatial map → distribution → model

Use when location/extent establishes the phenomenon but cannot by itself support the mechanism. A map or
image is the setup/phenomenon; an aligned distribution quantifies magnitude; a model/validation panel tests
drivers or generality. Keep spatial colour scales stable and make the measurement unit explicit.

Observed example: Bourgoin et al. (Nature 2024), Fig. 1 pairs continent-scale hex maps with aligned canopy-
height distributions; later figures quantify edge distance and recovery. The maps are not left to carry the
causal interpretation alone.

### 2. Ordered gradient → effect summary → boundary

Use for succession, climate, distance, age, or time. Show trajectories on the scientifically meaningful
scale, then summarize recovery time/slope/effect and expose between-site or model uncertainty. Use common
axes for repeated attributes when comparison is the task.

Observed example: Poorter et al. (Science 2021) moves from an approach/map, through twelve recovery
trajectories, to aligned summaries and a network. The sequence is setup → dynamics → comparative estimate →
coordination, not experiment chronology.

### 3. Intervention/comparison → identification → consequence

Use for policies, management interventions, natural experiments, or treatment contrasts. Establish units
and exposure; show raw/pre-post or treatment-control patterns; present the identified effect with interval;
then add the cheapest validation that addresses the main rival explanation.

Observed examples: Kuiper et al. (Science 2025) uses a causal-pathway figure before intervention results;
Xiong et al. (Science 2026) uses aligned before/after boxplots for nine responses. These designs are visually
compact, but inference still depends on repeating units, temporal design, and concurrent changes stated in
the text—not on stars alone.

### 4. Conceptual decomposition → simulation → empirical test

Use when a new relationship or index must first be defined. Panel order should allow the reader to derive
the quantity, see expected behaviour under controlled variation, and then test it in real systems.

Observed example: Liang et al. (Science 2025) defines scaling relationships, uses simulated debts, then
tests regressions across plant/fish systems and closes with spatial/SEM interpretation. Null and 1:1 lines
carry explicit comparison roles.

### 5. Scale/scenario → trade-off or priority surface

Use when no single optimum exists. Keep scenario semantics stable across maps and plots; show the decision
surface, not only a ranked winner. A map can locate priorities, while a common-scale curve/frontier exposes
what is traded and where thresholds occur.

### 6. Conceptual overview → quantitative claim package

Use a schematic only when it reduces the reader's model-building cost. It should define entities, pathways,
or measurements; later panels must provide the quantitative evidence. If deleting the schematic leaves the
claim intact and comprehension unchanged, it is decoration or Extended Data.

Conceptual figures have a stricter maturity boundary because geometry can imply causality or certainty:

- **prototype** — an explicit reasoning sketch; may be generated rapidly, but cannot be shipped;
- **human-approved** — every entity, arrow, grouping, order and omission has been checked by the researcher;
- **ship** — the approved structure is rebuilt as editable vector geometry, uses the same paper vocabulary,
  passes final-size collision review and is linked to the quantitative panels or evidence it explains.

Generative imagery may help explore visual metaphors, never establish the scientific relation. An AI-created
arrow, species depiction or landscape arrangement is not evidence and must not become final merely because
it looks polished.

## Paper-level storyline roles

Main figures commonly distribute these jobs:

1. **setup/phenomenon** — system, measurement, geography, or central pattern;
2. **main comparison/estimate** — the result that changes the reader's belief;
3. **mechanism/decomposition** — why components or pathways generate it;
4. **validation/boundary** — independent data, sensitivity, rival explanation, or scope;
5. **implication/decision** — scenario, priority, consequence, or synthesis.

Not every paper needs all five. Descriptive and measurement papers should not be forced into a causal
rescue template. The load-bearing rule is dependency: each main figure must perform a necessary claim job.

## What the corpus changes in lj-viz

- Replace seven isolated chart-purpose labels with figure/panel evidence roles plus reader tasks.
- Treat multi-panel claim packages as the normal publication unit, while preserving single-panel simplicity.
- Make maps, gradients, effect summaries, validation, and Extended Data routing first-class ecology patterns.
- Make `n`, raw points, and uncertainty conditional on estimand/repeating unit rather than universal panel
  decorations.
- Judge final-size hierarchy and repeated encodings across the whole figure set, not one chart at a time.
