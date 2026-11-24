#!/usr/bin/env python3
"""lj skill-suite check runner — stdlib + (optional) PyYAML, offline.

Runs three gates, in order, and exits non-zero if any FAILs:
  1. legacy phrase audit  — advisory migration signal only; behavior fixtures are the gate
  2. test-your-test        — the bad fixtures MUST fail and the good fixtures MUST pass
                             (proves the linters are not vacuously green)
  3. content lint          — every journal card + every concept page, two-tier

Usage:
  python3 lint/run_checks.py                 # FAILs + a one-line WARN summary
  python3 lint/run_checks.py --strict        # also print every WARN + the re-verify ranking
  python3 lint/run_checks.py --selftest-only # gates 1+2 only (fast pre-commit on skill edits)
  python3 lint/run_checks.py --concepts DIR  # override the concept-pages directory

NECESSARY, NOT SUFFICIENT. A green run means: no debunked default is asserted in a
Key-Claims bullet, every claim carries a provenance marker, the schema is intact, and the
skills still state their own guardrails. It does NOT verify that a cited source actually
supports the claim, that a number is correct, or that my_notes is genuinely first-hand —
those need the source text or Juan. See lint/README.md.
"""
import glob
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from checks import FAIL, WARN, Finding  # noqa: E402
from lint_concept import lint_concept   # noqa: E402
from lint_journal import lint_journal   # noqa: E402
from lint_skills import validate_routing_contracts, validate_skills  # noqa: E402

DEFAULT_CONCEPTS = os.environ.get("LJ_WIKI_NOTES_DIR", "D:/hub/20_wiki/notes")
FIXTURES = os.path.join(SUITE, "tests", "fixtures")

# Advisory phrase audit across the 12 active public skills. Missing phrases emit WARN only;
# structural checks, routing contracts, and behavior fixtures remain the blocking gate.
GUARDRAILS = {
    "lj-question/SKILL.md": [
        "Explore", "Select", "Explain", "Constraints",
        "roam-engine.md", "question-engine.md", "dig-engine.md", "constraint-lenses.md",
        "precedent check",
    ],
    "lj-evidence/SKILL.md": [
        "Build", "Fulltext", "Verify",
        "fetch_oa.py", "pdf_to_md.py", "resolve_citation.py",
        "Metadata establishes identity, not claim support",
        "Never automate Sci-Hub or bypass paywalls",
        "OA access does not grant public redistribution",
    ],
    "lj-design/SKILL.md": [
        "estimand", "competing predictions", "falsifier", "decisive contrast",
        "design-engine.md", "Do not invent sample size",
    ],
    "lj-review/SKILL.md": [
        "distinguish defects from preferences", "smallest honest repair",
        "lj-evidence", "lj-write",
        "Grant-review material remains out of scope", "validate_report.py",
    ],
    "lj-write/SKILL.md": [
        "Render the supplied science faithfully", "prose-engine.md",
        "content gap", "citation attachment", "Do not fill gaps with new analyses",
    ],
    "lj-viz/SKILL.md": [
        "Medium & Palette Scope Guard", "medium: paper",
        "Do not invent data", "Inspect the actual render at its intended size",
        "validate_manifest.py", "preflight_figure.py",
    ],
    "lj-concept/SKILL.md": [
        "define / distinguish / predict / intervene",
        "exclusions.md", "domain-ecology.md",
        "⚠待核", "references/weave-engine.md",
    ],
    "lj-talk/SKILL.md": [
        "Medium Scope Guard", "editable `.pptx`",
        "engineplan", "teaching-handoff.md", "deck-acceptance.md",
        "Preserve scientific claims",
    ],
    "lj-read/SKILL.md": [
        "partial coverage", "paper-engine.md", "coverage-map.md",
        "x → f → f(x)",
        "validate_companion.py", "validate_note.py",
    ],
    "lj-journal/SKILL.md": [
        "my_notes", "⚠待核", "landscape-workflow.md", "biodiversity-entry-map.md",
        "Do not predict acceptance", "Do not mix JIF",
    ],
    "lj-annotate/SKILL.md": [
        "An untouched answer is not a negative answer", "offline and self-contained",
        "human-review state", "fail closed", "Never reduce human confirmation",
        "interface-contract.md",
    ],
    "lj-backbone/SKILL.md": [
        "backbone-engine.md", "counterexample search finds errors",
        "never write an unchecked DOI", "Keep the field's real disagreements visible",
    ],
}


