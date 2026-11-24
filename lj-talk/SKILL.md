---
name: lj-talk
description: Create, revise, and render editable .pptx scientific teaching and research slide decks.
---

# lj-talk

**Medium Scope Guard**: `lj-talk` owns **editable `.pptx` scientific teaching and research slide decks** (argument structure, speaker notes, native PowerPoint geometry). For manuscript static figures use `lj-viz`; for interactive HTML slides or web explainers use the dedicated HTML deck/web skill when installed.

For a new deck or major restructuring, keep a compact internal deck plan with audience, duration, purpose, sources, and stable slide IDs ([references/deck-plan.md](references/deck-plan.md) and [references/talk-engine.md](references/talk-engine.md)). Distinguish on-screen text, speaker notes, teaching intent, and provenance; Markdown headings are not automatically slides.

When given an approved teaching package or course reference deck, execute its learning sequence and inherit its verified layout/typography rather than inventing a new theme ([references/teaching-handoff.md](references/teaching-handoff.md) and [references/teaching-visuals.md](references/teaching-visuals.md); see [references/kami-provenance.md](references/kami-provenance.md) for optional clean minimal defaults). Preserve scientific claims, original evidence bytes, and explicit attribution for schematic vs empirical visuals.

Deliver editable `.pptx` via `scripts/deck.py` / `scripts/render_deck.py`, validate outlines with `scripts/validate_outline.py`, and run visual acceptance checks per [references/deck-acceptance.md](references/deck-acceptance.md). If rendering tools are unavailable, declare the output visually unverified rather than claiming PASS.

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Explicit output paths and read-only/no-save instructions take precedence.
