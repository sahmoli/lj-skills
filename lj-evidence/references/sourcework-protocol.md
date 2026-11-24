# Sourcework protocol and theory anchors

## 1. The object being built

A folder is not a corpus. A corpus is a deliberately admitted, provenance-preserving set of sources whose
coverage and limits are visible. Represent it as four linked objects:

1. **Question contract** — the claims or decisions the evidence must support.
2. **Source census** — the plausible universe of genres, repositories, languages, traditions, periods, and
   voices; this exists before individual downloads.
3. **Evidence graph** — sources linked to claims, source lineages, contradictions, versions, and gaps.
4. **Search ledger** — routes tried, query changes, admissions/rejections, access status, and stop/reopen
   decisions.

The reachable evidence space is approximately:

`coverage × fitness × independence × provenance × retrievability`

This is not a numeric score. A zero-like failure on one axis can dominate: an inaccessible snippet cannot
support a strong claim; ten derivative stories remain one lineage; a mistranslated edition can corrupt a
well-covered corpus.

## 2. Source census lenses

Select only lenses that expose consequential missingness.

| Lens | Questions |
|---|---|
| Genre | law, letter, diary, ledger, image, map, object, oral account, dataset, scholarship, catalogue? |
| Production | who created it, for whom, under what incentive, template, institution, or coercion? |
| Survival | what was preserved, destroyed, weeded, privately held, or never recorded? |
| Description | who catalogued/digitized it, using which vocabulary, hierarchy, OCR, and selection policy? |
| Access | language, subscription, archive rules, privacy, location, format, disability, technical barrier? |
| Tradition | which national, regional, disciplinary, ideological, or linguistic scholarly conversation? |
| Time | contemporary traces, retrospective accounts, editions, later reinterpretations? |
| Lineage | independent observation, copied record, translation, reprint, digest, or retelling? |
| Voice | state/elite/institutional voice versus affected, local, non-literate, absent, or unsafe-to-speak actors? |

Missingness is data only after its production mechanism is considered. “Not found” can mean absent in the
world, absent from the archive, undescribed, undigitized, inaccessible, or missed by the query.

## 3. Search routes

Marcia Bates's berrypicking model rejects the fiction of one stable query returning one final set. In real
humanities research, sources change the question and the route. Preserve this evolution.

| Route | Strength | Characteristic failure |
|---|---|---|
| Known-item / author | high precision, recovers a landmark and its oeuvre | inherits the initial canon |
| Subject / controlled vocabulary | systematic within an index | vocabulary and cataloguing bias |
| Backward chaining | finds intellectual ancestry and hidden sources | walks only preserved citation lineages |
| Forward chaining | finds uptake, correction, and reinterpretation | database/date/language coverage bias |
| Journal/series/press run | local recall inside a venue | venue tunnel vision |
| Area/collection scanning | finds neighbours missed by words | classification/arrangement bias |
| Bibliography/review/handbook | fast field map | authority freezes one historiography |
| Finding aid/archive portal | exposes record groups and provenance | description is not item-level completeness |
| Expert annotated list | recovers tacit landmarks and reasons | prestige/network and school bias |
| General web/discovery model | high-recall lead generation | ranking, SEO, hallucination, missing metadata |

Use complementary routes with different failure structures when a deep build needs broader coverage. Expand
queries across languages and vocabularies where those choices could hide relevant material; do not mistake a
direct translation for complete coverage.

## 4. Triage and historical criticism

### Discovery prior versus admission evidence

Citation counts, prestigious venues, course frequency, and multiple model recommendations help order a search.
They do not prove truth, fitness, independence, or representativeness. A source can be highly cited because it
is canonical, controversial, convenient, wrong, or repeatedly criticized.

### External criticism

- What exactly is the object and which version/edition/translation is present?
- Is authorship, date, provenance, custody, and integrity established?
- Has the text been copied, excerpted, normalized, OCRed, translated, or silently edited?
- Can the original passage and stable location be recovered?

### Internal criticism

- What did the source mean in its genre and historical context?
- What could the source-maker know, and through which observation chain?
- What were purpose, audience, incentives, conventions, risks, and silences?
- Which claims are direct observation, report, inference, performance, memory, or formula?
- What independent source could corroborate or challenge it?

### Negative-space criticism

- Which actors could not write, preserve, publish, archive, digitize, or grant access?
- What did the institution have reason not to record?
- Which cataloguing terms erase the relevant identity or practice?
- Are apparent absences produced by language, OCR, access, or archive survival?

## 5. Spanning-set design

Do not begin with the top N most cited. Assemble roles:

- orientation bibliography / field guide;
- foundational or paradigm-setting work;
- central primary-source collection or catalogue;
- current frontier synthesis;
- strongest revision or refutation;
- disconfirming or negative case;
- underrepresented tradition, language, region, actor, or source genre;
- method/data work needed to judge evidence quality.

