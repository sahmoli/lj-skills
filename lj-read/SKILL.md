---
name: lj-read
description: Deep-read a specified paper or book with traceable evidence and coverage.
---

# lj-read

Reconstruct the specified work from accessible primary originals (preferring page-anchored local full texts prepared via `lj-evidence` when available) and complete the supported reading, marking missing sections or supplements explicitly as partial coverage.

- **Paper:** trace the central claim, load-bearing evidence, estimand/repeating unit, hidden assumptions, serious alternatives, uncertainty, and verified citation lineage. For empirical or mechanism claims, state an observation or assumption failure that would weaken them (`falsifier`), or explain why the text cannot establish one. Use [paper guidance](references/paper-engine.md) for deep appraisal; faithful reconstruction precedes critique.
- **Book:** reconstruct the problem, operative framework, and judgment/action it changes (`x → f → f(x)` when faithful, never forced as slogans). Before claiming whole-book coverage, apply [coverage guidance](references/coverage-map.md) across distributed book zones; excerpts support only a `partial` or `hypothesis` companion.

Preserve disagreements, caveats, and scope limits. Strictly separate what the authors claim, what the primary data/proofs show, and your own inference. Never dump AI-generated reading summaries directly into human-authored Wiki notes without explicit user authorization. For saved schema-based companions, run [validate_companion.py](scripts/validate_companion.py) or [validate_note.py](scripts/validate_note.py).

Follow the [suite honesty and authorization rules](../_shared/honesty-constitution.md) and [unified Markdown note contract](../_shared/note-output.md). Explicit output paths and read-only/no-save instructions take precedence.
