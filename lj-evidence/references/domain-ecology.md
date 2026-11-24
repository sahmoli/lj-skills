# Ecology & Conservation Domain Passes (`lj-evidence` optional lens)

Load this reference **only** when auditing ecology, conservation biology, or environmental-science manuscripts/notes. Do not apply ecology-specific defaults to unrelated disciplines (AI/CS, education, cognitive science, history).

1. **Method-citation correctness.** When a manuscript states *"we used `<method>` (`X et al.`)"*, verify that `X` actually introduces or justifies that method rather than being decorative or mismatched (e.g. citing an occupancy paper for an N-mixture model, or a non-phylogenetic study for PGLS). Coordinates with `lj-review` design-type checks.
2. **Debunked-default citation.** Flag citations propping up debunked ecology defaults (balance-of-nature, diversity→stability-as-universal-law, carrying-capacity-*K*-as-measured-truth, single-stable-climax) for scrutiny; cross-check against `lj-concept/references/domain-ecology.md` and `lj-concept/references/exclusions.md`.
3. **Self-citation / venue-fit sanity (light).** Flag when a broad empirical claim leans exclusively on the authors' own prior papers where independent corroboration is expected, or when a load-bearing method/dataset citation is missing entirely.
