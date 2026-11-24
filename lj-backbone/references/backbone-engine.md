# Backbone engine

The acceptance test is Juan's, not the note's: after reading, can he rebuild the key relations without looking, update a prediction when one condition changes, tell which changes should not affect a conclusion, and say which conclusions cannot yet be reached? Completeness of the diagrams and coverage of phenomena are secondary. A backbone that makes a field look tidier or more derivable than it is fails this test even if every section is filled.

## Field character

Declare the field's character at the top: formal, empirical, applied/normative, or mixed (name the parts). Several rules below branch on it. Do not import checks from one character into another: a theorem proved from explicit axioms is not refuted by observations; what can fail is the proof, the conditions, or the modelling step that applies it to the world.

## Node types

Give every node a stable ID and exactly one type. A type states what kind of knowledge a node is, not how central it is: an empirical regularity or a norm can sit at the core of a field whose theory is not unified. Do not call something an axiom or a theorem merely because the question used those words.

| ID | Type | What it is | Formal field | Empirical or applied field |
|---|---|---|---|---|
| `A` | Foundation | A starting commitment the field does not try to prove | Axiom, postulate | Framing assumption, measurement convention, value commitment |
| `D` | Core concept | The vocabulary every other node uses; fixed by definition | Definition | Operational definition with its unit and scale |
| `P` | Principle | A reusable explanatory principle that many results draw on | Core lemma or construction | Mechanism, conservation law, trade-off, selection or constraint logic |
| `T` | Core result | A result reached from other nodes through relations in the relation list | Theorem | Derived law, model prediction, or hypothesis the theory generates |
| `E` | Empirical regularity | A stable pattern the field relies on but cannot yet derive | Rare | Scaling law, measurement regularity, pattern with a contested mechanism |
| `H` | Heuristic or norm | A rule of practice, method, or value goal | Proof technique | Method heuristic, management rule, conservation goal |
| `O` | Phenomenon | An observed case used for the structural self-check | Worked example | Field or experimental observation |

An `E` node may be used as an explicitly labeled input to derive other results: using a regularity to predict a new case and explaining the regularity from deeper principles are different achievements; record which one a relation achieves, and never present a used `E` as explained. An `H` node may be a goal that other results serve.

For each `A`, record one of: `约定` (a convention, can be replaced), `经验上足够稳` (empirically well supported), `规范` (a value commitment), or `方法预设` (presupposed by the method itself). Also record what fails if it is dropped.

### Principles need not be independent

Choose principles for explanatory reach and reuse, not to reach a fixed count of independent pillars. Principles may depend on one another; record each dependency in the relation list. Claim logical independence only when there is a formal basis for it, such as independent axioms or a model in which one principle varies while the other is fixed by construction. A principle that applies in different situations is not thereby independent. For every principle kept separate despite a dependency, say why it earns its own node: it organizes a distinct family of results, it has its own formal statement, or learners reliably fail to see its consequences from the parent principle.

## Labels on every claim

Three labels describe the claim; keep them apart, since one does not imply another.

| Dimension | Values |
|---|---|
| 主张 (who holds it) | `共识`; `学派：<name>`; `多方争议：<sides>` |
| 证据 (how it fares) | `支持`, `混合`, `未通过`, `未检验`, or `非经验` for definitions, conventions, and formal results |
| 核验 (this session) | `外核` with the source actually read this session; `本篇展开检查` when the derivation or counterexample is written out in the note for the reader to check; or `未核` |

`本篇展开检查` is not an external check: a derivation written by the model can still be wrong. Use `外核` only when a source was actually read, and say what it covered.

When a label has the same value for every node, as 主张 `共识` and 证据 `非经验` usually do in a formal field, declare it once at the top of the expansion and label only the exceptions.

`未检验` means the claim has not been tested, as far as the field knows; do not assign it merely because a search found nothing. When the status is uncertain, write `证据状态未核`.

A fourth label describes each relation's derivation; see the relation list.

## Knowledge basis and targeted checks

Build the backbone from model knowledge by default; it is not a literature review. When search tools are available, check these kinds of claim, and mark them `未核` when they cannot be checked:

