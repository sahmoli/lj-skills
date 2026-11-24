# weave-engine — the织网 engine (single source of truth)

Load only the needed section when running lj-weave. SKILL.md is the orchestration + contract; this is the detailed
machinery. Table of contents:

- § 六生成器 — the skeleton lj-weave anchors to (don't re-derive; pointer to the hub)
- § 抽节点表 — extracting the real root from each essay (grep ladder + fallback)
- § 五种边 — the five edge types, each with a mechanism template + worked example
- § 结构洞 — ranking missing nodes by citer demand (WantedPages), not by vibes
- § 验证门 — the cross-domain-isomorphism verification protocol
- § Pass-01 金标准 — the killer edges any correct run must reproduce (regression ledger)

---

## § 六生成器 (the anchor skeleton)

The single source of truth is the hub page [[降秩系列-生成器字母表]]. Do not re-derive it; anchor to it.

- **A 缺口 / 匮乏当发动机** — system never coincides with itself; the gap is the engine. (人生·意义·爱·幸福·经济稀缺·货币·权力·宗教)
- **B 变异 + 选择（棘轮）** — generate variation, environment filters, survivors ratchet up irreversibly. (演化·生物·适应·知识·科学·技术·文明·AI)
- **C 反馈环** — quantities push each other; positive self-amplifies, negative self-stabilizes. (复杂系统·系统·生态系统·气候·网络·政治·佛教·心理)
- **D 压缩** — squeeze the manifold into a short core that regenerates it; the harder the squeeze, the wider the reach. (知识·信息·模型·数学·语言·叙事·艺术·美·测量)
- **E 势差 → 流动** — a gradient makes something flow; the flow does work and levels the gradient. (熵·物理·化学·物候·地理·货币·信息)
- **F 张力对（对立统一）** — a line pulled from both ends; the real thing sits in the middle, extremes capsize. (哲学·道家·自由意志·自由·伦理·人性)

A domain spanning two or three generators is the norm — that overlap is the interface where cross-domain
weaving happens.

## § 抽节点表 (extract the node table)

Per essay, recover the **root**, not the title:

1. **Closing root sentence.** The most reliable signal is the last prose line before the trailing `---`
   / ASCII skeleton. Grep ladder (try in order): `拆到底` · `就这么几根` · `就这么.*根线` · `到底就这` ·
   `收成.*根` · `底下.*就这`. Most essays end with one ("乱了一辈子的东西，到底，就这么几根线。").
2. **Fallback to frontmatter.** If no closing sentence matches (≈ a few essays bury it inside the ASCII),
   use the `domain:` field (it names the domain + its cross-domain framing) plus `tags:`.
3. **Emit** `领域 — 根的一句话 — 主生成器(A–F)`. Keep the root in the essay's own words; that is the 底料
   the edges are tested against. If a node's generator is ambiguous, list both — the overlap is a weave site.

## § 五种边 (the five edge types)

Edges live only at **shared generator**, **adjacent ladder rung**, or **opposed tension**. Each emitted
edge MUST carry its mechanism.

### 1. 同源 (co-source) — cheapest, weakest
Two domains hang on the same generator. Template: `<A> ── <B> · 共享生成器 <X> · 机制: 都靠 <X 的动作>`.
Example: 货币 ── 信息 · both E (势差→流动) · 机制: 都靠"势差驱动流通"，钱在购买力差里流，信息在信道两端的不确定差里流。
This is a weak edge — it says "same family", not "same machine". Don't over-claim it as isomorphism.

### 2. 同构迁移 (isomorphic transfer) — most valuable, #1 hallucination zone
*Same machine, different material.* Template: `<A> = <B> = … · 同一台机器换料 · 机制: <name the ONE
shared machine and how each material instantiates each part>`. Must pass the surface-vs-structure test
(§ 验证门) and carry `grounded` / `^[inferred]`.
Worked example (杀手边①): 演化 = 科学 = 知识 = 经济 = AI · the machine = **变异 + 选择转成的棘轮**:
generate variants (突变 / 猜想 / 试错 / 参数扰动) → a narrow gate selects (生死 / 反驳 / 市场 / 损失) →
fidelity ratchets the survivors (遗传 / 扛过反驳 / 制度 / 梯度下降). Grounding: Universal Darwinism
(Campbell 1960 BVSR; Dawkins; Dennett; Hull; Mesoudi) + Popper. The "same skeleton" compression →
`^[inferred]` → gate.

### 3. 派生·尺度 (derivation / scale)
The lower layer's root IS the upper layer's phenomenon; 尺度 is the elevator. Template:
`<下层> ──> <上层> · 下层的根=上层的现象 · 机制: <what the lower root becomes upstairs>`.
Worked example: 物理 ──E──> 化学 ──键的成本账──> 生物 ──B──> 生态. Crossing a rung is **translation**,
not addition — new roots emerge at each floor (emergence), which is why 尺度 gets its own node.

### 4. 嵌套 (nesting)
Same machine, one scale up, **mechanism unchanged**. Template: `<尺度1> ↔ <尺度2> · 同机制换尺度`.
Example: 个体 ↔ 种群 ↔ 生态系统 ↔ 生物圈 (selection runs at each level). Discriminator: if moving up a
scale makes a **new root** appear, it is a 派生 edge, not 嵌套.

### 5. 张力·矛盾 (tension / contradiction) — the problem generator
Two roots pull against each other; the gap is a deep question. Template:
`<A> ◄──► <B> · 对顶 · 落差=深问题: <the question> · (缺的桥: <hole>)`.
Worked example (矛盾①): 熵(E, 走向无序) ◄──► 生命/生态系统(C, 局部建序) · 深问题: 生命怎么在熵增宇宙里
持续造序？· 缺的桥: 耗散结构/自组织. Return an idea-row suggestion only; writing it to
`context/ideas.md` still needs Juan's authorization and the live Wiki contract.

## § 结构洞 (rank missing nodes by citer demand)

## § Structural-Hole Detection

A structural hole is a target concept that **multiple existing notes point toward, yet no dedicated note exists**:
- **Rank by citer demand, not intuition:** count incoming mechanistic edges from in-scope notes, weighted by the citing notes' centrality (cf. Wulczyn et al. 2016).
- **Separate thin existing notes from missing notes:** structural holes cover missing nodes; propose candidates as a ranked list for user selection without auto-generating stubs.

## § Cross-Domain Isomorphism Verification Gate

Cross-domain "same skeleton" claims require strict verification:
1. **Part-by-part structure mapping (Gentner 1983):** map specific relational roles across both domains and state where the mapping breaks. Shared buzzwords ("both have feedback") are rejected or demoted to loose analogy.
2. **Primary-source support (`lj-evidence`):** verify that cited works actually support the claimed mechanism (`existence ≠ support`).
3. **Explicit epistemic labels:** `grounded` requires a named mechanism backed by a checked source; `^[inferred]` marks an unverified structural hypothesis; `⚠待核` marks unchecked or unreachable sources. Validate saved weave reports with `scripts/validate_weave.py`.
