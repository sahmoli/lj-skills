---
name: lj-concept
description: >-
  Dissect and master a single concept, principle, or model across any discipline with surgical
  clarity, primary-source honesty, discriminating examples, failure boundaries, and optional
  active-learning transfer checks.
---

# lj-concept

Dissect a single concept, principle, or model so a learner or researcher can **define, distinguish, predict, and intervene** on a new case. Deliver directly in chat by default; write to a personal Wiki or note vault only when requested.

- **Scope boundary:** Use `lj-concept` for one concept/principle and its nearest confusable twins; use `lj-backbone` for a whole field's axiom-to-theorem dependency graph; use `lj-read` for reconstructing a specific paper or book; use `lj-question` for research question selection.

## 1. Classify the Proposition First (By Claim Type, Not Department Label)
- **Formal / Logical:** exact definition, derivation chain, necessary conditions, and counterexample boundary.
- **Empirical / Mechanistic:** generating process, measurement grain/unit, competing predictions, and breakdown boundary.
- **Normative / Institutional:** explicit value premises, argument structure, affected parties, strongest opposing case, and crux of disagreement.
- **Mixed:** separate formal, empirical, and normative layers explicitly.
- Calibrate authority honestly: distinguish home-domain primary scholarship from cross-disciplinary synthesis (`⚠待核` where primary originals remain unread; see [rank-interface.md](references/rank-interface.md) when learner-level adaptation is requested).

## 2. Core Dissection Bar (Accuracy Outranks Novelty)
1. **Concrete before abstract:** anchor on a specific phenomenon or common misconception before introducing terminology; carry the same concrete case across variations rather than switching examples mid-stream. Never leak internal prompt labels into user-facing headings.
2. **Nearest confusable distinction & failure boundary:** contrast the concept against its closest look-alike on an observable case where their predictions or classifications diverge, and name a real counterexample or breakdown condition.
3. **Compute before sketching:** any quantitative thought experiment (thresholds, ratios, scaling, geometry) must state assumptions and actually compute the numbers; distinguish calculated quantities, cited empirical outputs, and qualitative schematics (never invent smooth trend curves from prose).
4. **Three-part source check:** verify source identity, passage-level support (denominator, unit, direction), and scope independently; screen against [shared exclusions](../_shared/exclusions.md) and (for ecology) [domain-ecology.md](references/domain-ecology.md).

## 3. On-Demand Active Transfer Drills (Invoke Only When Helpful or Requested)
- **Predict first:** when the user asks to be tested ("quiz me / don't give the answer yet"), pose a minimal discriminating scenario and **pause for their response** before explaining.
- **Vary one condition:** change a single load-bearing condition on the same object and trace whether the verdict flips.
- **Stop cleanly:** state what is established and what remains open (`⚠待核`) without inventing pseudo-axioms.

## 4. Progressive References
- Analytical lenses: [references/lenses.md](references/lenses.md) · Learner calibration: [references/rank-interface.md](references/rank-interface.md)
- General inference exclusions: [../_shared/exclusions.md](../_shared/exclusions.md) · Ecology-specific: [references/domain-ecology.md](references/domain-ecology.md)
- Structured concept card template: [references/concept-page-template.md](references/concept-page-template.md)
- Cross-concept mechanistic link audit ([validate_weave.py](scripts/validate_weave.py)): [references/weave-engine.md](references/weave-engine.md)

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Never overwrite human-authored judgment sections (`My Take` / `我的判断`) when updating local notes.
