# Offline one-screen annotation interface contract

Use this reference when designing a packet, changing the bundled generator, or auditing a generated page.

## Contents

1. Public packet contract
2. Human-effort objective
3. Fixed spatial grammar
4. Visual system
5. Highlight contract
6. State and confirmation
7. Export contract
8. Offline and privacy boundary
9. QA checklist

## 1. Public packet contract

Use `lj.annotate.packet.2` for every new task. Keep packet v1 only to read or reproduce frozen historical
artifacts. A project's CSV, Parquet, database, or source JSON is **not** the public interface contract. Write
a thin project adapter that emits packet v2; never make the shared renderer understand project columns.

The complete synthetic reference is `synthetic-packet-v2.json`. Its cross-research shape is:

```json
{
  "schema_version": "lj.annotate.packet.2",
  "return_schema_version": "lj.annotate.return.2",
  "packet_id": "stable-project-task-id",
  "task_version": "frozen-task-version",
  "title": "Human-facing title",
  "mode": "assisted_review",
  "provenance": {
    "task_spec_sha256": "...",
    "codebook_sha256": "...",
    "source_manifest_sha256": "...",
    "ai": {
      "system": "provider/system",
      "model": "model snapshot",
      "prompt_sha256": "...",
      "draft_manifest_sha256": "..."
    }
  },
  "layout": {
    "profile": "fixed_review",
    "desktop_decision_overflow": "fail",
    "evidence_min_font_px": 12,
    "evidence_max_font_px": 34,
    "max_fields": 12,
    "secondary_mode": "auto"
  },
  "sections": [
    {"key": "scope", "role": "upstream_scope", "label": "1 · Scope", "tone": "target", "fields": ["relevance"]},
    {"key": "classes", "role": "peer_classification", "label": "2 · Peer classifications", "tone": "classification", "fields": ["content"]},
    {"key": "quality", "role": "input_quality", "label": "3 · Input quality", "tone": "quality", "fields": ["adequate"]}
  ],
  "fields": ["ordered field definitions"],
  "structural_rules": ["upstream condition -> assigned and locked downstream value"],
  "highlighting": {
    "enabled": true,
    "groups": [
      {"key": "focal", "label": "Current object", "tone": "target", "static_terms": [], "include_focal_aliases": true, "targets": "both"}
    ]
  },
  "records": [
    {
      "record_key": "stable-key",
      "primary_text": "frozen readable evidence",
      "secondary_text": "optional preserved source",
      "focal_entity": {"key": "entity-key", "label": "Human name", "subtitle": "Optional subtitle", "aliases": ["literal alias"]},
      "highlight_terms": {"focal": ["record-specific literal"]},
      "active_fields": ["optional subset for targeted verification"],
      "ai_draft": {"every field": "one legal value"},
      "initial_notes": {},
      "bindings": {"evidence_sha256": "..."}
    }
  ],
  "return_filename": "task-review.json"
}
```

The schema expresses semantics, not one paper's vocabulary:

- `sections` makes scientific hierarchy explicit. Every field belongs to exactly one ordered section.
  Roles are `upstream_scope`, `peer_classification`, `downstream_outcome`, and `input_quality`.
- `focal_entity` is optional and generic. It may be a species, policy, paper, intervention, person, place,
  image region, claim, or any other current object.
- `highlighting.groups` declares no more than three concepts. Static terms live in the group; dynamic
  terms live under each record's `highlight_terms`. `include_focal_aliases` is a generic bridge, not a
  species-specific rule.
- `active_fields` supports a targeted adjudication or verification packet while keeping inactive rows in
  place. Completion and change calculations use only active fields; export preserves the complete draft.
- `bindings` and top-level provenance bind what was seen and which task/codebook/source/AI draft produced it.
- `layout` declares capacity. `desktop_decision_overflow: fail` is the default. If a frozen task genuinely
  requires more fields, explicitly select `internal_scroll` or split the task; never silently shrink or clip.

Field and option order is the screen and return order and must remain frozen. Shortcut keys are globally
unique lowercase letters or digits. `requires_note` preserves uncertainty. `structural_only` values are
legal only under a matching rule. Every structural assignment must also lock the field; dependencies must
be acyclic and flow from earlier scientific sections to the same or later section.

Allowed modes:

