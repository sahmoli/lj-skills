# Visualization engine

Use this reference for scientific choices after the Figure Contract is known. Venue production numbers
belong to `lj-journal`; execution details belong to `build-and-qc.md`.

## 1. First ask whether this should be a figure

Use a figure when spatial structure, distribution, uncertainty, trajectory, relationship, mechanism or
several coordinated comparisons are necessary to the claim. Use a compact table when readers need exact
values across a modest matrix; use text when there are one or two results and no visual pattern to inspect.
Do not manufacture a multi-panel figure merely because a manuscript has an available slot.

## 2. Start from the reader task

| Reader task | Usually strong first encoding | Common rejection |
|---|---|---|
| Compare estimates to a null | coefficient/dot-whisker plot; common zero/reference line | bars of coefficients |
| Compare observed distributions | points + interval/box/violin chosen for sample and density | bar-of-means that hides spread |
| Follow an ordered gradient | points/lines with model interval; small multiples when groups recur | unordered rainbow categories |
| Locate spatial pattern | task-matched projection + map, often paired with distribution/model panel | Web Mercator used for area/density |
| Diagnose model or mechanism | observed-vs-predicted, residual/validation panel, path diagram only when identified | decorative causal arrows |
| Compare scenarios/trade-offs | aligned small multiples or position-based frontier; common scales | stacked areas when exact comparison matters |
| Explain a process | minimal schematic paired with the quantitative test that could fail it | schematic occupying the evidence slot |

Use Cleveland & McGill's position/length/angle/area/colour findings to prefer more accurately decoded
channels when the reader needs numerical comparison. Do not apply the hierarchy mechanically to tasks such
as topology, geographic location, or category identification.

## 3. Axis policy is quantity-specific

| Quantity/mark | Policy |
|---|---|
| Absolute magnitude encoded by bar or filled area length | Start at the meaningful zero. Otherwise change mark or show the full baseline. |
| Difference/effect/coefficient | Centre or clearly mark the scientific null; symmetric limits help comparison but are not mandatory when wasteful. |
| Scatter/regression | Show the domain needed to judge relationship, leverage, and extrapolation; zero is optional. |
| Time series | Show the relevant observation window and breaks; do not imply an unobserved baseline. |
| Log/allometric relationship | State transform/base, show readable tick labels, and express the claimed effect on an interpretable scale. |
| Probability/proportion | Respect the valid domain; zero/one may be omitted if the mark is positional and the zoom is explicit. |
| Map | Projection follows measurement purpose. Never infer area/density/distance from EPSG:3857. |

Truncation becomes misleading when the visual mark depends on baseline length or the crop hides variation
needed to evaluate the claim. A zoomed position plot with explicit limits is not automatically dishonest.

## 4. Uncertainty follows the estimand

Ask four questions in order:

1. What varies: observations, sites, biological units, model parameters, predictions, or space/time?
2. Which variation is relevant to the claim?
3. What interval/distribution represents it: SD, SE, CI, credible interval, prediction interval, quantiles,
   bootstrap distribution, or raw observations?
4. Where is the repeating unit defined: panel, caption, manifest, or methods?

Show uncertainty when the figure makes an inferential statement. Define target, type, level, and repeating
unit. Do not demand error bars for a deterministic schematic, complete census, raw map, or single fitted
curve when the relevant uncertainty is shown elsewhere or honestly unavailable. Do not call technical
replicates `n` independent biological samples.

Prefer effect size plus interval over significance stars. A p-value may supplement the estimand but should
not replace magnitude, direction, and uncertainty.

### Bayesian and latent-scale outputs

- Show the posterior quantity that answers the claim: distribution, median/mean plus credible interval, or
  probability of a scientifically meaningful region. Do not turn a posterior into a significance-star plot.
- Pair important fitted claims with posterior predictive checks. Prior sensitivity and sampler diagnostics
  normally belong in Extended Data unless the central claim depends on them; never hide failed convergence.
- Distinguish credible intervals for parameters from predictive intervals for future observations.
- For latent scores, ordinations and embeddings, state orientation/identifiability conventions and whether
  scales are comparable across panels or fits. If scales are not comparable, facet or normalize only with a
  declared transformation and disclose the boundary; visual alignment must not imply a common metric.

## 5. Multi-panel contract

