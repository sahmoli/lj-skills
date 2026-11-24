# `lj-evidence` — Verification Protocol (`v2.0`)

The SKILL.md is the orchestration and contract; this file is the detail. Everything serves one doctrine:
**存在 ≠ 支撑 (existence ≠ support)** — the valuable, hard work is proving the source actually backs the
claim, not just that it exists. Bibliographic APIs supply DATA, not verdicts.

---

## The four axes (escalating cost, escalating value)

| 轴 | 问的是 | 怎么查 | 失败 / 预警时 |
|---|---|---|---|
| **1 存在性** existence | 这篇被引文献真的存在吗？ | DOI / arXiv ID → Crossref / OpenAlex / arXiv resolve；无 ID → title+author+year 匹配 | 有界搜索后仍 resolve 不到 → 🔴 unresolved / suspected fabrication；不是“不存在”的证明 |
| **1.5 学术诚信与版本状态** integrity | 这篇文献是否被撤稿、勘误，或预印本已正式发表且发生结论漂移？ | `resolve_citation.py` 自动检查 OpenAlex `is_retracted`、Crossref `update-to` / `relation`（含 Retraction Watch 信号）与预印本→正式版映射 | 撤稿 → 🔴 retracted（立即标红禁作正面支撑）；勘误/关切 → 🟠 updated-or-corrected；预印本已发表 → 核查正式版是否改结论 |
| **2 元数据一致性** metadata | 引用写的 作者/年/刊/题 与真实记录一致吗？ | 比对 resolved record | 不符 → 🟠 误引（写错年/作者/刊） |
| **3 支撑性** support | 这个源真的“说了”这句话所声称的吗？ | 按访问阶梯先查本地全文库（`search_local_corpus.py`），再取合法 OA 源文本逐句核 | 不支撑 → 🔴 存在但不支撑（最危险）；取不到 → ⚠待核 |

Axes 1–2 are cheap and deterministic (`resolve_citation.py`). **Axis 1.5 catches poisoned/retracted/drifted literature automatically.** **Axis 3 is the reason this skill exists.** A reference can pass 1, 1.5, and 2 and still be attached to a claim it never makes — or that it contradicts.

---

## The legal-access ladder (for Axis 3 — support)

Use the first legal source that is sufficient for the claim; begin with task-provided text or already-downloaded private local full texts, then choose the smallest suitable authorized rung. **Never download paywalled material** or search Juan's personal Zotero without authorization.

1. **Task-provided legal text / local private corpus (`D:\hub\10_raw\papers\`)** — run `search_local_corpus.py` first; locate exact physical page (`<!-- pdf-p0001 -->`) and visually verify against the PDF when numbers/qualifiers are load-bearing.
2. **Legal open-access full text** — `fetch_oa.py` cascade: explicit legal URL → native arXiv PDF → OpenAlex → Unpaywall → Europe PMC → Semantic Scholar OA.
3. **Juan's Zotero full-text, when an installed and explicitly authorized capability is available** — otherwise record that this source was not searched.
4. **Abstract-only** — if only the abstract is legally available: you may judge support **only if the claim is abstract-level**; a fine-grained claim (a specific number, denominator, subgroup, or methodological detail) → **⚠待核**, not a guess.
5. **No legal access** → **⚠待核** with a one-line note of what is needed (and write a `_wanted.md` lead in `D:\hub\00_inbox\` when helpful — never an automated paywall download).

Record which rung was used on every support verdict — it sets the confidence.

---

## The support verdict rubric (Axis 3)

- **✅ supports** — the source states (or directly entails) the claim; cite the locating detail (page anchor / section / figure / quote) so Juan can re-find it.
- **◑ partial** — supports a weaker/narrower version than the sentence asserts; state how to soften or scope the claim.
- **🔴 exists-but-doesn't-support** — resolves, metadata clean, but the claim is **not in** the source (or is **contradicted** by it). Headline finding under 【最危险先修】.
- **🔴 retracted** — source is flagged retracted via Crossref/OpenAlex/Retraction Watch signals; cannot serve as positive support.
- **⚠待核** — full text not legally reachable, or only abstract for a fine-grained claim. Never silently upgraded to ✅.

A "supports" with no locating detail is not a verdict — it is a vibe. Always anchor it.

---

## Optional domain lenses

- **Ecology & Conservation**: load [domain-ecology.md](domain-ecology.md) for method-citation correctness, debunked defaults, and ecology self-citation checks.
- **AI / CS / Education / Interdisciplinary**: check preprint-vs-published drift (`arXiv` vs conference/journal version), benchmark saturation/date-slice validity, and separate peer-reviewed empirical studies from vendor blogs or whitepapers.

---

## Precedent search (the `lj-question` novelty handoff — back-or-kill)

A separate axis with an INVERTED question. Support asks *"does this source back the claim?"*; precedent asks *"does any source already exist for this NOVELTY claim?"* `lj-question` marks every originality claim ⚠待核 and hands it here.

**The procedure**
1. **Decompose** the claim → phenomenon · mechanism/relationship · system/taxon · **scope word** (first / unexplored / novel-combination).
2. **Search the STRUCTURE, broadly** — use `discover_sources.py` across OpenAlex + Semantic Scholar + arXiv (plus backward/forward snowballing from seed papers) covering synonyms, adjacent fields' vocabulary, and review/synthesis articles that would cite the work if it existed.
3. **Closeness grading on a hit:** **exact** (same phenomenon × mechanism × system) → novelty dead; **near** (two of three) → novelty must be narrowed; **partial** (related but a real gap remains) → novelty survives, reframed around the gap.

**The three verdicts**
- **FOUND** (exact/near/partial) — cite the work(s) + DOI/arXiv ID + closeness. Hand back to `lj-question`: kill or reframe the novelty pitch ("extends X", not "first").
- **NOT-FOUND** — no precedent surfaced after a real, bounded search. **Provisional, scoped, never "definitively first".** Record databases, terms/synonyms tried, date range, and **what was NOT searched**.
- **⚠待核** — claim too ambiguous to decompose, scope undecidable, or key databases unreachable. Never default an unsearched claim to NOT-FOUND.

**Honesty (two mirror failures):** absence of evidence ≠ evidence of absence. Guard against (1) **false NOT-FOUND** by searching structure across vocabularies, and (2) **false FOUND** by reading the candidate's abstract/text before killing a novel question (`存在 ≠ 支撑`, applied to precedent).

---

## Data-source routing (DATA, not skills)

- **Active topic discovery & citation snowballing** → `scripts/discover_sources.py` (OpenAlex + Semantic Scholar + arXiv; `--seed-doi --backward --forward`).
- **Local-first full-text lookup** → `scripts/search_local_corpus.py` (`D:\hub\10_raw\papers\*.md` page anchors).
- **DOI / arXiv resolve & retraction check** → `scripts/resolve_citation.py` (Crossref, OpenAlex, PubMed, arXiv).
- **Legal OA PDF fetch** → `scripts/fetch_oa.py` (explicit legal URL, arXiv, OpenAlex, Unpaywall, Europe PMC, Semantic Scholar).
- **Juan's own Zotero** → use installed, authorized capability only; otherwise record `not searched`.

---

## Confidence ladder (mirrors the suite)

- **official / high** — checked against full text Juan can re-open (local private library / stable OA copy), with a physical page or section anchor and clean integrity check.
- **secondary** — checked against abstract or record-level metadata only (existence/integrity/metadata solid; support abstract-level).
- **⚠待核 / lead** — could not legally reach the text needed; what is missing is named.
