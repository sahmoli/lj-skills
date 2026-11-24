# Exploration & Structure-Mapping Engine (`Explore`)

Single source of truth for divergent question generation. Return an **unranked** pool so selection gates do not prematurely prune non-obvious leads.

## 1. Structure-Mapping Bar (Gentner 1983)
Align **relational skeletons**, never surface topic words:
1. Strip the focal phenomenon to its core relation (e.g., connectivity percolation on a network, critical slowing down near a regime shift, feedback amplification, Pareto trade-off, allometric scaling, selection/filtering, bet-hedging under noise, spatial self-organization).
2. Import theory from a distant domain that owns that exact mathematical or causal relation.
3. **Prediction bar:** retain an analogy only if a relation true in domain B yields a **non-trivial, checkable prediction** in ecology/conservation A. Pure renaming is discarded.
4. **Disanalogy / breakpoint:** explicitly name where the mapping breaks — the breakdown point often yields the sharpest empirical question.

## 2. Calibrated Atypicality Guardrail (Uzzi et al. 2013)
Highest-impact science pairs a **conventional, well-grounded core** (tractable study system, established measurement, clear baseline) with **one** atypical structural bridge (`越远 ≠ 越好`).
- Flag candidates that stack an exotic analogy + speculative mechanism + unverified system as `speculative, Uzzi-stacked`.
- Seek tail diversity beyond first-association clichés (e.g., avoid reflexively mapping every patch network to `R0=1` unless it predicts a specific measurable threshold), while letting structural soundness govern retention (`Zhang et al. 2025`, arXiv:2510.01171).

## 3. Complementary Generation Moves (Use Only What Adds Real Variance)
- **Scale / Axis Transfer:** invert predictor and response, shift spatial/temporal grain by an order of magnitude, or fill an empty cell in a taxon × disturbance comparison matrix.
- **Outside-In Horizon:** trace an emerging policy, infrastructure, energy, land-tenure, or sensor/AI shift that creates a natural experiment before the ecology literature names it.
- **Outcome Back-Derivation:** state a concrete conservation decision that currently lacks decisive evidence and back-derive the minimum discriminating observation.
- **Assumption Inversion:** ask which "inevitable" background assumption could be otherwise, and identify a system where that assumption flips.

## 4. Honesty Floor
- Every priority or novelty lead starts `⚠待核` until verified via `lj-evidence`.
- Distinguish `grounded` (supported by cited primary work or known dataset) from `hypothesis-level` leads. Use `scripts/validate_pool.py` only when validating saved structured pool artifacts.
