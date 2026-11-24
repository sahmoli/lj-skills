"""Lint a lj-journal card (journals/<slug>.yaml).

Hard gate (FAIL):
  - top-level keys are a subset of the schema allowlist (catches a typo'd key that
    silently does nothing)
  - slug == filename stem
  - no un-filled template tell-tale
  - YAML parses

Advisory (WARN):
  - graduated provenance: an official/secondary fact with a value should carry a
    source_url and a last_verified date
  - re-verify backlog: count of ⚠VERIFY-LIVE / 待核实 / 403 markers + unknown-confidence
    facts (the runner ranks cards by this to make the next verification batch self-selecting)

source_url-missing is WARN, not FAIL, so a hand-curated suite is never blocked from
committing; the advisory lane surfaces the honesty debt.
"""
import os
import re

from checks import Finding, FAIL, WARN, first_match

try:
    import yaml
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False

ALLOWED_TOP = {
    "slug", "journal", "publisher", "doi_prefixes", "society", "metrics", "open_access",
    "apc_usd", "review_model", "scope", "taste", "caps", "desk_reject_triggers", "reporting",
    "ai_disclosure", "submission", "my_notes", "artwork",
}

# Publisher-profile keys live in journals/../publisher_profiles.yaml, not journal cards.
# reviewer_ai_policy is the optional referee-mode field added by J001-WP1.
ALLOWED_PUBLISHER_KEYS = {
    "ai_disclosure", "review_model_default", "portal_family", "inherits",
    "review_model_note", "review_model_source_url", "review_model_confidence",
    "review_model_last_verified", "note", "reviewer_ai_policy",
}

VERIFY_MARKERS = [r"VERIFY[ _-]?LIVE", r"待核实", r"\b403\b", r"\bblocked\b",
                  r"fetch_separately", r"js-rendered", r"\blogin required\b"]

TEMPLATE_TELLS = [r"\bTODO\b", r"\bFIXME\b", r"\bPLACEHOLDER\b",
                  r"<kebab-case-id>", r"<display name>", r"<Article Type>", r"<one-paragraph",
                  r"</[a-z_]+>", r"<parameter\b"]


def _empty(v):
    return v is None or (isinstance(v, str) and not v.strip()) or v == [] or v == {}


def _is_leaf(d):
    return isinstance(d, dict) and "value" in d and "confidence" in d


def _walk(node, path=""):
    if _is_leaf(node):
        yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def lint_journal(path):
    out = []
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()

    _, m = first_match(raw, TEMPLATE_TELLS)
    if m:
        out.append(Finding(FAIL, "journal.template", name, f"unfilled template tell: {m.group(0)!r}"))

    if not HAVE_YAML:
        out.append(Finding(WARN, "journal.yaml", name, "PyYAML unavailable — schema/provenance checks skipped"))
        return out

    try:
        data = yaml.safe_load(raw)
    except Exception as e:
        out.append(Finding(FAIL, "journal.parse", name, f"YAML parse error: {e}"))
        return out
    if not isinstance(data, dict):
        out.append(Finding(FAIL, "journal.parse", name, "card is not a YAML mapping"))
        return out

    for k in data:
        if k not in ALLOWED_TOP:
            out.append(Finding(FAIL, "journal.schema", name, f"unknown top-level key '{k}' (not in schema allowlist)"))

    stem = os.path.splitext(name)[0]
    if data.get("slug") != stem:
        out.append(Finding(FAIL, "journal.slug", name, f"slug {data.get('slug')!r} != filename {stem!r}"))

    # Validate nested caps mapping by article type (prevent scalar `caps: 5000` schema bypass)
    if "caps" in data and data["caps"] is not None:
        if not isinstance(data["caps"], dict) or _is_leaf(data["caps"]):
            out.append(Finding(FAIL, "journal.caps_shape", name, "caps must be a mapping keyed by article type"))
        else:
            for art_type, cap_entry in data["caps"].items():
                if not isinstance(cap_entry, dict):
                    out.append(Finding(FAIL, "journal.caps_shape", name, f"caps.{art_type} must be a mapping of limit fields"))

    allowed_conf = {"official", "secondary", "inferred", "unknown"}
    backlog = 0
    for p, leaf in _walk(data):
        conf, val = leaf.get("confidence"), leaf.get("value")
        if conf not in allowed_conf:
            out.append(Finding(FAIL, "journal.confidence_enum", name, f"{p}: invalid confidence={conf!r}"))
        if conf in ("official", "secondary") and not _empty(val):
            if _empty(leaf.get("source_url")):
                out.append(Finding(WARN, "journal.provenance", name, f"{p}: confidence={conf} but no source_url"))
            if _empty(leaf.get("last_verified")):
                out.append(Finding(WARN, "journal.last_verified", name, f"{p}: {conf} fact has no last_verified"))
        source = str(leaf.get("source_url", "")).lower()
        if conf == "official" and any(domain in source for domain in (
            "openalex.org", "bioxbio.com", "resurchify.com", "manusights.com"
        )):
            out.append(Finding(FAIL, "journal.confidence", name,
                               f"{p}: aggregator source cannot have confidence=official"))
        if conf == "unknown" and not _empty(val):
            backlog += 1

    markers = sum(len(re.findall(m, raw)) for m in VERIFY_MARKERS)
    if markers or backlog:
        out.append(Finding(WARN, "journal.verify_backlog", name,
                           f"re-verify queue: {markers} live-check markers + {backlog} unknown-confidence facts"))
    return out


if __name__ == "__main__":
    import sys
    failed = False
    for p in sys.argv[1:]:
        for f in lint_journal(p):
            print(f)
            if f.severity == FAIL:
                failed = True
    raise SystemExit(1 if failed else 0)
