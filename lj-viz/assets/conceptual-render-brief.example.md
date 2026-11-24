# Conceptual render brief

## Thesis and topology

- **Deepest thesis:** [one mechanism-level sentence]
- **Logical topology:** [linear | branched | convergent | feedback | parallel | nested | hybrid]
- **Dominant path:** [ordered node IDs]
- **Scope boundary:** [what the figure does not claim]

## Semantic lock

- **Must show:** [node/edge IDs]
- **Must not show:** [forbidden components, relations, labels]
- **Locked labels:** [copy exact text from the manifest]
- **Evidence status:** [direct | synthesized | hypothesis] for every causal component
- **Invariants during revision:** [node/edge IDs]

## Wireframe and representation

- Begin with a monochrome wireframe. The dominant path must be readable without colour.
- Use SVG for nodes, edges, labels and legend. Keep all locked labels as editable `<text>`.
- Use colour only for declared semantic roles, with line style, arrow direction, shape or direct labels as redundant encoding.
- Treat generated imagery as a draft or bounded decorative asset only. It must not recreate numerical plots, causal arrows, labels or scientific data.

## Negative constraints

- Do not invent nodes, molecules, taxa, causal links, effect sizes, directions, labels or evidence.
- Do not add a feedback loop unless the semantic model contains a closed directed cycle.
- Do not turn outcomes into detached decorations; attach each one to its causal source.
- Do not use rounded UI cards, decorative loops, colour-only distinctions or rasterized final labels.

## Critic and patch record

1. Semantic faithfulness hard gate: verify every locked relation and forbidden component.
2. Scientific coherence: verify baseline, insertion point, trigger, mechanism, consequence, feedback, failure and safeguard as applicable.
3. Visual reasoning: inspect topology, hierarchy, reading path, density and attachment of outcomes.
4. Technical preflight: inspect editable text, SVG structure, font size, clipping and final-size readability.

Record each repair as `add_node`, `remove_node`, `relabel_node`, `redirect_edge`, `change_relation`, `move_group`, `change_style` or `replace_asset`, with target, reason and preserved invariants.
