# Local Primary-Literature Fulltext Pipeline (`lj-evidence` v2.1)

Shared by `lj-evidence`, `lj-read`, `lj-concept`, and `lj-review` so critical claims are checked against real primary text rather than abstract snippets.

## 1. Configuration, Storage & Isolation Boundary
- **Environment variables (portable across Windows/macOS/Linux)**:
  - `LJ_PAPERS_DIR`: private local papers folder (defaults to `./papers`; e.g., set to `D:\hub\10_raw\papers` in local user env).
  - `UNPAYWALL_EMAIL`: your real academic/contact email for Unpaywall & OpenAlex polite pools (never hardcode placeholder `@example.org` emails; Unpaywall is skipped cleanly if unset).
  - `WILEY_TDM_TOKEN` *(optional)*: official Wiley Text & Data Mining token for authorized institutional/OA Wiley retrieval.
- **File naming & provenance**: `<YYYY>-<firstauthor>-<short-slug>.pdf` + companion `.md` (ASCII `kebab-case`, compatible with `Reading.base` and Obsidian `PDF++`).
- **Provenance ledger**: `$LJ_PAPERS_DIR/_provenance.jsonl` (records only verified PDFs or JATS XML full texts: `slug`, `doi`, `pmcid`, `source_format`, `is_retracted`, `sha256`, `source_url`, `source_api`, `oa_status`, `version`, `license`, `verification`, `fetched_at`).
- **Quarantine folders (never silently filed as verified)**:
  - `_needs_review/`: valid PDFs with uncertain identity (low text layer / scan, possible Correction/Erratum header, or borderline metadata match).
  - `_rejected/`: non-PDFs, truncated downloads (`%%EOF` missing), or clear wrong articles (e.g., publisher media kits).
  - `_pending_match/`: local PDFs with only a fuzzy title match (no exact DOI) awaiting human confirmation.
- **Non-Leak Guard**: Never store downloaded PDFs or extracted Markdown inside public git repositories or web publishing directories. Local OA download does **not** grant license to publicly redistribute full texts or figures.

## 2. Step-by-Step Execution

### Step 1 — Local-First Search (zero network)
```bash
python scripts/search_local_corpus.py --query "comprehension illusion"
```
- Returns exact physical PDF page anchors (`<!-- pdf-p0001 -->` + `[[...pdf#page=N]]`) when a PDF-derived Markdown exists.
- Returns `<!-- jats-sec:... -->` locators (`page: null`, empty `pdf_link`) for JATS XML Markdown — **never fabricates `page=1`**.

### Step 2 — Active Discovery & Citation Snowballing (stdlib-only)
```bash
python scripts/discover_sources.py --query "LLM scientific paper reading" --year-from 2024 --limit 15 --out discovery.json --md-out discovery.md
python scripts/discover_sources.py --seed-doi "10.1038/..." --backward --forward --year-from 2024 --out snowball.json
```

### Step 3 — Repository-First Legal OA Fetch + Semantic Verification
```bash
# Dry-run all unchecked *wanted*.md items in inbox:
python scripts/fetch_oa.py --scan-inbox --dry-run

# Fetch & convert a wanted note (up to 10 papers):
python scripts/fetch_oa.py --wanted-note path/to/wanted.md --limit 10 --convert --wanted-out path/to/remaining-wanted.md

# Single DOI / arXiv ID:
python scripts/fetch_oa.py --doi "10.1002/fee.2597" --convert
python scripts/fetch_oa.py --arxiv "2409.13740" --convert
```
- **Repository-first order (minimizes WAF friction)**: cached PDF revalidation → explicit URL / arXiv → PLOS direct → Europe PMC OA PDF → OpenAIRE Graph v3 OPEN repositories → Unpaywall (`published > accepted > submitted`, repositories prioritized) → OpenAlex → optional `$WILEY_TDM_TOKEN` → Semantic Scholar → Crossref / OA publisher patterns + 1-level `citation_pdf_url` scrape → Europe PMC JATS XML fallback (if PDF unavailable).
- **Three-state semantic verification (`verify_pdf.py`)**: checks `%PDF-`, `≥20 KB`, `%%EOF`, PyMuPDF readability (`≥1` page, allowing 1-page letters), detects low-text scans (`needs-ocr-review`) and `Correction/Erratum/Corrigendum` notices (`possible-correction-notice`), and matches NFKC/de-hyphenated DOI, title tokens, or author+year.
- **Explicit failure taxonomy**: `waf-html`, `paywall-html`, `landing-html`, `no-oa`, `wrong-article`, `needs-review`, `truncated-no-eof`, `network`, `no-doi`.
- Never calls Sci-Hub, shadow libraries, or anti-bot/CAPTCHA bypasses.

### Step 4 — Normal Browser / Zotero Handoff + Safe Local Ingest
For remaining `waf-html` or `paywall-html` papers, open up to 10 DOIs in your normal desktop browser (using university VPN / Zotero Connector), download the PDFs, then harvest safely:
```bash
# Preview matches without touching files:
python scripts/ingest_local.py --from-dir ~/Downloads --scan-inbox --dry-run

# Copy verified exact-DOI matches into $LJ_PAPERS_DIR, convert to MD, log provenance, and check off [x]:
python scripts/ingest_local.py --from-dir ~/Downloads --scan-inbox
```
- Default mode is **read-only copy** (never mutates originals; `--move` is explicitly refused inside `Zotero/storage/`).
- Skips incomplete downloads (`.crdownload`, `.part`, `.tmp`), deduplicates by SHA-256, prevents slug collisions, and atomically checks off `[x]` in `*wanted*.md` **only after** exact DOI match + `verify_pdf.py` pass + `pdf_to_md.py` conversion + `_provenance.jsonl` write all succeed.

### Step 5 — Page-Anchored PDF → Markdown (`pdf_to_md.py`)
```bash
# Fast CPU default (PyMuPDF in isolated venv):
python scripts/pdf_to_md.py --pdf path/to/paper.pdf

# High-fidelity tables / equations / scanned legacy PDFs (MIT-licensed IBM Docling):
python scripts/pdf_to_md.py --pdf path/to/paper.pdf --engine docling --overwrite
```
- Low text density (`<120` chars/page) automatically sets `needs_ocr_check: true` and prints a `--engine docling` hint.
- Treat Markdown strictly as a **search and reading view**. Before finalizing any quantitative claim, denominator, subgroup, or quote, visually confirm the cited page in the original PDF (`fetched ≠ converted ≠ verified`).