- Load-bearing claims whose error would change many downstream relations.
- Claims with strong quantifiers or modals: 只、必然、全部、不可能、唯一.
- Studies used to set a result's evidence status to `支持`, `混合`, or `未通过`.
- Standard derivations that a `推出` relation relies on but does not write out.

Also search when Juan asks for citable references. Name sources as author and year; never write a DOI, page, or quotation that was not checked in this session.

Watch for a claim that is familiar rather than reliable: a strong wording repeated from popular accounts often merges two different statements (for example, "selection acts only on the past" merges "selection occurs through reproductive differences in each generation's environment" with "existing mechanisms reflect past selection, so they need not fit the present").

## Relation list: one source of truth

Write the relations once, as a list, before drawing anything. Each relation is one complete route and records:

- ID (`R1`, `R2`, ...), all source nodes it jointly requires, the target node, and the relation type;
- the extra conditions it needs;
- its derivation basis (below), for `推出` and `近似推出`;
- failure examples: for each listed condition, what goes wrong when it is removed (below).

An alternative route to the same target is a separate relation with its own ID; never merge alternatives into one relation. The Mermaid graph, the optional matrix, and the derivation text are all built from this list. When one of them needs a change, change the list and rebuild the others; never edit them separately.

### Relation types

| Type | Meaning |
|---|---|
| `推出` | The sources plus the listed conditions suffice for the target |
| `近似推出` | As `推出`, under a named idealization or limit |
| `生成假说` | The theory motivates the target as a testable hypothesis; the sources do not suffice for it |
| `经验支持` / `经验反对` | Observations bear on the target; attach the evidence status |
| `定义` | The target is defined in terms of the source |
| `约束` | The source limits what the target can be |
| `张力` | The two nodes pull in opposite directions; the resolution depends on conditions |
| `替代解释` | Another theory accounts for the same target by a different route |
| `类比` | Structural similarity only; nothing transfers without separate checking |

`A ⇒ B` does not give `非A ⇒ 非B` or `B ⇒ A`. Correlation, reading order, and historical order are not `推出`. Satisfying a concept's definition does not by itself establish a prediction about its members.

### Derivation basis for 推出

A relation stays `推出` or `近似推出` only if its derivation can be checked. Record one of:

- `写出`: the derivation is written out in the note, step by step, with each step's conditions.
- `标准推导`: a named standard result or derivation (for example, "by Chebyshev's inequality") with its conditions of application, plus `外核` or `未核`.
- `推导待核`: the relation is believed to hold, but no checkable derivation is given or verified. It stays in the list with this label; it is neither confirmed nor downgraded to `生成假说`.

Downgrade to `生成假说` only when the target is an empirical hypothesis the sources motivate but cannot deliver. An unverified formal theorem is `推导待核`, not a hypothesis.

### Failure examples and counterexample search

For every `推出` and `近似推出`, record in the relation list a concrete failure example for each listed condition: what goes wrong when that condition is removed (overlapping groups double-count; a copied variable is not binomial). A condition with no known failure example is either unnecessary or not yet understood; say which. Never fill the column with "none found".

Separately, try to construct a situation where all the sources and listed conditions hold but the target fails. If one exists, add the missing condition or change the relation type. A search that finds no counterexample is a way to find errors, not a proof of validity; it never replaces the derivation basis. Typical gaps:

- A principle that says when a behaviour is favoured does not by itself fix how much of it occurs; that needs a model with the other quantities held fixed.
- A trade-off does not fix the number or form of the strategies it produces.
- A difference in investment does not by itself produce active harm; harm needs its own mechanism and evidence.
- A multi-step chain is only as strong as its weakest link; label the chain by that link.

### When a result fails

What can fail depends on the field's character:

- **Empirical:** the principle, a bridging assumption, an auxiliary assumption, the measurement, or the study design.
- **Formal:** the proof, an unstated condition, or the modelling step that applied the result to a real case.
- **Normative:** a factual premise, or the value weighting the recommendation assumed.

