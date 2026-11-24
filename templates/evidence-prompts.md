# Prompt scaffolds

Prompts generate hypotheses and search routes, not evidence. Require every named scholar/work/database to carry
`verified | needs verification`; verify outside the model before admission.

## 1. Field map

```text
I am preparing <output/decision> about <topic>, scoped to <time, geography, languages, actors>.
Act as a curriculum designer plus historiography mapper. Produce a 10–14 unit field map, not an essay.

For each unit give:
1. the question it answers;
2. major rival interpretations or paradigms;
3. primary-source genres and collections that could adjudicate the dispute;
4. landmark, revisionist, and frontier works, separated;
5. methods or source discoveries that changed the field;
6. differences among <relevant regional/language traditions>;
7. contested or superseded claims;
8. terms, historical names, and controlled vocabulary for further search.

Mark each proper name/work `verified` only if you can provide authoritative metadata; otherwise mark
`needs verification`. End with disagreements or missing traditions that another mapper should challenge.
```

## 2. Source universe and multilingual query matrix

```text
Given this question contract and provisional field map, act as a research librarian and archivist.
Do not answer the research question. Construct a source census and search matrix.

Columns: source genre; creator/institution; period; region; actor/voice; language/script; historical names;
transliteration variants; controlled terms; bibliographies/catalogues; repositories/finding aids; databases;
known-item seeds; likely access/licence; characteristic bias or survival gap.

Then produce query families by route, not one flat keyword dump:
- known-item/author
- subject/controlled vocabulary
- source genre/archive/collection
- backward and forward citation seeds
- journal/series/press
- regional-language scholarly tradition
- disconfirming/minority/missing-voice search

Rank families by expected coverage gain. Remove direct translations that have no demonstrated local usage.
Mark all unverified names and collections `needs verification`.
```

For effect/impact questions, append:

```text
Create a separate evidence grid for mechanism, outcome/proxy, counterfactual/comparator, rival explanations,
and disconfirming evidence. For every candidate, state what causal role it can support and its evidentiary
ceiling. Do not treat evidence of policy/institutional existence as evidence of effect.
```

## 3. Adversarial gap pass

```text
Audit this field map, coverage matrix, admitted-source list, and search log as a skeptical historian,
archivist, area-studies scholar, and information-retrieval researcher.

Find:
1. one canon/reputation loop;
2. one duplicated source lineage mistaken for independent evidence;
3. one language, region, actor, institution, period, or source genre missing for structural reasons;
4. one version/translation/provenance risk;
5. one credible disconfirming source class;
6. one search route not yet tried that has a different failure structure;
7. one claim that the current corpus cannot support.

For each, name the evidence needed to resolve it. Do not invent citations. End with `close | another round`
and the exact closure test that failed.
```

## 4. Expert annotated list request

```text
I am trying to support <decision/output>, not merely learn the topic. Please recommend a small spanning set,
and for every item explain: what role it plays; which claim/source type it is good for; what it gets wrong or
omits; which edition/translation to use; and what I should read against it. Please include one bibliography or
finding aid, one primary-source gateway, one major disagreement, and one work outside your own school/tradition.
```
