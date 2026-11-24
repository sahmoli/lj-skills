# Nature visual system — scientific craft, not decoration

This reference owns the aesthetic defaults for `lj-viz`. It is deliberately narrower than a multi-journal
theme library: the target is a quiet, information-dense, publication-width figure that would not look out of
place in flagship *Nature*. Exact upload rules remain dated facts in `lj-journal`; this file defines visual
craft.

## Evidence boundary

Three evidence layers must not be blurred:

1. **Nature official requirements**: live, dated technical facts are owned only by `lj-journal`, currently in
   `lj-journal/journals/nature.yaml`. `lj-viz` consumes a verified venue contract when one is supplied; it
   does not duplicate widths, height limits, DPI, colour mode or delivery-format numbers here. The stable
   visual principles retained here are editable type, restrained linework, readable axes/units, accessible
   colour and avoidance of grids, coloured text, patterns, shadows, overlaps and superfluous icons.
2. **Local published-figure corpus**: 139 main figures visually coded from 34 original Nature/Science ecology
   papers, then 18 representative corpus figures plus all 12 main figures from Juan's two supplied papers
   re-coded for colour, typography, density, spacing, legends, annotations and icon grammar. This second set
   is purposive craft evidence, not a frequency sample.
3. **Implementation references**: public, pinned GitHub sources were inspected for reusable engineering
   moves. We borrow pre-code reference boards (AgentFigureGallery), panel alignment/guide collection
   (patchwork/cowplot), snapshot diffs (pytest-mpl/vdiffr), colour-vision simulation (colorblindr), and
   reproducible manual/SVG polish (Pylustrator/Fig-Draw). SciencePlots remains a scoped style-sheet floor,
   not an aesthetic certificate. Third-party “Nature palettes” and universal composition checklists are not
   treated as publisher guidance.

Do not refresh publisher facts from this reference. Invoke `lj-journal` and update its Nature card from the
official pages; the resulting export contract may constrain the canvas without changing this visual system.

## Beauty Contract — required with the Figure Contract

Before styling, record:

```text
Reference Board: >=2 source figure/page IDs · borrow · avoid
Visual direction: quiet-analytical | spatial | mechanism | image-led
Hierarchy: hero/support + what evidence earns each panel's physical area
Palette: neutral scaffold · one scientific namespace · explicit meaning→colour map · critical comparison
  pairs · redundant carrier where needed · CVD collision check
Spacing (mm): outer · panel gutter · within-panel gap · label offset
Typography: family · body/tick/label sizes at final output
Legend strategy: direct labels | one shared strip | one compact legend | none
Icon policy: none | repeated-small | diagram-symbol; purpose + source/licence + optical size
Placement: longest-label stress case · reserved label/icon bands · 1.5 mm clearances · fallback ladder
Density/title policy: data occupy the panel; caption-only or short headers; no explanatory UI cards
Scaffolding: square geometry, axes/ticks/reference lines; no default grid, shadow or coloured text
```

Scientific faithfulness is a constraint; visual craft is also a ship requirement. A figure that is correct
but has no hierarchy, accidental gutters, competing colours, repeated legends, or clip-art decoration is not
finished.

## 1. Reference before code

Choose close references before drawing when a new visual language needs grounding. Match the evidence
architecture where possible and record a specific move to borrow and a failure to avoid. A useful note is
“Pigot Fig. 3: repeat small silhouettes above taxon-aligned facets; avoid eleven colours when the paper only
contrasts two conditions”, not “Nature style”. Build a monochrome thumbnail first. Colour cannot rescue a
weak reading path, empty hero or broken alignment.

## 2. Colour is a paper language, not a house palette

Stable neutral scaffold:

- `ink #202124` — text, primary axes, essential outlines;
- `context #D9DDE2` / `context_soft #F0F1F3` — baselines, background observations, facet scaffolding;
- `missing #8B9098` — missing or unavailable, never silently transparent.

Then choose one semantic namespace. Shipped ecology defaults are deliberately limited:

- `surrogacy`: umbrella coral, keystone blue, flagship warm ochre, matching Juan's established U/K/F language;
- `portfolio`: pair blue-teal, singleton salmon, preserving Juan's pair-versus-singleton language while
  remaining separable under red-green colour-vision simulations;
- `period`: before red, after blue, useful for policy/intervention timing;
- `evidence`: focal blue, comparison ochre, positive green, negative red;
- `taxonomic`: a restrained multi-hue set only when taxon identity is the actual comparison;
- continuous data: a declared perceptual sequential or diverging scale, never the categorical namespace.