- `assisted_review`: every record requires a complete ordered `ai_draft` and hash-bound AI provenance.
- `blind_coding`: answers begin blank; AI/prior/design/outcome leakage is forbidden. Highlighting requires
  hash-bound protocol authorization affirming task-neutrality and no design/outcome disclosure.

`primary_text` is the easiest evidence to read. `secondary_text` is the optional preserved source. Do not
show sampling strata, inclusion probability, weights, outcomes, old labels, or AI rationale unless the
measurement protocol explicitly requires them.

## 2. Human-effort objective

Optimize the median repeated record, not the setup screen:

- Correct AI draft: one keypress (`Enter`).
- Incorrect single field: one click/shortcut plus `Enter`.
- Previous record: one keypress (`Left`).
- No modal, accordion, confirmation dialog, or separate save action in the main loop.
- No need to remember option meanings: each button shows label and shortcut.
- No need to find current state: selected option, AI provenance, progress, and save status are visible.

Human effort is not merely click count. Also minimize eye travel, pointer travel, working-memory load,
context switching, and recovery cost after interruption.

## 3. Fixed spatial grammar

Desktop target: 1440×900, 100% zoom.

```text
+-------------------------------------------------------------------+
| mode/title                     reviewed/total     progress track   |
+----------------------------------+--------------------------------+
|                                  | Field 1  [A] [B] [C]           |
| primary visible evidence         | Field 2  [A] [B] [C]           |
|                                  | Field 3  [A] [B] [C]           |
| -------------------------------- |                                |
| preserved source / legend        | stable notes / AI markers       |
+----------------------------------+--------------------------------+
| [Previous]  key help       [Partial] [Full] [Confirm / Next]       |
+-------------------------------------------------------------------+
```

Use `100dvh`, `overflow:hidden` on the document, and a three-row grid (`header`, `minmax(0,1fr)`, `footer`).
The work area is a two-column grid. Evidence and decisions may scroll internally, but the footer and
decision columns must not shift. Never conditionally remove a field row; disable it in place so all later
buttons keep their coordinates.

The fixed layout must also express the measurement hierarchy:

- focal entity + evidence first;
- upstream target/scope judgment as its own group;
- peer classification fields in one bounded, explicitly labeled group;
- downstream outcome/content-depth judgments in another group;
- input adequacy/provenance checks last and visually quieter.

Do not flatten these levels into one undifferentiated stack. If a record has a focal entity, show its
human-readable name above the evidence, not below it. Record-specific aliases may be used for dynamic
literal highlighting when they are frozen in the packet and do not reveal an outcome.

For long evidence, use responsive type fitting down to a documented minimum. Below the minimum, preserve
readability and allow only the evidence pane to scroll. Never shrink scientific text into illegibility to
win a no-scroll screenshot.

At narrow widths, stack evidence over decisions and allow controlled page scrolling. Keep confirmation
reachable and do not clip required controls.

## 4. Visual system

Choose a restrained task-specific palette, then express it as tokens. Minimum roles:

- canvas, paper, ink, muted, line;
- action/confirmed;
- yes/present;
- no/absent;
- unclear/attention;
- structural/inapplicable;
- up to three evidence-highlight groups.

The same semantic state always gets the same color, label order, and shortcut. Use borders, pressed state,
text, and `aria-pressed` as well as color. Keep strong color for selected/attention/primary actions; leave
the rest quiet. Avoid arbitrary per-field palettes.

In assisted review, **selection is the dominant state**: all unselected options stay neutral, regardless
of whether their value is YES, NO, or UNCLEAR. Only the current AI/human selection receives the group's
strong fill, and it must also show a checkmark plus an explicit AI/current-state marker. A colored YES
button must never look selected when the actual draft is NO. When a focal entity is present, its title,
literal evidence highlights, and the selected target/scope judgment share one semantic token.

Typography should make evidence fastest to read: a readable serif may serve substantive text; a compact
sans serves decisions; a mono or tabular-number style serves keys/progress. Use system fonts in offline
pages unless fonts are embedded as data and privacy/size permit it.

## 5. Highlight contract

Use literal, predeclared terms by default. Match case-insensitively and prefer longest terms first. Wrap
text nodes after assigning evidence through `textContent`; do not apply untrusted strings through
`innerHTML`. A legend maps each highlight color to a concept.

Highlight only what helps the human locate evidence. Do not:

