# Rank-to-weave interface

Normalize every rank essay into this record before weaving:

```text
domain:
basic_assumption_ceiling: <what the field treats as given | unknown>
root_rank_floor: <the lowest generative skeleton | unknown>
relation_shape: orthogonal | nested | chain | feedback | tension | branching | network | cycle | other | unknown
coordinate_system: <optional operational axes derived from one root line | none | unknown>
source_anchor: <essay path and exact section>
```

Rules:

1. The ceiling is a premise the field rests under; it is not the root that generates the field.
2. The root rank is the lowest surviving generative skeleton after recursive descent.
3. A coordinate system is optional and derived. Do not weave its axes as peers of root-rank elements.
4. Relation shape controls the edge representation. Do not default to a three-layer drill or 2x2.
5. Legacy essays may lack fields. Preserve `unknown`; never backfill from title or style alone.
6. Same-level edges compare like with like. Cross-level edges must explicitly name the level transition.
