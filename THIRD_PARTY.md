# Third-Party Notices & External Dependencies

`lj-skills` keeps third-party attributions and runtime dependency boundaries explicit:

## 1. Bundled Assets
- **Snow Leopard Silhouette (`lj-viz/assets/silhouettes/panthera-uncia__phylopic-cb44ff49.svg`)**
  - Creator: Margot Michaud (via [PhyloPic](https://www.phylopic.org/images/cb44ff49-165e-4c97-9a94-98f512dda64f/panthera-uncia))
  - License: **CC0 1.0 Universal (Public Domain Dedication)**
  - Metadata & registry: `lj-viz/assets/silhouettes/registry.yaml`

## 2. Methodological & Design Acknowledgements (No Upstream Source Code Bundled)
- **Kami Slide Inspiration (`lj-talk/references/kami-provenance.md`)**: acknowledges layout inspiration from [`tw93/kami`](https://github.com/tw93/kami) (MIT License, Copyright 2026 Tw93); no Kami code is bundled.
- **Denote Filename Convention (`_shared/note-output.md`)**: acknowledges Protesilaos Stavrou's Denote naming scheme (`YYYYMMDDTHHMMSS--title__tags`) and `ljg-think` Markdown note naming conventions.
- **Scholarly Literature Citations**: methodological anchors cited in `references/*.md` (e.g., Platt 1964, Tinbergen 1963, Gould & Lewontin 1979, Gentner 1983, Keshav 2007, Alon 2009, Uzzi et al. 2013) are standard academic citations.

## 3. Optional External Runtime Packages (Installed Separately by the User; Never Vendored)
- **`PyMuPDF` (`pymupdf`)** — used optionally in an isolated user virtual environment by `lj-evidence/scripts/verify_pdf.py`, `pdf_to_md.py`, and `lj-viz` preflight scripts. Licensed upstream by Artifex under **GNU AGPL-3.0** (or commercial license); `lj-skills` does not bundle or redistribute PyMuPDF.
- **`Docling` (`docling`)** — optional high-fidelity table/equation/OCR parser invoked on demand via `pdf_to_md.py --engine docling`. Licensed upstream by IBM / LF AI & Data under **MIT License**.
- **`python-pptx`, `matplotlib`, `Pillow`, `PyYAML`** — standard open-source Python packages (MIT / PSF / HPND) installed by the user when running figure, deck, or test suites.
- **Node.js & Playwright (`playwright`)** — optional browser automation runtime used by `lj-annotate/scripts/browser_qa.sh` for geometry and fail-closed export verification (Apache-2.0).
- **LibreOffice / Poppler (`soffice`, `pdftoppm`)** — optional system tools used when visually rendering `.pptx` slide decks in `lj-talk`.
