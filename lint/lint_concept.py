"""Lint a lj-concept output page (legacy wiki/concepts/<slug>.md OR D:/hub/20_wiki/notes/<slug>.md).

Hard gates (FAIL):
  Legacy wiki-knowledge format (type: concept without Hub privacy/provenance fields):
    - YAML frontmatter with title / type / status
    - every '## Key Claims' bullet carries a provenance marker
    - no unfilled template tell-tale

  D:/hub/20_wiki clean-room Zettelkasten format (type: zettel, or Hub provenance/privacy keys present):
    - YAML frontmatter with title / type / provenance / privacy
    - provenance in {ai-draft, source, meeting, juan-confirmed}
    - privacy in {private, lab-internal, public-candidate, published}
    - provenance == juan-confirmed REQUIRES non-empty human text in '## 我的判断 (My Take)'
      (catches empty-note fake-provenance templates)
    - privacy in {private, lab-internal} FORBIDS a public publish_target (must be empty or 'none')
    - no unfilled template tell-tale

Advisory (WARN): lean budget, falsifier presence, debunked defaults asserted in claims.
"""
import os
import re

from checks import Finding, FAIL, WARN, section, bullets, count_headers, first_match

PROV = re.compile(r"\^\[extracted|\^\[inferred|\^\[own-result|\([A-Z][A-Za-z.&'\- ]+\s+\d{4}[a-z]?\)")

HUB_PROVENANCE = {"ai-draft", "source", "meeting", "juan-confirmed"}
HUB_PRIVACY = {"private", "lab-internal", "public-candidate", "published"}

TEMPLATE_TELLS = [
    r"\bTODO\b", r"\bFIXME\b", r"\bPLACEHOLDER\b", r"\bXXX\b", r"lorem ipsum",
    r"\{slug\}", r"<slug>", r"<source-id>", r"<Concept Name>", r"<related-slug>",
    r"<one-line relation>", r"<the [a-z]", r"<one [a-z]", r"<Author Year>",
]

DEBUNKED_IN_CLAIMS = [
    r"balance of nature",
    r"more diversity\s+(?:always|automatically|means)\b.*stab",
    r"carrying capacity\b.*\b(?:is|=)\b.*\b(?:fixed|measurable|constant)\b",
    r"proceeds to a (?:single )?stable climax",
]


def _frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    return m.group(1) if m else None


def _fm_val(fm, key):
    m = re.search(rf"^{key}\s*:\s*([^\r\n#]+)", fm, re.M)
    if not m:
        return None
    return m.group(1).strip().strip("'\"")


def _strip_html_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()


def lint_concept(path, force_hub=False):
    out = []
    name = os.path.basename(path)
    norm_path = os.path.abspath(path).replace("\\", "/").lower()
    in_hub_wiki = force_hub or "/20_wiki/" in norm_path
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    fm = _frontmatter(text)
    if fm is None:
        out.append(Finding(FAIL, "concept.frontmatter", name, "missing YAML frontmatter block"))
        is_hub = in_hub_wiki
    else:
        note_type = (_fm_val(fm, "type") or "").lower()
        is_hub = in_hub_wiki or note_type == "zettel" or _fm_val(fm, "privacy") is not None or _fm_val(fm, "provenance") is not None

        if is_hub:
            for k in ("title", "type", "provenance", "privacy"):
                if _fm_val(fm, k) is None:
                    out.append(Finding(FAIL, "concept.hub_frontmatter", name, f"Hub note missing required key '{k}'"))
            prov = _fm_val(fm, "provenance")
            if prov is not None and prov not in HUB_PROVENANCE:
                out.append(Finding(FAIL, "concept.hub_provenance", name, f"invalid provenance '{prov}'"))
            priv = _fm_val(fm, "privacy")
            if priv is not None and priv not in HUB_PRIVACY:
                out.append(Finding(FAIL, "concept.hub_privacy", name, f"invalid privacy '{priv}'"))

            my_take = _strip_html_comments(section(text, r"我的判断|My Take"))
            if prov == "juan-confirmed" and not my_take:
                out.append(Finding(
                    FAIL,
                    "concept.fake_confirmed",
                    name,
                    "provenance is 'juan-confirmed' but '## 我的判断 (My Take)' has no human-written content",
                ))

            pub = (_fm_val(fm, "publish_target") or "").lower()
            if priv in {"private", "lab-internal"} and pub not in {"", "none"}:
                out.append(Finding(
                    FAIL,
                    "concept.privacy_leak",
                    name,
                    f"privacy '{priv}' cannot declare public publish_target '{pub}'",
                ))
        else:
            for k in ("title", "type", "status"):
                if not re.search(rf"^{k}\s*:", fm, re.M):
                    out.append(Finding(FAIL, "concept.frontmatter", name, f"frontmatter missing required key '{k}'"))

    if not is_hub:
        kc = section(text, r"Key Claims")
        if kc.strip():
            for b in bullets(kc):
                if not PROV.search(b):
                    snippet = re.sub(r"\s+", " ", b)[:64]
                    out.append(Finding(FAIL, "concept.provenance", name, f"Key-Claims bullet has no provenance marker: {snippet}…"))
        else:
            out.append(Finding(FAIL, "concept.keyclaims", name, "managed page has no '## Key Claims' section"))
        claims_text = kc
    else:
        claims_text = "\n".join(
            section(text, pat)
            for pat in (r"AI 概念切片", r"Key Claims", r"我的判断|My Take", r"判据", r"机制", r"辨析", r"证据", r"争议")
        )

    _, m = first_match(text, TEMPLATE_TELLS)
    if m:
        out.append(Finding(FAIL, "concept.template", name, f"unfilled template tell: {m.group(0)!r}"))

    n = count_headers(text)
    if n > 10:
        out.append(Finding(WARN, "concept.budget", name, f"{n} '##' sections (> 10 one-screen budget)"))

    for d in DEBUNKED_IN_CLAIMS:
        if re.search(d, claims_text, re.I):
            out.append(Finding(WARN, "concept.exclusions", name, f"claims may assert a debunked default (/{d}/) — confirm it is framed as a misconception, not asserted"))

    asec = section(text, r"Assumptions")
    if asec.strip() and not re.search(r"change my mind|falsif", asec, re.I):
        out.append(Finding(WARN, "concept.falsifier", name, "Assumptions section has no 'what would change my mind' falsifier"))

    return out


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        for f in lint_concept(p):
            print(f)
