---
name: lj-viz
description: Design, build, and preflight-audit journal static and multi-panel scientific publication figures.
---

# lj-viz

Preserve the figure's scientific claim, data provenance, estimand, repeating unit, scales, units, transformations, and uncertainty. A visual repair never authorizes altering study design or statistical results. Use the project's output directory, otherwise `outputs/figures/`.

**Medium & Palette Scope Guard**: `lj-viz` governs **journal and manuscript static/multi-panel publication figures (`medium: paper`, white `#FFFFFF` page ground, print `pt`/`mm` typography, vector PDF/SVG + high-DPI PNG)**. Do not apply web-portal card backgrounds or slide-deck chrome to manuscript figures; if the user requests interactive HTML pages, posters, or live slide decks, route surface styling to the appropriate web or presentation skill while keeping `lj-viz`'s statistical encoding and uncertainty discipline.

Route reading strictly by task (do not load unrelated references):
- Encoding choice or redesign → [references/viz-engine.md](references/viz-engine.md) and [references/ecology-figure-architectures.md](references/ecology-figure-architectures.md)
- Typography, multi-panel hierarchy, or colour accessibility → [references/nature-visual-system.md](references/nature-visual-system.md)
- Production build, geometry audit, and preflight QC → [references/build-and-qc.md](references/build-and-qc.md) and [references/engineering-practices.md](references/engineering-practices.md)
- Conceptual / mechanism diagrams → [references/conceptual-figures.md](references/conceptual-figures.md)
- Reference exemplars & species silhouettes → [references/exemplars.md](references/exemplars.md) ([query_reference_board.py](scripts/query_reference_board.py)) and [references/species-silhouettes.md](references/species-silhouettes.md)

Do not invent data or hand-draw quantitative curves. Inspect the actual rendered output at its target print dimensions ([preflight_figure.py](scripts/preflight_figure.py), [audit_layout.py](scripts/audit_layout.py), [craft_metrics.py](scripts/craft_metrics.py), [audit_palette.py](scripts/audit_palette.py); auxiliary CVD/comparison helpers indexed in [references/build-and-qc.md](references/build-and-qc.md)); source-code inspection is never a visual check. Conceptual or mixed figures require explicit researcher sign-off on scientific relationships before being marked final ([validate_manifest.py](scripts/validate_manifest.py) / [validate_quick_manifest.py](scripts/validate_quick_manifest.py)).

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Explicit output paths and read-only/no-save instructions take precedence.