List the candidates, say what would discriminate among them, and name a single locus only when that evidence exists. A route losing support does not mean the phenomenon is absent, or that no other route reaches it.

## Build order

Work through these internally, but put the results in the note.

1. **Scope.** Name the scope, the sub-fields left out, the field's character, and the learning purpose the scope serves (for example, "undergraduate core plus the interface to statistical prediction", or "the measure-theoretic route to the limit theorems"). The same field name admits scopes that give materially different backbones; when the request does not settle which purpose Juan wants and the choice would change the core results, ask before building. If Juan has prior notes on the field, list what they claim and what this pass will check.
2. **Phenomenon list.** List 10–20 representative phenomena (`O` nodes), or for a formal field, representative problems the theory solves. This list serves the structural self-check in step 8.
3. **Foundations.** Ask what the field never tries to prove, and what its methods presuppose. Keep only commitments whose removal changes which results hold.
4. **Core concepts.** Pick the 5–10 concepts every derivation uses. For each, give a plain definition, the nearest concept it is confused with and the difference, and a recognition cue: what in a concrete case shows the concept applies, and what shows it does not.
5. **Principles, regularities, and goals.** Descend layer by layer: find what lies directly beneath the phenomena, then ask what lies beneath that. Keep as few principles as the results need, record their dependencies, and give each a recognition cue. Keep the field's central `E` and `H` nodes at the core when the field is organized around them.
6. **Relation list.** Write the relations for 5–12 core results, with derivation bases, failure examples for removed conditions, a counterexample search, and the three claim labels.
7. **Targeted checks.** Check the claims listed under targeted checks.
8. **Structural self-check.** Using `A`/`D`/`P`, plus `E`/`H` nodes as labeled inputs, regenerate the phenomenon list. Record each item as derived, derived with an extra condition (name it), derived from a labeled regularity, hypothesis generated, hypothesis generated but failed, or not derivable. This checks the note's structure, not Juan's learning.
9. **Reach and variation.** Derive two or three results not on the list and check whether they hold. Then run the variation test:
   - Change a condition expected to affect the conclusion, and explain why the prediction changes.
   - Name changes that should not affect the conclusion, and say why.
   - When a prediction does not change, it may mean the condition is irrelevant, the theory is invariant under that change, or current observations cannot discriminate. Do not conclude that the principle is stated too loosely unless the principle claims to cover that condition and the prediction should have changed.
10. **Boundaries and disputes.** For each principle and major result, state where it fails or narrows (scale, unit, regime, idealization, domain of the formal system), classified as hard (world or logic), soft (rule or measurement), or self-imposed (inherited interpretation). Attach live disputes to their node or relation, with the sides and what would decide them.
11. **Learning order.** Build it only from prerequisite relations: `定义`, `推出`, `近似推出`, and the sources of each `生成假说`. `经验支持`, `经验反对`, `约束`, `张力`, `替代解释`, and `类比` do not set learning order, and they may legitimately form cycles with the rest of the graph. When joint definitions or a genuine cycle remain among prerequisites, learn those nodes as one group. Group the order into 3–5 stages; for each, say what a learner can derive once it is done.
12. **Probes.** Write them last, following the rules below.

## Probes: test independent use

The probes are the learning test. Write three, one of each kind below, in situations the note has not discussed and without node IDs in the question. What each kind tests depends on the field:

| Kind | Formal field | Empirical field | Normative or applied field |
|---|---|---|---|
| 重建 (rebuild) | Choose the premises, carry out the derivation, and say what changes when one condition changes | Same | Same, from goals and facts to a recommendation |
| 区分 (discriminate) | Which condition, theorem, or proof method applies here | Which new observation would make two competing explanations diverge | How different goals or value weights change the choice |
| 止步 (stop) | A condition is missing, the result cannot be derived, or the question lies outside the system | The evidence is insufficient, the effect is not identifiable, or the extrapolation goes out of bounds | The facts alone cannot settle what should be done |

Rules for all probes:

