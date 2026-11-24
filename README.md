# lj-skills

Epistemically grounded AI agent skills and composable research workflows for scientists — built across ecology, conservation biology, and interdisciplinary scholarship, compatible with **Google Antigravity**, **OpenAI Codex**, and **Anthropic Claude Code**.

Unlike broad tool catalogs that bundle hundreds of generic API wrappers, `lj-skills` focuses on **scientific reasoning integrity and deterministic verification**: separating pattern from process, locking 30-second discriminating questions before study design, checking retractions and physical PDF page anchors (`<!-- pdf-p0001 -->`) before citing, catching numeric/citation drift in manuscript edits, and auditing publication figures at print dimensions.

---

## Architecture: 12 Atomic Skills + 3 Composable Workflows

### 1. Core Research Cycle (`--profile core` · 7 Skills)

| Skill | Deliverable & Core Guardrail | Deterministic Scripts |
|---|---|---|
| [`lj-question`](lj-question/SKILL.md) | Develop, compare, or diagnose research questions (`Explore` / `Select` / `Explain` / `Constraints`) with a 30-second elevator & anti-defensive scope gate. | `validate_pool.py`, `validate_dig.py`, `validate_constraint.py` |
| [`lj-evidence`](lj-evidence/SKILL.md) | Multi-database discovery & citation snowballing, repository-first legal OA full-text retrieval, three-state PDF semantic verification, local PDF ingestion, page-anchored Markdown, and retraction/integrity checks. | `discover_sources.py`, `fetch_oa.py`, `verify_pdf.py`, `ingest_local.py`, `pdf_to_md.py`, `search_local_corpus.py`, `resolve_citation.py` |
| [`lj-read`](lj-read/SKILL.md) | Deep-read papers or books from primary originals with explicit artifact/SI inventories, denominator checks, and `confirmed` vs `inferred` lineage. | `validate_companion.py`, `validate_note.py` |
| [`lj-design`](lj-design/SKILL.md) | Design minimum-sufficient discriminating studies (`H` vs strongest `H_alt`, falsifier, unit-mismatch screen, and 30-minute feasibility probes). | `validate_output.py` |
| [`lj-review`](lj-review/SKILL.md) | Fact-first manuscript self-review, confidentiality-gated referee review, and comment-to-plan parity response planning. | `validate_report.py` |
| [`lj-write`](lj-write/SKILL.md) | Render supplied science faithfully into manuscript sections, captions, and reviewer replies without altering claims or inventing caveats. | `check_drift.py` |
| [`lj-viz`](lj-viz/SKILL.md) | Design, build, and preflight-audit journal static/multi-panel figures (`medium: paper`, print geometry, colour-vision accessibility, species silhouettes). | `preflight_figure.py`, `craft_metrics.py`, `audit_palette.py`, `audit_layout.py`, +10 more |

### 2. Specialist Extensions (`--profile full` or `--optional <name>` · 5 Skills)

| Skill | Deliverable & Core Guardrail |
|---|---|
| [`lj-concept`](lj-concept/SKILL.md) | Dissect a single concept or principle across disciplines (proposition type, confusable twin, computed thought experiment, breakdown boundary, transfer drills). |
| [`lj-backbone`](lj-backbone/SKILL.md) | Map a field's foundational commitments, principles, core results, and typed derivations without forcing false deductive closure. |
| [`lj-journal`](lj-journal/SKILL.md) | Assess venue fit, run journal-led cross-disciplinary scans, and verify official article-type submission caps with dated provenance. |
| [`lj-annotate`](lj-annotate/SKILL.md) | Build and Playwright-audit offline, single-record HTML workbenches for assisted or blind human coding (`selftest.py`, `browser_qa.sh`). |
| [`lj-talk`](lj-talk/SKILL.md) | Plan, build, and visually verify editable `.pptx` research talks and teaching slide decks (`deck.py`, `render_deck.py`). |

### 3. Composable Workflow Playbooks ([`workflows/`](workflows/))

