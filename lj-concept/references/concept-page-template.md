# Portable Concept Card & Zettelkasten Link Contract

Use this template only when the user explicitly asks to save a durable concept card into a local note vault or Zettelkasten. Ordinary concept explanations stay in chat (or follow [`_shared/note-output.md`](../../_shared/note-output.md)).

## 1. Clean-Room & Human-Authorship Rules
- **No unsolicited AI dumps:** Never write unapproved AI summaries or placeholder stubs into a personal Wiki/Zettelkasten.
- **Protect human judgment:** Never overwrite or paraphrase human-authored judgment sections (`## My Take` / `## 我的判断 (My Take)`). AI additions belong only in clearly marked draft/notes sections.
- **Honest provenance:** Default to `provenance: ai-draft` and `privacy: private` until the human author explicitly verifies primary sources and confirms their own judgment.

## 2. Portable Concept Card Schema
```markdown
---
id: "zettel-<kebab-slug>"
title: "<Concept Name>"
type: zettel
domain: "<ecology | cognitive-science | statistics | philosophy | ...>"
epistemic_role: "<primary | cross-disciplinary>"
sources: []
provenance: ai-draft   # ai-draft | source | meeting | confirmed
privacy: private       # private | internal | public-candidate | published
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <Concept Name>

> <One-sentence scope-bounded definition>
> <Optional verbatim primary-source quote + DOI / page locator>

## 我的判断 (My Take)
<!-- Human-authored judgment only; AI must never overwrite -->

## 机制与辨析 (Mechanism & Distinctions)
<!-- Criteria, generating mechanism, nearest confusable twin, quantitative metric if applicable -->

## 争议与边界 (Debates & Breakdown Boundaries)
<!-- Strongest opposing view + discriminating condition (estimand, grain, design, or value premise) -->

## 关联 (Mechanistic Links)
<!-- Only genuine mechanistic/argumentative edges: prereq / contrasts / isomorphism (with breakpoint) / challenges -->

## Sources
<!-- Primary / review / book / lead with verification status; never invent DOIs or pages -->
```

## 3. Bottom-Up Link Proposals
When filing a card into an existing vault, propose **1–3 high-signal mechanistic links** (see [weave-engine.md](weave-engine.md)); surface adjacency or shared keywords do not qualify. Propose backlinks for human review rather than batch-editing existing notes automatically.
