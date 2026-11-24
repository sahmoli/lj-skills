# LJ Write Prose Engine

Load this reference for a substantial manuscript section, style calibration, or a difficult de-AI edit.
For a small local edit, the core `SKILL.md` is enough.

## Contents

1. Positive target
2. From scientific content to prose
3. Section-specific decisions
4. Exemplar calibration
5. Structural AI smells
6. Semantic-drift audit

## 1. Positive target

Aim for prose that feels written by a scientist who knows exactly what the evidence does and does not
show. The target is not "human-like" in the abstract. It is field-natural, reader-centered, and
proportionate to the scientific move.

A useful sentence does at least one job: state a question, report evidence, explain a necessary relation,
bound an inference, or move the argument. Delete sentences that only announce importance, completeness,
rigor, or transition.

Use the reader-expectation test:

- Is the grammatical subject the entity the sentence is really about?
- Is the important action carried by a verb rather than hidden in a noun stack?
- Does familiar information connect to the previous sentence before new information arrives?
- Does the sentence place its real emphasis near the end when that helps comprehension?

These are diagnostics, not a mandatory syntax. A short direct sentence can already be right.

## 2. From scientific content to prose

Before writing a paragraph, identify four things internally: reader job, claim, authorized evidence, and
inference boundary. Use only the fields the paragraph needs. Do not display or mechanically repeat them.

Draft in this order:

1. Put the paragraph's scientific move early enough that the reader knows why the details matter.
2. Add only the evidence needed to make that move credible.
3. Interpret at the level authorized by the design and analysis.
4. End when the move is complete. Add a bridge only if it names a real relation to what follows.

Use subtraction as the default revision move. When a paragraph feels thin, first ask whether it lacks
evidence or thought. More prose cannot repair either absence.

## 3. Section-specific decisions

### Abstract

Compress the actual story: problem, unresolved gap, minimal design, distinguishable findings, and bounded
contribution. Do not add field history, generic significance, citations unless the venue expects them, or
future work. Each result must be specific enough to remain meaningful without a figure.

### Introduction

Move from a real scientific tension to the study's question. Use prior work to create the problem, not to
inventory a field. State the contribution at its true level. Avoid cinematic openings, universal claims,
and inflated "for the first time" language.

### Methods

Prioritize reproducibility and order of operations. Repetition is often necessary here. Do not force
sentence-rhythm variation, narrative hooks, or interpretive transitions into procedural text.

### Results

Lead with the finding and comparison, then give the evidence needed to evaluate it. Keep explanation of
why it happened for the Discussion unless the genre integrates interpretation. Do not narrate every test
that was run.

### Discussion

Begin from the result's actual delta, not a generic restatement of the topic. Distinguish finding,
interpretation, plausible mechanism, alternative explanation, implication, and speculation. Include a
limitation only when it changes what the reader should believe or where the result applies.

### Titles, captions, and responses

Make titles informative rather than grandiose. Make captions sufficient to interpret the display without
repeating the Results. In reviewer responses, answer the concern directly, state the change, and avoid
performing gratitude or defensiveness at length.

## 4. Exemplar calibration

Use sufficiently varied, verified samples in proportion to what is available and to the requested genre:

- Juan-authored passages only when their authorship is known and voice matching is requested;
- comparable passages from the target journal and article type when that calibration helps.

Do not claim a voice match without reliable author samples. If samples are sparse, say that the profile is
limited and calibrate to genre rather than inventing an author voice.

Sample comparable sections. Do not infer Discussion style from Methods or a review article from a research
article. When papers are co-authored, use only passages Juan identifies as his own if claiming voice match.

Extract qualitative tendencies, not fake biometric precision:

- information density and typical sentence movement;
- paragraph progression and where claims appear;
- narrative versus parenthetical citation integration;
- hedge vocabulary and causal restraint;
- active/passive choices and the entities used as subjects;
- transition density, modifier density, and closing style.

Use the profile as a soft prior. Preserve a deliberate sentence that works even when it is statistically
unusual for the sample. Never borrow a distinctive phrase or reproduce another author's rhetorical sequence.

## 5. Structural AI smells

Diagnose the action, then fix the scientific sentence underneath it.

| Smell | What is really wrong | Better move |
|---|---|---|
| throat-clearing | the claim arrives late | start with the subject and claim |
| false reversal | an imaginary naive view props up novelty | state the distinction and evidence directly |
| rule of three | count replaces judgment | keep only independently useful points |
| mirrored paragraphs | template outranks reader function | let each paragraph take the shape of its job |
| preview plus recap | the same claim is paid for twice | keep the stronger occurrence |
| synonym cycling | terminology becomes unstable | repeat the exact technical term |
| hedge stacking | uncertainty is performed, not measured | choose one accurate qualifier |
| defensive caveat | prose anticipates a reviewer but changes no claim | cut it or name the real boundary |
| engineering diction | the manuscript becomes a pipeline specification | use the field's ordinary scientific verbs |
| grand significance | importance is asserted rather than shown | name the concrete scientific consequence |

Punctuation, individual words, paragraph length, and sentence length are contextual signals. Do not impose
global quotas. Repeated tics matter; an isolated clear use does not.

## 6. Semantic-drift audit

For an edit, compare before and after sentence by sentence. For new prose, compare every sentence with the
source brief, results, figure, or cited source.

Check five invariants:

1. **Quantity:** numbers, units, denominators, direction, and comparison are unchanged.
2. **Inference:** descriptive, associational, predictive, causal, and mechanistic levels do not silently rise.
3. **Uncertainty:** confidence intervals, variability, qualifications, and generalization boundaries survive.
4. **Attribution:** citations remain attached to the claims they support; author interpretation is not made
   to look source-extracted.
5. **Scope:** population, place, time, taxon, scale, and stated nonclaims remain intact.

If a style improvement conflicts with an invariant, keep the plainer faithful sentence. If the original is
ambiguous, flag the ambiguity rather than choosing the scientifically stronger reading.