Explicit 1-page stage-gated playbooks (invoked on demand so they never bloat everyday context or fight atomic skill routing):
1. **[`01-idea-pilot-proposal.md`](workflows/01-idea-pilot-proposal.md)** — *Spark → Full-Text Precedent Check → Lock 30s Question → 30-Minute Data/Sample Feasibility Probe → Minimum-Sufficient Proposal*.
2. **[`02-draft-review-manuscript.md`](workflows/02-draft-review-manuscript.md)** — *Fact-First Audit → Citation & Figure Verification → Human Disposition Lock → Drift-Checked Revision & Replies*.
3. **[`03-read-to-note-or-chapter.md`](workflows/03-read-to-note-or-chapter.md)** — *Primary Full-Text Reconstruction → Human `My Take` Gate → Book Chapter, Slide Deck, or Visual Note Brief*.

---

## 2-Minute Quickstart

```bash
# 1. Install the 7 core research skills (or --profile full for all 12)
./install.sh copy --profile core --dest ~/.claude/skills
./install.sh copy --profile full --dest ~/.codex/skills
# Cross-platform / Windows PowerShell:
python scripts/install_skills.py copy --profile core --dest "$HOME/.codex/skills"

# 2. Configure your academic email & private local papers folder (optional, recommended for lj-evidence)
export UNPAYWALL_EMAIL="your.name@university.edu"
export LJ_PAPERS_DIR="$HOME/Documents/papers"
export LJ_NOTES_DIR="$HOME/Documents/lj-notes"

# 3. Discover papers, fetch verified legal OA PDFs, and convert to page-anchored Markdown
python3 lj-evidence/scripts/discover_sources.py --query "behavioral plasticity population collapse" --year-from 2022 --out discovery.json
python3 lj-evidence/scripts/fetch_oa.py --doi "10.1371/journal.pone.0169725" --convert
python3 lj-evidence/scripts/search_local_corpus.py --query "conservation"
```

> *Note for PDF verification & conversion*: `verify_pdf.py` and `pdf_to_md.py` use `pymupdf` (and optionally `docling` for dense tables/scans) inside your local Python 3.11+ virtual environment. All bibliographic discovery, citation resolution, and local Markdown search scripts run on **zero third-party dependencies (Python stdlib only)**.

---

## Non-Goals & Epistemic Boundaries

Shared scientific honesty, confidentiality, and authorization rules live in [`_shared/honesty-constitution.md`](_shared/honesty-constitution.md):
- **No paywall or anti-bot bypasses:** `lj-evidence` queries only legal open-access repositories and official APIs (arXiv, Europe PMC, OpenAIRE, Unpaywall, OpenAlex, Semantic Scholar, Crossref). Never automates Sci-Hub, shadow libraries, or CAPTCHA/WAF circumvention; OA download for personal research does not grant public redistribution rights.
- **No black-box guarantees:** Validators certify mechanical contracts, citation existence, retraction signals, and page-anchor presence — never scientific truth. Always visually confirm critical numbers, denominators, and figures on the original PDF page (`fetched ≠ converted ≠ verified`).
- **Confidentiality:** Never send unpublished third-party peer-review manuscripts or grant proposals to unapproved external services; grant review remains strictly out of scope.

---

## Validation

```bash
python3 -m pip install -r requirements-test.txt -r lj-talk/requirements-deck.txt
PYTHONUTF8=1 python3 lint/run_checks.py --selftest-only
PYTHONUTF8=1 python3 -m unittest discover -s tests
```

---

## License & Citation

- **Code (`scripts/`, `lint/`, `tests/`, `_shared/*.py`, `install.sh`)**: [MIT License](LICENSES/MIT.txt)
- **Skill Prompts, References, Workflows & Metadata (`SKILL.md`, `references/`, `_shared/*.md`, `workflows/`, `templates/`, `config/`, `lj-journal/journals/`)**: [Creative Commons Attribution 4.0 International (`CC BY 4.0`)](LICENSES/CC-BY-4.0.txt)
- **Third-Party Assets & Runtime Notices**: [`THIRD_PARTY.md`](THIRD_PARTY.md)
- **Academic Citation**: See [`CITATION.cff`](CITATION.cff) or visit [juanli.me/resources/skills/](https://juanli.me/resources/skills/).