- Each answer names what would lower confidence in it: empirical counter-evidence, an error in the derivation, an unmet condition, or a changed value premise, whichever fits.
- Accept every valid route to an answer. Give the route the note uses as one route, not the only one.
- Do not show the probe kind with the question; labelling a probe as a stop probe gives away the strategy. Record the kind inside the answer.
- Do not reward a fluent story: a probe whose best answer is a plausible narrative with no discriminating content is a bad probe.
- A probe must be solvable from knowledge the note has already given at that point, or explicitly allow the answer that the information is insufficient.
- Put each answer in a collapsed `<details>` block, with its dependency path.

## Reading path and layout

Start with a short entry, then the expansion. Keep the entry light: it shows a few key nodes, not the full inventory.

1. **这个领域解决什么问题**, in two or three sentences.
2. **核心思想**: 3–5 principles, regularities, or goals in plain language, mechanism before name.
3. **关键节点图** (ASCII): only the nodes the entry uses.
4. **一条完整推导**: one key chain walked through with one concrete case, every condition visible.
5. **改一个条件**: the same case with one condition changed and how the conclusion changes, plus one change that leaves it unchanged and why.
6. **这套结构不回答的**: one boundary of the backbone. For an empirical field this may be a phenomenon it cannot yet derive; for a formal field, a question outside the system or a modelling step the theorems do not settle; for a normative field, a choice the facts do not determine. Do not manufacture an explanatory gap for a mature formal theory.

Then:

7. **入门探针**: only probes solvable from the entry. Probes that need the expansion go after the section they depend on.
8. **展开** (expansion): the full ASCII layer overview, the relation list, the Mermaid graph, each node with its labels, the structural self-check, reach and variation, boundaries and disputes, learning order, remaining probes, and what to read next.
9. **查阅** (optional): the dependency matrix.

### Diagrams

- **ASCII layer overview** (full version, in the expansion): all nodes grouped by type. It is a legend of kinds of knowledge, not a ranking and not a claim that the field is a tower.
- **Mermaid graph**, built from the relation list, with typed edges. When a relation has several jointly required sources, draw them into one junction node and one arrow from the junction to the target, so `A + B ⇒ T` never looks like two independent arrows. Draw each alternative route separately. Style `未通过`, `混合`, and `推导待核` distinctly and add a legend line. A syntactically valid graph has not been visually checked; do not claim that it has.
- **Dependency matrix**, optional. It indexes the routes this note uses; it does not measure how fragile the field is. Mark direct use `X` and use through another node `o`; when a target has alternative routes, give each route its own row. A column count ranks learning priority, not what an attack would bring down.

Keep ASCII diagrams inside fenced code blocks. CJK characters and symbols such as `●` or `│` are double-width in many terminals, so build aligned columns from plain ASCII (`X`, `o`, `.`, `|`, `-`) and put Chinese labels only at the end of a row or on their own line.

### Writing rules

- Explain the mechanism before giving it a name.
- One case carries one key chain in depth; connect other branches with short contrast cases rather than stretching one story across the whole graph.
- Every analogy states where it breaks.
- Gaps stay visible where they occur; do not fill a missing condition, threshold, or step to make the structure look complete.

## Self-check before saving

- The Mermaid graph, matrix, and derivation text agree with the relation list and with each other; joint sources go through a junction and alternative routes are separate relations.
- Every `推出` has a derivation basis of `写出` or `标准推导`, or is labeled `推导待核`; no relation is confirmed only because no counterexample was found; every listed condition has a failure example or an explanation of why it has none.
- No principle is claimed independent without a formal basis; every dependency among principles is recorded.
- Every claim carries 主张, 证据, and 核验 labels, declared once where uniform; `外核` appears only for sources actually read this session; no `E` or `H` node is presented as explained, and no node's type is treated as a ranking.
- Targeted claims were checked or marked `未核`; no `未检验` rests only on an empty search.
- No failure is pinned to a single locus without discriminating evidence.
- The learning order uses only prerequisite relations, and groups any remaining cycle.
- The three probes fit the field's character, hide their kind, accept alternative valid routes, and each is placed after the knowledge it needs.
- The entry shows only key nodes and names a boundary suited to the field's character.
- No unchecked DOI, page number, or quotation appears in the note.