Write one line per panel:

`label → evidence role → quantity/estimand → visual task → why the claim fails without it`

Then apply two tests:

- **Dependency test:** order panels as the reader must reason, not as experiments were completed.
- **Occlusion test:** cover one panel. If no claim-relevant information disappears, merge, move to Extended
  Data, or delete it.

Use hero/support layouts when one panel carries the main estimate and others establish context or validity.
Use equal-sized small multiples only when repeated encodings and common scales make comparison the task.
Overview→zoom→quantification is useful for spatial/image evidence; the zoom must not become anecdotal proof.

## 6. Data-presentation contract

Before layout, record: category/order rule; displayed axis domain and breaks; unit and transform display;
approved abbreviations; label priority/fallback; and whether repeated panels genuinely share a comparable
scale. This prevents plotting defaults from silently reordering categories, changing limits or inventing
inconsistent abbreviations during composition.

## 7. Colour, spacing, legends and annotation

- Use stable neutrals plus one paper-level semantic namespace from `nature-visual-system.md`; declare every
  meaning→colour assignment and prevent cross-figure collisions. There is no universal Nature signal/accent
  palette. Okabe-Ito is an accessibility reference, not the default eight-colour cycle.
- Categorical: use a stable qualitative palette only when categories are the scientific quantity; keep
  identity constant across the figure set.
- Ordered magnitude: perceptually ordered sequential palette.
- Signed deviation: diverging palette centred on the scientific reference.
- Add shape, line type, direct labels, facets, or position when colour would otherwise be the sole carrier.
- Use arrows only for a declared relation or reading direction. A decorative arrow is visual prose without
  evidence.
- Set outer margins, panel gutters, within-panel gaps and label clearance in millimetres from the shared
  `1.5 / 2.5 / 4 / 6 / 9` spacing scale. Optical alignment and repeated rhythm matter more than equal panels.
- Prefer direct labels, then one shared legend strip, then one compact frameless legend. Repeated legends
  need a panel-independence reason.
- Add reference lines, uncertainty bands, and direct labels when they shorten decoding; remove borders,
  grids, legends, icons, and callouts that do no work. Semantic icons retain a text label when ambiguous and
  must share one vector stroke/fill language plus source/licence provenance.

## 8. Maps and conservation privacy

Choose the map product before choosing a CRS:

- area/density/global comparison → equal-area projection (for example Equal Earth EPSG:8857 globally);
- local distance/buffer analysis → a suitable local projected CRS whose distortion is acceptable;
- location-only display → geographic coordinates may be adequate when quantitative geometry is not implied.

State CRS and spatial unit. Add a scale bar when distance is part of interpretation; add a north arrow only
when orientation is not conventional or obvious. For sensitive species, prefer governed aggregation,
grid/bin counts, coarsening, access control, or a documented displacement/privacy model. Never publish raw
coordinates merely because the plotting code can, and never use casual degree jitter as a privacy method.

## 9. Caption and provenance contract

A caption begins with the whole-figure claim/title, then explains panels in reading order. `lj-viz` owns
the scientific caption contract; `lj-write` may render final legend prose against it without changing fields. Include only
applicable fields:

- quantity/estimand and units;
- repeating unit and sample definition;
- uncertainty target/type/level;
- statistical model/test only where needed to interpret the mark;
- projection/spatial unit/privacy transformation for maps;
- filters, exclusions, transformations, and symbol definitions.

The manifest traces:

`artifact ← exact command ← code ← data columns/files ← transforms/filters ← authorised claim`

Manual assembly may align vector/raster panels, labels, and legends. It must not redraw data, change scales,
or create values that cannot be regenerated.

## 10. Audited anchors

- Cleveland & McGill (1984), graphical perception — channel accuracy for quantitative comparison.
- Rougier, Droettboom & Bourne (2014), *Ten Simple Rules for Better Figures* — message-first design.
- Wong (2011), Nature Methods Points of View — colour blindness and redundant distinction.
- Crameri et al. (2020), scientific colour maps — perceptual uniformity and false gradients.
- Wilke (2019), *Fundamentals of Data Visualization* — task/encoding and final rendering.
- The local Nature/Science ecology corpus audit — field-specific architecture evidence; see
  `ecology-figure-architectures.md` and the Wiki audit dataset.