These are corpus-grounded defaults, not an official Nature palette. A paper-specific mapping is preferable
when the manuscript already has a coherent language.

Rules:

- Begin with neutrals + the smallest semantic namespace that answers the reader task.
- Use softened fills and darker strokes from the same family; do not introduce a new hue for uncertainty.
- A multi-category palette is conditional. Stable ecological entities may need distinct hues, but an
  experiment with control versus treatment does not need eight Okabe–Ito colours.
- Keep each semantic colour token constant across every panel and figure. The same hue cannot mean “pair”
  in one panel and “keystone” in the next. Do not force every biological
  entity to have a colour: if colour means treatment or evidence role, use silhouette/text/shape for taxon
  identity. Colour hierarchy must match evidence hierarchy after rendering; a dark baseline must not
  dominate the result.
- Never use coloured text as the key. Use black/white text plus a coloured keyline, swatch, mark or direct
  spatial association.
- Sequential, diverging and categorical palettes are different semantic objects. Do not use a pretty
  sequential ramp for unrelated categories.
- Accessibility is evaluated on **declared critical pairs**, not every theoretical pair in a large
  taxonomic palette. If two categories must be compared, name that pair and require a redundant carrier
  (position, label, shape or line style) whenever colour alone is fragile. Use `audit_palette.py --builtin`
  to regression-test shipped namespaces and `audit_palette.py <manifest>` for a paper-specific mapping.

## 3. Spacing is measured rhythm

Use the shared millimetre scale: `1.5, 2.5, 4, 6, 9`.

- 1.5 mm — hairline separation, label-to-mark clearance;
- 2.5 mm — compact within-panel gap;
- 4 mm — standard panel gutter and outer breathing room;
- 6 mm — modality break, legend-to-data gap, hero/support separation;
- 9 mm — major section break in a complex composite.

“Minimize white space” in the Nature guide means remove accidental waste, not remove breathing room. Align
panel edges and baselines; use repeatable gutters; leave extra separation where dark image plates meet white
analytical plots. Dense content may use 2.5 mm gutters only after a final-size collision check.

The contract must drive code. Full Python composites should use `canvas_grid(...)`, which creates exact axes
boxes in millimetres and writes a renderer geometry sidecar; `nature_grid(...)` remains suitable for quick,
simple panels that are checked after rendering. R composites use `nature_canvas_positions()` plus
`nature_canvas_grob()`. An undeclared local spacing number is a failed handoff, even when it happens to look
acceptable at editor zoom.

## 4. Hierarchy, density and composition

- Choose a hero only when evidence earns it: a map with many locations, an image plate, a dense mechanism or
  the main estimate can justify more area. A sparse threshold, slogan or three-symbol cartoon cannot. Do not
  enforce a 45–60% hero quota.
- Use equal small multiples only when repeated comparison is the task and scales/geometry are genuinely
  shared.
- Panel order follows the evidence dependency. Lowercase labels are navigation, not decoration.
- Avoid plotting-library titles inside every panel. Prefer concise axis labels, direct labels, and a caption;
  use a short panel header only when it removes ambiguity. Large explanatory headlines belong to slides,
  not paper figures.
- White space is distributed, not maximized: data should fill its allotted panel, repeated axes should align,
  and a legend should not create a weak empty column. Square corners and open axes signal scientific figure;
  rounded cards and tinted canvases read as UI or consulting slides.
- One paper-level visual vocabulary: same entity label/silhouette, semantic colour role, line style, symbol,
  direction and terminology across figures. Keep semantic namespaces separate; a colour used for treatment
  in one figure cannot quietly become species identity in the next.

## 5. Legends and annotations

Preferred order:

1. direct label when the identity is stable and collision-free;
2. one shared legend strip for repeated panels;
3. one compact frameless legend near the decoding task;
4. repeated panel legends only when panels must stand alone.

Use reference lines, bands, arrows and callouts only when they shorten a specific inference. An annotation
must identify its relation (`threshold`, `event`, `comparison`, `flow`, `boundary`) in the contract. Avoid
opaque label masks that cut holes through data; move labels outside the local data envelope and use thin
keylines.

### Placement contract

Plan labels as geometry, not prose added after plotting:

1. Render the longest real label and widest statistic before fixing panel widths. Placeholder names such as
   `Species A` are not a valid stress test.
