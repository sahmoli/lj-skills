# Engineering practices borrowed from public figure tooling

This is implementation evidence, not a publisher style guide. Repositories were inspected at pinned commits
on 2026-08-15; re-verify before adopting a changing API or dependency.

| Practice | Primary implementation reference | Borrow | Do not infer |
|---|---|---|---|
| reference-first workflow | [AgentFigureGallery](https://github.com/Dsadd4/AgentFigureGallery/tree/62f6094ef0587a074ab115c2aab9cf6adb504233) | query/show/select references before code; record like/reject/selected and export a small reference bundle | its gallery is not evidence that a layout is Nature-level |
| deep control of Matplotlib | [Scientific Visualization](https://github.com/rougier/scientific-visualization-book/tree/62fa569f30333c817c13e4dc757877c1192fd15a) | treat typography, layout, ornaments and coordinates as explicit design objects | a library default or recipe is not a paper-specific composition |
| scoped style floor | [SciencePlots](https://github.com/garrettj403/SciencePlots/tree/b9b16959570bd2fbc9ff5118bacc423c3bddd592) | use styles in a local context and compose small concerns | a style sheet cannot certify hierarchy, density or semantics |
| panel assembly | [patchwork](https://github.com/thomasp85/patchwork/tree/6b1d88ce1da1c5cae3818d984edf80dc0bb3de8c), [cowplot](https://github.com/wilkelab/cowplot/tree/b18d820d3af26b749235c4e4bc18bf416fba88e1) | align panels, collect guides, declare widths/heights and preserve fixed aspects | equal grids are not always better; area follows evidence |
| visual regression | [pytest-mpl](https://github.com/matplotlib/pytest-mpl/tree/f58f8b6d8edc49457ce6682f1284f04c89e8561d), [vdiffr](https://github.com/r-lib/vdiffr/tree/dc4f8127d8e857a2703d98bacd302ce697eacfb3) | version human-approved baselines; fail on unexplained rendered drift; inspect diffs | pixel similarity says nothing about scientific validity or baseline quality |
| colour-vision review | [colorblindr](https://github.com/clauswilke/colorblindr/tree/90d64f8fc50bee7060be577f180ae019a9bbbb84) | inspect rendered simulations, not only hex contrast | a simulated pass cannot replace redundant encodings or user testing |
| reproducible manual polish | [Pylustrator](https://github.com/rgerum/pylustrator/tree/b0341ee96cd3d11aab62e444ad6bf8b0abb83ce2) | save manual alignment/label edits back into reproducible Python code | freehand edits may not redraw or alter data |
| editable SVG assembly | [Fig-Draw / SciCompose](https://github.com/xuedong-z/Fig-Draw/tree/cdcc225cd52cc1d607363f9e70e307dd254d42e8) | preserve font/line/marker size while resizing; align/distribute; trim whitespace; export editable SVG | a browser editor is optional and must not receive private data silently |

## Workflow used by lj-viz

1. Figure Contract establishes scientific truth conditions.
2. A Reference Board, when needed for a new visual language, records relevant figures and `borrow/avoid`.
3. A monochrome stress render uses the final canvas, longest real labels and real icon footprints.
4. A semantic palette namespace is locked at paper level.
5. Full composites are canvas-first: panel rectangles and gutters are specified in physical units before
   marks, then written to a layout sidecar. Code renders PDF/SVG plus PNG; manual polish is allowed only when
   retained as code/editable provenance.
6. Deterministic craft metrics may verify declared geometry, font/stroke tiers and collisions. They may not
   impose universal density, hero-area or manual-placement ratios: hierarchy and optical balance remain
   visual judgements.
7. Technical preflight, CVD/grayscale review, visual regression and human craft review produce separate verdicts.

## Explicitly rejected shortcuts

- “Nature” as one fixed blue/orange palette;
- journal-named style sheets as publication-quality guarantees;
- updating snapshot baselines automatically when tests fail;
- universal requirements for `n`, raw points, uncertainty, zero baselines or equal grids;
- inferring authoring software from appearance;
- copying a reference figure's data, artwork or distinctive composition without licence and scientific need.
