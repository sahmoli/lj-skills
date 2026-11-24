# Kami provenance

Kami is an optional minimal slide-layout inspiration for `lj-talk`; it is not a required runtime dependency or a scientific-content authority.

## Recorded source

- Upstream: [tw93/kami](https://github.com/tw93/kami), commit `4dab24cc4c527dbb35aa8fae09e02822992dfbe2` (inspected 2026-09-11).
- Upstream files reviewed: `LICENSE`, `README.md`, `skills/kami/SKILL.md`, `skills/kami/assets/templates/slides.py`, and slide design references.
- License: MIT, copyright 2026 Tw93. Retain its copyright and MIT notice with any copied or adapted upstream code. `lj-talk` records provenance only and includes no copied Kami source code.

## Usage boundary

Extract only generic reusable typography and spacing tokens (e.g., serif display + monospace metadata + clean CJK sans-serif fallbacks) when no project/course reference deck is supplied; existing user or course reference decks always take precedence.

Do not run external update checks, font installers, MCP setup, or network-backed renderers as part of `lj-talk`. If future work borrows upstream code rather than general layout ideas, include the upstream MIT notice alongside the borrowed file and record the exact commit.
