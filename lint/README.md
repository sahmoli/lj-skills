# lj-skills check harness

A small, **offline, stdlib-only** (PyYAML used if installed) gate that machine-verifies the
*honesty scaffolding* of the suite. It does not need installing and downloads nothing.

Borrowed (ideas only, 2026-06-23) from the brycewang-stanford
`Auto-Empirical-Research-Skills` eval-harness (CC BY-SA 4.0) and `Awesome-Journal-Skills`
maintenance stack (MIT) — **reimplemented from scratch; no code copied**. See
[[wiki/queries/2026-06-23-skill-suite-borrow-scan-awesome-journal-skills]] (golden mine B).

## Run

```
make check      # structure/routing/content lint + behavioral validators; FAILs + a WARN count
make audit      # also lists every WARN and ranks the re-verify worklist
make selftest   # guardrail regression + test-your-test only (fast)
make test       # the same self-tests as python -m unittest
make hook       # install the pre-commit hook into .git/hooks
```

`run_checks.py --concepts <dir>` overrides where concept pages are read
(default `~/wiki-knowledge/wiki/concepts`).

## Five gates

1. **Skill structure** — every installable `lj-*` directory must contain a valid `SKILL.md`,
   its frontmatter name must equal the folder name, only supported frontmatter keys are allowed,
   referenced local resources must exist, and every skill must ship `agents/openai.yaml` whose
   default prompt explicitly invokes that skill. Repo-external optional capabilities must be declared
   in `evals/external-dependencies.json` with consumers and an honest fallback.
2. **Routing contracts** — `evals/routing-cases.json` must cover every installable skill with at
   least two positive, two negative, and one ambiguous case. This is deterministic inventory
   coverage, not a claim that a model will route every prompt correctly.
3. **Legacy phrase audit (advisory)** — reports missing historical “soul phrases” during migration but
   never blocks a refactor. Substring presence is not evidence that a behavior is implemented. Behavior
   fixtures, artifact validators, and source/data lint are the blocking checks.
4. **Test-your-test + artifact validators** — the linters must FAIL `tests/fixtures/bad_*`
   and PASS `tests/fixtures/good_*`; representative artifact validators run paired positive and
   negative cases. `make check` executes this behavior suite, not only the prose/structure lint.
5. **Content lint** — every journal card and every page explicitly listed as managed in
   `lint/concept_pages.txt`, in two tiers. Legacy pages not yet meeting the contract stay visible in
   `lint/concept_migration_backlog.txt`; they are not misreported as managed/green.
   - **FAIL (blocks)**: concept frontmatter keys, a Key-Claims bullet with no provenance
     marker, an un-filled template tell; journal unknown-schema-key, slug≠filename,
     template tell, YAML parse error.
   - **WARN (advisory)**: lean budget (>10 sections), missing falsifier, a debunked
     default possibly asserted in Key Claims; journal `source_url`/`last_verified` gaps and
     the ⚠VERIFY-LIVE / unknown-confidence re-verify backlog (ranked under `--strict`).

## NECESSARY, NOT SUFFICIENT

A green gate means the honesty scaffolding is intact — **it does not certify the facts are
correct.** It does NOT check that a cited source actually supports its claim, that a number
is right, or that `my_notes` is genuinely first-hand (none of which is machine-checkable
from the file alone). Those still need the source text or Juan.

## Layout

```
lint/   checks.py  lint_concept.py  lint_journal.py  lint_skills.py  run_checks.py  README.md
evals/  routing-cases.json
tests/  test_suite.py  fixtures/{good,bad}_*
hooks/  pre-commit
Makefile
```