2. Reserve a label band outside the data envelope when endpoints or long taxa must be named. Do not spend
   data area and then hope that automatic repulsion or manual nudging finds empty space.
3. Apply one deterministic fallback ladder: `outside data → reserved margin band → thin leader line → compact
   legend`. Shorten only through a paper-level approved dictionary; never abbreviate the same taxon differently
   across figures.
4. Require at least 1.5 mm from page/panel edges and between a text box and semantic icon. Overlap is a hard
   fail. A nearby label without adequate clearance is a warning even when glyph pixels do not touch.
5. Treat `silhouette + label` as one compound layout unit. In Matplotlib use the shared `add_icon_label()`
   helper; in R assemble the grobs before placing them. Independent icon and text anchors caused visible
   collisions in the two-paper regression test.
6. If more than roughly six direct labels compete in one local region, a shared legend or aligned label strip
   is normally more reliable. This is a density trigger, not a universal label limit.

Automatic repulsion is a repair tool, not a layout strategy: it can move a label away from its referent,
change reading order between runs, or push content into a neighbouring panel. Save final positions in code
and run the PDF geometry audit after export.

## 6. Small icons and schematics

Nature explicitly discourages decorative or ambiguous icons. Icons are allowed only when they make a
real-world system or experimental process faster to understand.

- Default is `none` for quantitative panels.
- If semantic, state the noun/relation the icon denotes and keep a text label when ambiguity is possible.
- Use one coherent vector language: same stroke (normally 0.5–0.75 pt final), corner treatment, fill logic,
  optical size and viewing angle. Never mix emoji, clip art, silhouettes and detailed illustrations.
- Prefer simple geometric primitives or a provenance-recorded, licence-compatible SVG set. Do not invent a
  species silhouette or map symbol that could be mistaken for evidence.
- In organism-centred figures, a restrained species silhouette plus text may serve as a redundant identity
  channel. The recurrent corpus grammar is **small and repeated**: silhouettes sit above aligned taxa, beside
  a row, or at the endpoint of a direct label, normally at a common 5–9 mm optical height. A single oversized
  animal becomes a mascot and consumes evidence area. Use `references/species-silhouettes.md`: prefer exact
  taxon assets, disclose any approximation, and lock the same registry asset across the whole paper.
- Keep icon colour tied to the figure's palette roles. Icons do not receive a separate decorative palette.
- Arrows encode direction/flow; connectors encode association. Avoid gratuitous arrowheads.

## 7. What the 30-figure craft sample actually contributes

- strong figures often use a recognisable hook—a species strip, map silhouette, intervention timeline,
  branching mechanism or repeated ridge grammar—but the hook is integrated with the measurement task;
- dense panels feel controlled when axes, baselines, glyph heights and gutters repeat exactly;
- direct labels and shared strips preserve attention better than a legend repeated in every small multiple;
- vivid multi-hue systems occur when many taxa/categories are the subject (Cámara, Pigot), while two-condition
  questions use two stable families (Smith, Xiong, Juan's portfolio paper);
- illustrations can be large in conceptual figures (Bialic, Chen), but they replace ambiguity rather than
  decorate empty space;
- typography is generally subordinate to marks: short labels, narrow line lengths, no promotional headline.

These observations guide selection; they are not universal requirements or acceptance predictors.

## 8. Final-size craft gate

Inspect the rendered output at its declared physical dimensions, panel by panel and as a whole:

- If a hero is declared, can its evidence be found in two seconds without reading the caption? If none is
  declared, does the equal-grid comparison scan cleanly?
- Is any support element darker, larger or more saturated than the hero without scientific reason?
- Are gutters deliberate and repeated, or do they look like accidental leftovers?
- Can a legend be removed, shared or replaced by direct labels?
- Are label baselines, decimals, panel edges and small multiples optically aligned?
- Are marks, intervals and labels separated by at least one visible clearance unit?
- Do icons/lines share one visual grammar and a stated purpose?
- Does the figure remain coherent in greyscale and under colour-vision simulation?

Run three distinct reviews:

1. technical preflight: size, fonts, DPI, artifact freshness and manifest completeness;
2. visual regression: compare against an explicitly human-approved baseline and inspect the pixel diff;
3. visual craft: compare at final size to the selected Reference Board and inspect hierarchy, density,
   alignment, semantic colour, typography, legend economy and icon grammar.

Deterministic `PASS` applies only to step 1 or a declared snapshot tolerance. It cannot certify elegance,
hierarchy or icon meaning. A human/vision review remains mandatory.
