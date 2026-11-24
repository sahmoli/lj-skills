# lj-review — the review rubric (expanded)

The SKILL.md is the orchestration + contract; this file is the detail. It carries forward the bones of
Juan's `review-proposal` skill and adds the suite integration + honesty backbone. Read the sections that
change the requested review; this reference is not a mandatory sequence for a local comment.
Output to Juan is Chinese; keep manuscript quotes, journal names, author-year citations as-is.

## Saved-report compatibility

For new saved reviews, a compact `F<n>: severity=…; location=…; evidence=…; remedy=…` record makes the
decision trail easy to inspect. Existing reports may retain an `【行动清单】` line with an explicit severity and
remedy. Do not require a user to rewrite a valid historical report merely to adopt the compact record. In
either form, keep source records, `⚠待核`, and referee authorization/disclosure fields when they apply.

External anchors used here are **audited** (real attribution): Platt 1964 (strong inference / the
crucial discriminating test); Gould & Lewontin 1979 (the "just-so story" critique); Byrnes & Dee 2025
(pattern read as process); the debunked-default list in `../../_shared/exclusions.md`.

---

## 第零步 — classify the manuscript (sets how hard each pass bites)

Fill this table FIRST. The class is not decoration — it tells you which risks dominate.

| 维度 | 取值 | 用途 |
|---|---|---|
| 主领域 · 方法 | e.g. 群落生态 · 占据模型 / 宏生态 · SDM / 保护 · 政策评估 | picks which methods referee (R2) lens to load |
| 数据类型 | 观测 / 实验 / 整合分析 / 模拟 / 文献综述 | sets the identification bar (causal claims from observational data = high risk) |
| 成熟度 | **A** 接近可投 · **B** 需大改 | A → polish + desk-safety; B → claim and design repair |
| 最大单点风险 | one line — the thing most likely to kill it | everything else is secondary until this is addressed |

Idea/proposal-stage work without a substantial draft routes to `lj-design`; this rubric does not redesign it.

---

## Search protocol (when literature affects the requested verdict)

A review without relevant literature search is `opinion-grade, search pending` for novelty or
publication-priority claims. Search only the evidence needed to support those claims, source-trace material
results, and disclose the checked scope:

1. **Nearest relevant work.** What is the prior art that bears on a claimed novelty or differentiation?
   Use an appropriate authoritative source and name the material comparators actually checked.
