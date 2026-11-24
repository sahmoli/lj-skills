# Scientific conceptual figures

Use this reference for `figure_family: conceptual` and `figure_family: mixed`. It covers scientific
infographics, mechanism diagrams, causal-system figures, process diagrams and graphical abstracts. It does
not cover generic list, timeline, social-media or poster infographics; route those to `ljg-infograph`.

## 1. Communication Contract

Before a wireframe, write:

1. **Deepest thesis** — the narrowest mechanism-level sentence the figure is authorised to support.
2. **Reader task** — trace a mechanism, compare alternatives, locate an intervention, understand a feedback,
   or connect a data panel to its causal role.
3. **Scope boundary** — what remains unmeasured, hypothesised, unresolved or out of frame.
4. **Baseline and insertion point** — the system before perturbation, and where intervention, observation or
   disturbance enters.
5. **Outcome attachment** — each consequence must attach to the node or edge producing it.

Do not use a diagram to settle an unsettled scientific claim. Hand scientific disputes back to `lj-read`,
`lj-review` or the user; show a hypothesis as a hypothesis.

## 2. Ground the model before styling

Build `semantic_model.source_anchors` from user-provided material, traceable literature or manuscript text.
Each anchor needs a source, a locator and an explicit status:

- `direct` — the source directly supports the depicted relation.
- `synthesized` — the figure combines compatible, explicitly identified sources.
- `hypothesis` — a proposed relation, visibly and textually qualified.
- `design-only` — grouping or graphical context; never a causal edge.

Every scientific node and edge cites anchors, unless it is explicitly `hypothesis`. Never infer direction,
effect size, timing, taxa, molecular detail or a feedback loop from visual convention. The manifest is the
audit record; evidence status need not be printed in the final figure unless readers need it to interpret the
claim.

## 3. Build a semantic graph, not a prose collage

Define nodes with a stable ID, locked label, role and evidence. Use roles only when they clarify the model:
`baseline`, `insertion-point`, `driver`, `trigger`, `mechanism`, `mediator`, `state`, `outcome`, `feedback`,
`failure`, `safeguard`, `context` and `asset`.

Define each edge with direction, relation, sign and evidence. Allowed relations are `activates`, `inhibits`,
`transforms`, `transports`, `amplifies`, `feeds-back`, `restores`, `associates` and `other`. Use `other` only
when a short visible relation label removes ambiguity.

The integrated causal recipe is the default only when the claim is a dynamic causal system:

```text
baseline → insertion/driver → mechanism → consequence
                         ↑                    │
                         └── real feedback ───┘
failure pathway ↔ safeguard/restoration path
```

Do not decorate a loop around a diagram. A feedback loop exists only if the manifest names a closed directed
cycle. A safeguard must restore, block or reroute a named failure mechanism; it is not an optimistic icon.

## 4. Lock the topology before composition

Choose one dominant **logical topology**, not one fixed workflow:

| Topology | Use when |
| --- | --- |
| `linear` | one ordered mechanism or pipeline is the argument |
| `branched` | one driver produces several distinct routes or outcomes |
| `convergent` | several drivers meet at a shared mechanism |
| `feedback` | a real closed loop changes later system state |
| `parallel` | alternatives must be compared without implied causation |
| `nested` | a subsystem sits inside a larger system or scale |
| `hybrid` | the thesis truly needs a controlled combination |

State a `dominant_path` of connected node IDs. A reader must recover it in a monochrome thumbnail. Add
secondary routes only when they change interpretation; mere background belongs in the caption or a quieter
context layer.

## 5. Semantic tests before rendering

Use manifest constraints as semantic unit tests:

- `must_show` contains the nodes and edges without which the thesis changes.
- `must_not_show` lists prohibited entities, arrows, labels or visual claims.
- `locked_labels` is copied verbatim into the final vector text.
- `invariants` are nodes/edges a revision is not allowed to disturb.
- `redundant_encoding` names non-colour cues, such as arrow direction, line style, shape or direct labels.

Test these before and after each render. A plausible-looking image that violates the semantic graph fails.

## 6. Reference Board and monochrome wireframe

Choose reference figures by **structural resemblance** when a new visual language or layout needs grounding:
reader task, topology, evidence architecture, and density. Record any move to borrow and avoid. Reference
style never authorises copying data, artwork, or ungrounded scientific content.

Draw a black-and-white wireframe first. Reserve label bands, the feedback route, the intervention point and
the bottom-line conclusion before choosing colours or imagery. Do not let a title, hero illustration or
large empty box outrank the causal path.

Map colours to declared roles, not intrinsic good/bad meanings. Use an accessible palette and a redundant cue
for every contrast readers must decode. Red/green is not a semantic standard.

## 7. Dual representation plan

### Exploration lane

Use a render brief for composition experiments, style exploration and bounded non-data illustration. It must
include thesis, topology, locked labels, must-show, must-not-show, evidence status and negative constraints.
Generated arrows, labels and causal relations are untrusted until checked against the semantic model.

Never ask an image model to recreate a numerical plot, statistical interval, map geometry or factual trend.
If it produces text or causal structure, rebuild those elements in SVG rather than accepting pixels.

### Formal lane

The v1 canonical editable artifact is SVG. Nodes, arrows, labels, legend and semantic emphasis remain
separate vector elements; final labels are `<text>`. Put code-generated quantitative panels into the same
assembly only as faithful data artifacts, not model-generated approximations. Export PDF and a high-resolution
PNG preview from the editable source.

User-supplied scientific images are fixed inputs. If a generative asset appears in a final figure, record its
path, model, prompt and role in provenance, and check the target journal's live policy through `lj-journal`.

## 8. Layered critic and typed patches

Audit in this order:

1. **Semantic faithfulness hard gate** — no invented/omitted entities or reversed links; all locked labels and
   forbidden elements respected.
2. **Scientific coherence** — baseline, insertion, trigger, mechanism, consequence, feedback, failure and
   safeguard have the claimed roles; distinguish correlation from causal language.
3. **Visual reasoning** — topology, hierarchy, reading path, density, semantic palette and outcome attachment
   are clear at final size.
4. **Technical preflight** — editable labels, SVG structure, font size, clipping, final size and exports pass.

Do not accumulate vague critique. Each repair is one typed patch:
`add_node`, `remove_node`, `relabel_node`, `redirect_edge`, `change_relation`, `move_group`, `change_style`,
or `replace_asset`. Record target, reason and preserved invariants; rerun the relevant semantic tests after
the patch. If the same issue persists twice, revise the topology or representation instead of endlessly
nudging coordinates.

## 9. Mixed figures

For `mixed`, keep the quantitative Figure Contract and the semantic model both complete. `mixed_bindings`
must name the semantic node/edge, quantitative panel label and its evidence role. A chart must clarify a
specific causal location, not become a detached evidence appendix. The semantic diagram must never imply a
quantitative magnitude that the data panel does not support.

```yaml
figure_family: mixed
mixed_bindings:
  - semantic_id: outcome
    panel_label: b
    evidence_role: "quantifies the outcome attached to this mechanism"
```

## 10. Output additions

Alongside the ordinary `lj-viz` output, return:

```text
【Figure family】conceptual | mixed
【Communication Contract】deepest thesis · reader task · scope · baseline · insertion point
【Semantic model】source anchors/status · nodes · directed edges · dominant topology · feedback status
【Semantic tests】must-show · must-not-show · locked labels · invariants · redundant encoding
【Representation plan】exploration/formal lane · editable artifact · AI asset status
【Critic】semantic hard gate · scientific coherence · visual reasoning · technical preflight
【Patch record】typed patch · target · reason · preserved invariants
```