- highlight a term because the AI used it;
- highlight predicted answers, confidence rationales, sampling screens, or outcome-bearing metadata;
- imply that a highlighted term automatically yields YES;
- use more highlight colors than a person can remember;
- enable highlights in blind mode without explicit protocol authorization.

## 6. State and confirmation

Persist under a namespace containing packet ID, schema version, and the canonical packet SHA-256. A
packet change therefore starts a new state namespace even if a careless adapter reused the ID. State per
record includes:

```json
{
  "answers": {},
  "notes": {},
  "human_reviewed": false,
  "reviewed_at": ""
}
```

Assisted drafts initialize `answers` but not `human_reviewed`. Changing a choice or note sets
`human_reviewed=false`. Enter/Right confirms only when every required field has a legal value and every
note-required state has a nonblank note. It stamps an ISO timestamp and jumps to the next unreviewed item.
When a one-line note input has focus, ordinary typing remains local to the input, while Enter still runs
the same whole-record confirmation gate; a note field must not turn Enter into a dead key.

Revisiting a confirmed record shows its saved state. Editing it makes it unconfirmed until Enter is pressed
again. Reload must restore current index, choices, notes, and confirmation state.

## 7. Export contract

Packet v2 defaults to return v2. A project with a frozen return-v1 intake may explicitly set
`return_schema_version: lj.annotate.return.1`; additive packet/provenance metadata remains available, while
the legacy record contract stays intact. New tasks should use:

```json
{
  "schema_version": "lj.annotate.return.2",
  "packet_id": "...",
  "task_version": "...",
  "packet_sha256": "...",
  "renderer_version": "...",
  "provenance": {},
  "mode": "assisted_review",
  "export_kind": "partial",
  "exported_at": "ISO-8601",
  "records": []
}
```

Each returned record contains `record_key`, `answers`, `notes`, `human_reviewed`, `reviewed_at`, and frozen
`bindings`. Assisted returns additionally contain `ai_draft`, `changed_from_ai`, ordered `changed_fields`,
and `ai_initial_notes`. Never use an AI draft as proof of human completion. Intake must recompute change
status and reject packet/provenance/binding drift.

Partial export includes confirmed records only. Full export includes every packet record and is blocked
unless all are confirmed. Never coerce blank to NO. Preserve uncertainty and structural values exactly.

## 8. Offline and privacy boundary

Use a CSP at least as strict as:

```text
default-src 'none'; connect-src 'none'; img-src 'none'; media-src 'none';
object-src 'none'; frame-src 'none'; font-src 'none'; style-src 'unsafe-inline';
script-src 'unsafe-inline'; form-action 'none'; base-uri 'none'
```

Embed data, CSS, and JavaScript. No analytics, fetch/XHR/WebSocket, upload, form submission, external font,
remote image, or live link preview. If the source contains URLs, display them only as inert text.

Real restricted text stays in an authorized restricted directory. The reusable skill contains only
generic code and synthetic self-tests.

## 9. QA checklist

Static:

- packet keys unique; field/option values valid; assisted drafts complete;
- blind packet contains no prefill/prior answers and no unauthorized highlights;
- structural rules reference real fields and legal values;
- JSON is embedded with `<` escaped;
- CSP and zero-network design present;
- text rendered safely; full/partial export semantics present.

Browser at 1440×900:

- `scrollHeight <= innerHeight` and `scrollWidth <= innerWidth`;
- all footer controls visible; every field row visible when overflow policy is `fail`;
- record 1 and the longest record give identical field, option-button, and footer bounding boxes;
- every unselected enabled option has one neutral computed background; selected options have a checkmark,
  `aria-pressed=true`, and a visibly distinct fill;
- focal title, record-specific highlights, scientific section boundaries, and highlight legend render;
- renderer reports no undeclared capacity overflow through `window.__ljAnnotateQA.snapshot()`;
- Enter confirms exactly one record and advances;
- changing a confirmed answer clears confirmation;
- reload restores state;
- full export blocks unfinished state;
- focus rings and keyboard navigation work;
- no console errors or network requests.

Run `scripts/browser_qa.sh` for the public synthetic packet after every renderer change. It exercises the
desktop/compact/breakpoint/mobile matrix, button geometry, input-focused Enter, structural unlock/relock,
required notes, packet-digest state isolation, and return-v2 round-trip in a real Chromium session.

Record the viewport, browser, test result, packet hash, output hash, mode, record count, and human-reviewed
count in a receipt for research use.
