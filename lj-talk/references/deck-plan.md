# Editable deck plan

`scripts/deck.py` accepts an agent-authored JSON plan. It is an internal handoff
artifact: the person asking for a deck should describe the talk in ordinary
language, and the agent writes this plan. A supplied external teaching design
package can instead provide the plan's stable IDs, sequence, protected functions,
sources, and notes links; read [teaching handoff](teaching-handoff.md) when that
package governs substantial production. It builds only supplied local assets; it
does not call image generators, services, or upload material.

Install `../requirements-deck.txt` into the Python runtime that will build or
render the deck; it includes the editable PPTX and local rendering dependencies.

```json
{
  "deck_id": "stable-project-name",
  "title": "Deck title",
  "slides": [
    {
      "id": "opening", "section": "main", "kind": "title",
      "title": "A claim that frames the talk", "body": ["Optional subtitle"],
      "notes": "Speaker-only production notes.",
      "sources": [{"citation": "Author (2026)", "locator": "Fig. 2"}],
      "images": [{"id": "hero", "path": "assets/hero.png", "fit": "crop", "role": "illustrative", "generation_prompt": "optional recorded prompt", "generation_config_hash": "optional hash"}],
      "elements": [{"id": "callout", "type": "text", "text": "Native editable text", "x": 8.0, "y": 6.0, "w": 3.0, "h": 0.4, "size": 14}]
    }
  ]
}
```

Every slide needs a stable unique `id`, a nonempty `title`, and `section`
(`main` or `appendix`). `kind` is `title`, `content`, or `section`; it controls
only a lightweight default layout. The builder's default is a warm light canvas;
it is not a course-style decision. When a brief supplies an approved course
reference, match that reference rather than treating this fallback as Kami styling.
Set `"theme":"ink"` only when a dark page is wanted. `body`, `notes`,
`sources`, `images`, and `elements` are optional. A body string is plain text;
a list becomes separate editable lines, without invented bullets. Text stays in
native PowerPoint shapes; source entries are sent to speaker notes, separate
from on-slide production intent.

The builder and its JSON schema are optional local implementation aids, not the
visual ceiling for an approved design. When their defaults cannot express a
supplied course baseline or protected teaching function, use a suitable
authorized implementation and preserve the design rather than flattening it to
the fallback layout.

For a teaching deck, add only the lightweight teaching annotations needed to
clarify a beat (for example its starting state, task, carried-forward state,
open prediction, feedback, transfer, linked notes, or time estimate). These
fields guide sequencing and review; the local builder ignores them, so keep
student-facing wording in normal slide fields and notes. A plan field documents
intent; it does not demonstrate that the rendered page performs it.

Each normal source has a `citation` and `locator`; a local evidence file can be
recorded as `path` and must exist. Each image has unique `id`, local `path`,
`fit` (`contain` preserves the whole image; `crop` fills its box), and `role`
(`evidence` or `illustrative`). A genuinely unavailable asset must say
`"missing": true`; this creates a visible placeholder instead of silently
omitting the dependency. An existing generated asset may record
`generation_prompt` and `generation_config_hash`, only when its role is
`illustrative`; the builder never regenerates it.

Use `layout.title` or `layout.body` with `{x,y,w,h,size}` for intentionally
placed text. An image can likewise supply `{x,y,w,h}`. Without positions, a
body-free image uses the wide lower canvas; multiple body-free images form a
comparison row. All positions are inches on a 13.333 × 7.5 canvas.

Run `python scripts/deck.py check --plan plan.json` first, then
`python scripts/deck.py build --plan plan.json --output talk.pptx`. The build
creates `talk.pptx.deck-state.json`, with per-slide dependency hashes and the
output hash. It records `changed_slide_ids` and a rebuild reason, even though
PowerPoint assembly writes one package. Repeating an unchanged plan *and asset
bytes* does not rewrite the deck. Main and appendix pages use independent footer
numbering (`1 / N` and `A1 / AN`). The builder refuses to replace a PPTX without
matching state, or one edited outside the builder; choose a new output filename
in those cases.

For a safe direct tweak, write a distinct output:

```text
python scripts/deck.py edit --input talk.pptx --output talk-revised.pptx --slide-id opening --shape-name opening:title --text "Revised title"
python scripts/deck.py replace-image --input talk.pptx --output talk-revised.pptx --slide-number 1 --shape-name opening:image:hero --image assets/replacement.png --fit crop
```

Direct edits retain the original slide order, notes, media, and all untouched
shapes. Text replacement retains the selected shape's first run styling while
replacing its complete text. Image replacement keeps its native bounds, crop,
and z-order by default only when the replacement has the same aspect ratio;
otherwise choose explicit `contain` or `crop` fitting.
It does not invoke generation and title editing does not touch assets. Edited
outputs are marked detached from the JSON plan, so a later build cannot call
them unchanged by mistake.