Read enough to revise the map and admission criteria. Then scale acquisition. This makes breadth a learning
loop rather than a hoarding stage.

## 6. Closure test

“Search until exhausted” is impossible; “stop after 100 keywords” is arbitrary. Close a round when:

1. the question-critical matrix cells have either adequate sources or an explicit gap mechanism;
2. the central claim graph has appropriate primary and independent anchors;
3. disagreements and credible disconfirming cases are represented;
4. relevant routes with different biases show diminishing conceptual/source yield;
5. new material mostly duplicates known lineages and no longer changes the map or decisions;
6. residual uncertainty and a reopen trigger are recorded.

Possible reopen triggers: the research question changes, a central contradiction appears, an archive opens,
a new language/region enters scope, an unsupported claim survives drafting, or a reviewer identifies a missing
tradition.

For qualitative interviews or field-created sources, distinguish **breadth closure** (few new codes/topics/source
types) from **depth closure** (few new dimensions, meanings, mechanisms, or counterexamples). Do not import
sample-size thresholds from one interview study into documentary research.

## 7. Method comparisons

| Method | Best condition | Advantage | Failure mode | Complement |
|---|---|---|---|---|
| EP27 syllabus → multilingual keywords | unfamiliar but course-shaped field | fast boundary map and vocabulary | AI fabricates canon; a course reproduces disciplinary canon; keyword translation misses source systems | catalogue verification, citation/collection routes, coverage matrix |
| Multi-model union | mapping uncertainty and available independent models | raises candidate recall, makes divergence visible | correlated training data; union amplifies shared blind spots and hallucinations | authoritative metadata and adversarial gap pass |
| Citation/venue threshold | mature, indexed field as search ordering | cheap discovery prior | penalizes new, regional, book-based, archival, non-English, and sparse fields | claim fitness, provenance, expert/context calibration |
| Bulk corpus for AI weighting | legal full text and a bounded synthesis task | repeated themes become more retrievable | popularity becomes truth; duplicates and low-quality text distort weights | deduplication, source lineage, balanced spanning set |
| Traditional heuristic + source criticism | historical claims with recoverable traces | forces provenance, authenticity, meaning, and corroboration | classic positivism can underplay archive power and silenced voices | archival/negative-space criticism and reflexive source census |
| Berrypicking | exploratory humanities/social-science search | treats changing questions and multiple routes as normal | can wander and hide selective stopping | explicit ledger, coverage matrix, closure test |

## 8. Audited anchor ledger

- Shishufeng EP27, “AI 时代如何更好地找资料？feat. 六兽,” official transcript, 2026-08-13.
  Contribution: explicit syllabus prompt, multi-model multilingual keyword union, human screening, source-type
  triad, citation/venue/expert heuristics, time cost, stop/failure modes. Limit: practitioner account; claims
  about model retention and volume effects are not controlled evaluations.
- Shishufeng EP18, “大豆,” official transcript, 2026. Contribution: prior public version of essentially the
  same syllabus → multilingual query → human search → key reading → database workflow.
- Charles-Victor Langlois and Charles Seignobos, *Introduction to the Study of History*, 1898 English edition.
  Public-domain full text via Project Gutenberg. Contribution: heuristic (document search), external criticism,
  internal criticism, and synthesis. Limit: dated positivist assumptions; use as a historical anchor.
- Marcia J. Bates, “The Design of Browsing and Berrypicking Techniques for the Online Search Interface,”
  1989. Author-hosted full text. Contribution: evolving query and six complementary search tactics.
- Society of American Archivists, *Using Archives: A Guide to Effective Research*. Official open guide.
  Contribution: repository/finding-aid discovery, archivist contact, access preparation, citation and follow-up.
- Oral History Association, *Principles and Best Practices*, revised 2018. Official open page. Contribution:
  research design, consent, power, collaboration, preservation, and repository responsibilities for created
  sources.
- Hennink, Kaiser & Marconi, “Code Saturation Versus Meaning Saturation,” 2017, and Saunders et al.,
  “Saturation in qualitative research,” 2018, author/PMC open full text. Contribution: distinguish broad
  topic/code coverage from depth/meaning saturation and bind the saturation concept to the research question
  and analytic approach. Limit: qualitative interview studies/reviews; reported sample counts are not universal
  thresholds for document search.
- 梁启超，《中国历史研究法补编》, public-domain scan on Wikimedia Commons. Contribution: Chinese historical
  training tradition; scanned original retained, text extraction currently unavailable without OCR.
- 余嘉锡，《目录学发微》, public-domain scan on Wikimedia Commons. Contribution: 目录、版本、学术源流 and
  finding books through bibliographical structure; scanned original retained, text extraction currently
  unavailable without OCR.