def guardrail_regression():
    out = []
    for rel, phrases in GUARDRAILS.items():
        path = os.path.join(SUITE, rel)
        if not os.path.exists(path):
            out.append(Finding(FAIL, "guardrail.missing", rel, "SKILL.md not found"))
            continue
        with open(path, encoding="utf-8") as fh:
            low = fh.read().lower()
        for ph in phrases:
            if ph.lower() not in low:
                out.append(Finding(WARN, "guardrail.legacy_phrase", rel, f"legacy phrase absent: {ph!r}"))
    # inventory tripwire: every on-disk skill must have a GUARDRAILS entry, so a new skill
    # can't be added without declaring its soul phrases (caught at pre-commit). Empty diff today.
    on_disk = {os.path.relpath(p, SUITE).replace("\\", "/") for p in glob.glob(os.path.join(SUITE, "lj-*", "SKILL.md"))}
    for rel in sorted(on_disk - set(GUARDRAILS)):
        out.append(Finding(WARN, "guardrail.uncovered", rel, "on-disk skill has no legacy phrase audit entry"))
    return out


def test_your_test():
    """The linters must FAIL the bad fixtures and PASS the good ones."""
    out = []
    cases = [
        ("bad_concept.md", lint_concept, True),
        ("good_concept.md", lint_concept, False),
        ("bad_journal.yaml", lint_journal, True),
        ("good_journal.yaml", lint_journal, False),
    ]
    for fn, linter, should_fail in cases:
        p = os.path.join(FIXTURES, fn)
        if not os.path.exists(p):
            out.append(Finding(FAIL, "selftest.missing", fn, "fixture not found"))
            continue
        fails = [f for f in linter(p) if f.severity == FAIL]
        if should_fail and not fails:
            out.append(Finding(FAIL, "selftest.vacuous", fn, "BAD fixture produced no FAIL — the linter is not discriminating"))
        if (not should_fail) and fails:
            out.append(Finding(FAIL, "selftest.falsepos", fn, f"GOOD fixture wrongly FAILed: {fails[0].msg}"))
    return out


def _managed_concept_slugs():
    """Slugs lj-concept governs (lint/concept_pages.txt). The wiki concepts/ dir also
    holds many non-lj pages with other conventions — those are out of this skill's scope."""
    f = os.path.join(HERE, "concept_pages.txt")
    if not os.path.exists(f):
        return []
    with open(f, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def lint_content(concepts_dir):
    out = []
    for card in sorted(glob.glob(os.path.join(SUITE, "lj-journal", "journals", "*.yaml"))):
        if os.path.basename(card) == "_schema.yaml":
            continue
        out.extend(lint_journal(card))
    listed = _managed_concept_slugs()
    if not listed:
        out.append(Finding(WARN, "content.concepts", "lint/concept_pages.txt", "no managed concept pages listed"))
    elif not os.path.isdir(concepts_dir):
        out.append(Finding(WARN, "content.concepts.skipped", concepts_dir, "SKIPPED: concepts dir not found — concept page lint did NOT run"))
    else:
        for slug in listed:
            p = os.path.join(concepts_dir, slug + ".md")
            if os.path.exists(p):
                out.extend(lint_concept(p))
            else:
                out.append(Finding(WARN, "content.concepts", slug, "managed concept page not found in concepts dir"))
    return out


def main(argv):
    strict = "--strict" in argv
    selftest_only = "--selftest-only" in argv
    concepts_dir = DEFAULT_CONCEPTS
    if "--concepts" in argv:
        concepts_dir = argv[argv.index("--concepts") + 1]

    findings = []
    findings += validate_skills(SUITE)
    findings += validate_routing_contracts(SUITE)
    findings += guardrail_regression()
    findings += test_your_test()
    if not selftest_only:
        findings += lint_content(concepts_dir)

    fails = [f for f in findings if f.severity == FAIL]
    warns = [f for f in findings if f.severity == WARN]

    if fails:
        print("FAIL gate (blocking):")
        for f in fails:
            print("  " + str(f))
    else:
        print("FAIL gate: clean ✓")

    if strict:
        print(f"\nWARN advisory ({len(warns)}):")
        for f in sorted(warns, key=lambda x: x.code):
            print("  " + str(f))
        # re-verify ranking: journal cards with the most live-check/unknown debt
        backlog = [f for f in warns if f.code == "journal.verify_backlog"]
        if backlog:
            print("\nRe-verify worklist (cards by honesty debt):")
            for f in backlog:
                print("  " + f.target + " — " + f.msg)
    else:
        print(f"WARN advisory: {len(warns)} (run with --strict to list + rank the re-verify worklist)")

    print("\nNECESSARY-NOT-SUFFICIENT: a green gate does NOT certify the facts are correct,")
    print("only that the honesty scaffolding is intact. See lint/README.md.")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