2. **Target-journal saturation.** Check the target venue only when publication positioning matters.
3. **Verifiable method references.** Each method claim the review invokes ("the standard way to
   do X is …") must point to a REAL, resolvable paper. If you can't resolve it, it's a **lead (⚠待核)**,
   not a citation. For a manuscript with many citations, hand them to **lj-evidence** (存在性 / 元数据 /
   支撑性 — 存在 ≠ 支撑) and fold its verdicts in here; the dangerous case it catches is "exists but
   doesn't support the claim".

> **绝不编造引用.** This is the review-side of the suite's never-fabricate rule. A made-up "this was
> already shown by Smith 2019" misleads the author into killing real novelty (self-review) or is a
> referee acting in bad faith (referee mode). No resolvable source → say "I believe this exists, verify"
> and mark ⚠待核. Better an honest gap than a confident fabrication.
>
> **检索卫生.** In referee mode, search only with topic and structure terms. Never paste manuscript
> sentences, quotations, or unique phrasing into OpenAlex / PubMed / web queries.

---

## Venue hand-off (Phase 0.5 — call lj-journal, don't re-derive)

Do not hand-derive word/figure caps, desk-reject triggers, AI-disclosure placement, review model, or
SCB sibling routing. Call **lj-journal** with (journal, article type) and fold its contract in:
fit verdict · caps for THIS article type (met?) · top desk-reject risks · whether a sibling journal owns
the contribution more strongly (re-route BEFORE critiquing format). That keeps one source of truth for
venue facts and lets this skill spend its effort on the science.

---

## Phase 1 — 文献锚定 (is the contribution real?)

Against the relevant nearest work: state the **actual delta** of this manuscript. Is it (a) a genuinely
new question, (b) a new method/data on an old question, (c) a new system/scale for a known result, or
(d) a confirmation/replication (legitimate, but must be sold as such)? If the delta is thin, that's the
headline finding — say it in 【一句话判断】. Strong inference (Platt 1964): does the paper actually
discriminate between competing hypotheses, or just accumulate consistency with one?

**Delta-clause template** (when a comparator is available): *"Unlike `<closest relevant author-year>`, this paper shows
`<X>`, which revises the assumption that `<Y>`."* If `<Y>` is not a real prior assumption, the delta is
(b)/(c)/(d), not (a) — don't inflate it into novelty. **Name the overturn:** which accepted ecological
default does the paper overturn? (candidate pool = `../../_shared/exclusions.md`, already used in
the concept-rigor pass.) If it overturns nothing, say **"incremental"** plainly — a mislabelled incremental
result is a provenance violation, the review-side of never-fabricate. Also flag **gratuitous neologisms or unanchored private taxonomies** where established disciplinary terms or standard classifications (e.g., IUCN–CMP, Theory of Change) already exist and should be cited directly.

## Phase 2 — 编辑视角 (will it survive the desk + excite an editor?)

Before referees: would the handling editor send it out at all? In scope (per lj-journal)? Is there a
single, crisp, exciting take-home, or is it buried? Desk-reject risk (caps, anonymization, scope, DAS)?
An editor reads the abstract + figures + last paragraph of intro — does THAT package land?

## Phase 3 — 三审稿人模拟 (the room)

Use the three lenses to diversify scrutiny, not to multiply comments. Each lens may contribute at most one
non-duplicate finding that could change the recommendation or claim boundary; it may also report no major
issue in its checked scope. Do not fill empty referee slots with generic caveats.

- **R1 领域 (domain).** Is the contribution true and important to the field? Does it engage the right
  literature? Is the framing honest about what's new? Findings sourced.
- **R2 方法 (methods).** Do the statistics/identification/data actually support the claims? Run R2 in five moves:
  - **(a) Generic baseline.** Causal claim from observational data? Pseudoreplication, spatial
    autocorrelation, scale mismatch, model misspecification, uncorrected multiplicity? Reproducible
    (code/data)? Cross-cutting, every paper. This is usually where 🔴/🟠 live. Sourced to method references.
  - **(b) Design-type lens.** Load the row matching the study design (table below) — a generic checklist
    misses design-specific traps (the #1 being phylogenetic non-independence in comparative data).
  - **(c) Internal-number consistency (don't take printed figures on trust).** No data needed: do subgroup
    n sum to N? do df match the design/n? is each CI consistent with its SE/p? do headline means/percentages
    recompute? A mismatch is 🟠 — flag the specific cell/figure, don't demand a reanalysis you can't run.
    (The statcheck / GRIM discipline — Nuijten et al. 2016; Brown & Heathers 2017 — borrowed as principle.)
  - **(d) Robustness honesty.** Does each sensitivity/robustness analysis probe the main claim's *weakest*
    assumption (detection probability, spatial autocorrelation, scale, model/prior choice), or vary a
    peripheral knob while the load-bearing assumption goes unchecked (decorative robustness)? Flag any check
    sold as "robust to X" that in fact varies Y. Do not request another check unless it targets a distinct
    live threat and a plausible result could change the claim or recommendation. In self-review, if a frozen
    `lj-design` SPEC exists, compare the manuscript analysis to it and report **declared deviations vs
    undeclared deviations**; an undeclared deviation is 🟠 by default.
  - **(e) Recompute — don't just ask** (CONDITIONAL: only with legally accessible, runnable code and data
    supplied or explicitly authorized for this review, including authorized local materials). Reproduce only
    the smallest result that could change the decision; begin from the provided instructions or a clean
    checkout when that is relevant. A claimed runnable result that fails to reproduce is 🔴/🟠. Missing
    dependencies, data, compute, authorization, or runnable artifacts means `no reproduction` with the
    reason under ⚠待核—never a silent pass. Do not reproduce materials that are illegal or unapproved to use.

  **R2 design-type lens** (load the matching row; fall back to baseline (a) if the design isn't listed):

  | 设计类型 | naive 陷阱 | 现代估计量 (锚) | 一个辩护诊断 |
  |---|---|---|---|
  | Occupancy / detection | 把"没测到"当"不在",忽略 detection<1 | occupancy / N-mixture (MacKenzie et al. 2002; Royle 2004) | 报告 detection probability + 协变量 |
  | PGLS / 比较法 | 物种当独立样本(系统发育非独立) | PGLS (Felsenstein 1985; Freckleton et al. 2002) | 报告 Pagel's λ |
  | BACI | 无对照/无前期,把趋势当处理效应 | 处理×时间交互项 | 前期 处理-对照 平行性 |
  | Space-for-time | chronosequence 当时间序列(隐含立地同质) | 把"空间替时间"当假设而非事实 | 立地混杂因子检验 |
  | GEE / 遥感时序 | 像元/时点伪重复 + 空间自相关 | 显式空间/时间结构模型 | 残差 variogram / ACF |

  设计不在表内 → 回退基线 (a)。完整的**深度域门**(PGLS 假设全套 / GEE-RS provenance / 物种名 harmonization)
  属于 Juan 的独立 **ljg-gate** 项目——此处只做轻量设计感知,不重复造它的轮子。
- **R3 "Reviewer #2".** The harshest *fair* skeptic. Sort what R3 raises into **fatal** (claim cannot
  stand) / **major** (needs substantial work) / **addressable** (fixable in revision). The job here is to
  surface the worst defensible objection so Juan meets it first — NOT to manufacture nitpicks. Tag any
  point that is taste, not defect, with `[口味]`.

## Phase 4 — 最短可投路径 + 顶刊上限

First state the **minimum change set** that makes the manuscript's present claim defensible. Use the least
expansive remedy: cut, qualify, re-scope, clarify existing evidence, then add analysis or data only if the
earlier remedies cannot answer a load-bearing threat.

Separately state the **top-journal form** and at most **one optional** analysis, reframing, or piece of data
that could lift it there. Label it `[可选提升]`; do not disguise aspiration as a necessary defense. One, not
ten. Do not demand a new multi-year field study to fix a framing problem.

## Phase 5 — 行动清单 + 修订日志 (severity-ranked, actionable)

Severity ladder — every finding gets exactly one, tied to a specific line/figure/claim + the concrete fix:

| 级别 | 含义 | 处理 |
|---|---|---|
| 🔴 FATAL | claim cannot stand as written / 不可投或应拒 | must resolve before submission/acceptance |
| 🟠 MAJOR | serious, needs substantial revision | address before resubmission |
| 🟡 MINOR | small, polish-level | fix in pass |
| 🔵 STRATEGIC | positioning / venue / story-telling advice | judgment call, not a defect |
| `[口味]` | reviewer preference, NOT a defect | disclose, don't inflate |

For referee mode, end with a one-paragraph recommendation (accept / minor / major / reject) consistent
with the ladder. For self-review mode, default to the three most consequential non-duplicate actions, then
the Phase-4 optional upgrade. Aggregate minor copy edits unless Juan requests line editing.

---

## Concept-rigor checklist (borrows lj-concept — the flaws referees miss)

Run these four against the manuscript's core reasoning. Each maps to an audited anchor:

1. **Pattern read as process?** A correlation/spatial pattern narrated as if the mechanism were
   demonstrated (Byrnes & Dee 2025). Demand the process evidence or a downgraded claim.
2. **Just-so story?** A plausible adaptive/causal narrative with **no novel testable prediction** is not
   a mechanism (Gould & Lewontin 1979). Ask: what would this story predict that the alternative doesn't?
   (Platt 1964: the discriminating observation.)
3. **Debunked default asserted as fact?** balance-of-nature, diversity→stability as a law, carrying
   capacity K as a measured truth, climax community — see `lj-concept/references/exclusions.md`.
   Flag any that appear unqualified.
4. **Proxy mistaken for the construct?** Has a measurement/index quietly become the concept it was meant
   to estimate (construct validity)? e.g. species richness standing in for "biodiversity value", a single
   metric for "ecosystem stability".

A manuscript can be statistically clean and still fail here — these are the soft-reasoning defects that
get past R2 but sink a paper in revision or post-publication.

---

## The shared self-critique contract (the suite's pre-ship self-gate — lj-review owns it)

This is the canonical menu of honesty and faithfulness checks. Select only the checks that could change the
requested artifact's correctness, evidence status, or claim boundary; do not turn it into a default shipping
ritual or a defense package. Skills may reference this shared source instead of copying it. Borrowed ideas:
the always-on Scientific Critic (Virtual Lab, ingested `wiki/sources/virtual-lab-swanson-zou-2025`) and honest
abstain / admit-failure (Aletheia, wiki) — reimplemented, no framework dependency.

Apply relevant checks in the order the artifact needs:
1. **Strongest objection.** State the strongest *evidenced* flaw a referee/critic would raise to this
   specific output (not a generic worry). If no fatal flaw is supported in the checked scope, say
   `none found in checked scope`; never invent one to prove diligence.
2. **Honesty self-scan.** Any fabricated citation / fabricated novelty / invented number? Any **⚠待核**
   quietly passed as if confirmed? Is grounded-vs-speculative blurred anywhere? Is a debunked default
   (`lj-concept/references/exclusions.md`) asserted as fact? Each hit must be fixed or flagged, not shipped.
3. **Taste vs defect.** For each self-flaw, decide: real defect, or my own preference? Label preferences
   `[口味]` so they don't masquerade as blockers (the Reviewer-#2 guard, applied to yourself).
4. **Severity + smallest fix.** Tag what you're about to ship 🔴/🟠/🟡 and give the least expansive concrete
   fix for the worst: cut or qualify before adding machinery.
5. **Abstain exit.** If the output cannot clear its own strongest objection (point 1), **say so** — mark it
   `speculative`, downgrade it, or abstain. A confident wrong answer is the worst outcome; an honest
   "this doesn't hold up, here's why" is a success of the gate.

Each generator states in its own honesty backbone how this contract applies. This canonical file does not
maintain a roster.

When the stakes are high (a real submission, a contested claim), escalate from the self-gate to the full
referee review above only when Juan requests it or the evidenced risk warrants it. The contract is the fast
filter, not a ritual that forces a heavy review.

---

## The honesty rules (recap — these are load-bearing, not style)

- 绝不编造引用 — real source or ⚠待核. Never a confident fake.
- 区分缺陷 vs 口味 — `[口味]` label; don't inflate preference into severity.
- 针对具体稿件 — every point cites a specific line/figure/claim + concrete fix; no boilerplate.
- 不确定就标注 — say what you'd need to check; don't guess.
- 自审不护短也不自残 — surface evidenced, decision-relevant defects; do not manufacture criticism;
  praise only to mark what to protect.
- 已认局限 ≠ 审稿发现 — a weakness the manuscript already concedes is not a referee finding; credit the
  disclosure, then go beyond it. The value is the flaw the authors did NOT concede. (Matters most in 自审.)
- 绝不替写正文 — critique and strengthen; never ghost-write the manuscript.
