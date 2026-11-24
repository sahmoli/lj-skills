# Unified Markdown Note Output

When completing a substantive LJ skill task without an explicit file destination, save the deliverable as a UTF-8 Markdown note and report the saved path. Explicit output paths and read-only / no-save instructions always take precedence.

## Location

- Environment override: `$LJ_NOTES_DIR` (if set, takes priority on all platforms).
- Portable default: `~/Documents/lj-notes/` across Windows, macOS, and Linux (configured in [`note-settings.json`](note-settings.json)).
- Keep notes flat in this directory, indexed by Denote-style filename tags rather than per-skill or per-month subfolders.
- If the configured drive or directory is unavailable, report the error and deliver the body in chat without silently writing elsewhere or claiming the note was saved.

## Filename & Frontmatter

Denote-style pattern: `{YYYYMMDDTHHMMSS}--{short-title}__{tag}.md` (local ISO-8601 timestamp, tag = skill name without `lj-`).

Example: `20261020T153000--camera-records-vs-recovery__question.md`

Minimum YAML frontmatter:

```yaml
---
title: "Camera records vs population recovery"
date: "2026-10-20T15:30:00+08:00"
tags: ["question"]
identifier: "20261020T153000"
skill: "lj-question"
---
```

Sanitize filesystem-unsafe characters and avoid `--` or `__` inside `{short-title}`. Never overwrite an existing note on same-second collision.

## Helper Script

Use stdlib-only [`save_note.py`](save_note.py) on a headerless Markdown body:

```bash
python <skills-root>/_shared/save_note.py --skill lj-question --title "Short Title" --input body.md
```

Pass `--source` (repeatable) for verified sources, `--metadata-json` for extra schema fields, and `--dest` for explicit target directories. Saving a note never auto-promotes to personal Wiki/Mem or triggers git commits/pushes.

*Naming acknowledgement*: Denote-style filename convention adapted from Denote / `ljg-think` Markdown conventions; scientific workflows and epistemic rules belong to `lj-skills`.
