#!/usr/bin/env python3
"""Deterministic bibliographic & integrity resolver for lj-evidence.

stdlib-only. Queries Crossref / OpenAlex / PubMed E-utilities / arXiv Atom API.
Adds Axis 1.5 integrity checks: retraction flags (OpenAlex `is_retracted`,
Crossref `update-to` / retraction relations), update/correction signals, and
preprint-to-published resolution.

Network is optional; tests must use --from-cache-only plus recorded cache files.
Crossref and OpenAlex URL shapes preserve exact backward compatibility for cache keys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


CROSSREF = "https://api.crossref.org"
OPENALEX = "https://api.openalex.org"
PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ARXIV = "https://export.arxiv.org/api/query"

ARXIV_ID_RE = re.compile(
    r"(?:arxiv:\s*|10\.48550/arxiv\.|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _cache_key(service: str, url: str) -> str:
    return hashlib.sha256(f"{service}\n{url}".encode()).hexdigest()


def _cache_path(cache_dir: Path, service: str, url: str) -> Path:
    return cache_dir / f"{_cache_key(service, url)}.json"


def _load_cache(cache_dir: Path | None, service: str, url: str):
    if cache_dir is None:
        return None
    path = _cache_path(cache_dir, service, url)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_cache(cache_dir: Path | None, service: str, url: str, payload: dict) -> None:
    if cache_dir is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_path(cache_dir, service, url).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _fetch(url: str, timeout: float = 20.0, expect_xml: bool = False) -> tuple[int | None, dict | str | None, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "lj-evidence/resolve_citation/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code, None, str(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, None, str(exc)
    text = raw.decode("utf-8", errors="replace")
    if expect_xml:
        return status, text, None
    try:
        return status, json.loads(text), None
    except json.JSONDecodeError:
        return status, None, "non-json response"


def query_service(
    service: str,
    url: str,
    cache_dir: Path | None,
    cache_only: bool,
    min_interval: float,
    last_request: list[float],
    expect_xml: bool = False,
) -> dict:
    cached = _load_cache(cache_dir, service, url)
    if cached is not None:
        cached = dict(cached)
        cached["from_cache"] = True
        return cached
    if cache_only:
        return {
            "service": service,
            "url": url,
            "http_status": None,
            "body": None,
            "error": "cache-miss under --from-cache-only",
            "from_cache": False,
        }
    elapsed = time.monotonic() - last_request[0]
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    status, body, error = _fetch(url, expect_xml=expect_xml)
    last_request[0] = time.monotonic()
    payload = {
        "service": service,
        "url": url,
        "http_status": status,
        "body": body,
        "error": error,
        "from_cache": False,
        "fetched_at": _now(),
    }
    _save_cache(cache_dir, service, url, payload)
    return payload


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def extract_arxiv_id(text: str | None) -> str | None:
    if not text:
        return None
    m = ARXIV_ID_RE.search(text)
    if m:
        return m.group(1)
    bare = re.fullmatch(r"\s*(\d{4}\.\d{4,5}(?:v\d+)?)\s*", text)
    return bare.group(1) if bare else None


def _title_from_crossref(item: dict) -> str:
    titles = item.get("title") or []
    return titles[0] if titles else ""


def _authors_from_crossref(item: dict) -> list[str]:
    out = []
    for author in item.get("author") or []:
        family = author.get("family") or ""
        given = author.get("given") or ""
        name = " ".join(part for part in (given, family) if part)
        if name:
            out.append(name)
    return out


def _year_from_crossref(item: dict):
    issued = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
    return issued[0] if issued else None


def _crossref_integrity(item: dict) -> dict:
    is_retracted = False
    signals: list[str] = []
    published_doi: str | None = None
    work_type = (item.get("type") or "").lower()

    for upd in item.get("update-to") or []:
        utype = (upd.get("type") or "").lower()
        ulabel = (upd.get("label") or "").lower()
        target_doi = upd.get("DOI") or ""
        if "retract" in utype or "retract" in ulabel:
            is_retracted = True
            signals.append(f"crossref:update-to:{utype or ulabel}({target_doi})")
        elif utype or ulabel:
            signals.append(f"crossref:update-to:{utype or ulabel}({target_doi})")

    relation = item.get("relation") or {}
    if isinstance(relation, dict):
        for rel_key, entries in relation.items():
            rk = rel_key.lower()
            if not isinstance(entries, list):
                continue
            for entry in entries:
                rid = entry.get("id") or ""
                if "retract" in rk:
                    is_retracted = True
                    signals.append(f"crossref:relation:{rel_key}({rid})")
                elif rk == "is-preprint-of" and rid:
                    published_doi = rid
                    signals.append(f"crossref:preprint-published({rid})")
                elif rk in ("is-updated-by", "has-correction", "has-expression-of-concern"):
                    signals.append(f"crossref:relation:{rel_key}({rid})")

    title_lower = _title_from_crossref(item).lower()
    if title_lower.startswith(("retracted:", "retraction:", "retraction notice")):
        is_retracted = True
        signals.append("crossref:retracted-title-prefix")

    return {
        "is_retracted": is_retracted,
        "work_type": work_type or None,
        "published_doi": published_doi,
        "signals": signals,
    }


def _openalex_integrity(item: dict) -> dict:
    is_retracted = bool(item.get("is_retracted"))
    signals: list[str] = []
    published_doi: str | None = None
    work_type = (item.get("type") or "").lower()

    if is_retracted:
        signals.append("openalex:is_retracted=true")

    primary_doi = (item.get("doi") or "").replace("https://doi.org/", "").strip() or None
    for loc in item.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        ver = (loc.get("version") or "").lower()
        src_type = ((loc.get("source") or {}).get("type") or "").lower()
        loc_doi = (loc.get("doi") or "").replace("https://doi.org/", "").strip() if loc.get("doi") else None
        if work_type == "preprint" and ver == "publishedversion" and src_type == "journal":
            published_doi = loc_doi or primary_doi
            signals.append(f"openalex:preprint-has-published-version({published_doi or 'journal'})")

    return {
        "is_retracted": is_retracted,
        "work_type": work_type or None,
        "published_doi": published_doi,
        "signals": signals,
    }


def _match_from_crossref(item: dict) -> dict:
    integ = _crossref_integrity(item)
    return {
        "service": "crossref",
        "doi": item.get("DOI"),
        "title": _title_from_crossref(item),
        "authors": _authors_from_crossref(item),
        "year": _year_from_crossref(item),
        "venue": (item.get("container-title") or [None])[0],
        "is_retracted": integ["is_retracted"],
        "work_type": integ["work_type"],
        "published_doi": integ["published_doi"],
        "integrity_signals": integ["signals"],
    }


def _match_from_openalex(item: dict) -> dict:
    authors = [auth.get("author", {}).get("display_name") for auth in item.get("authorships") or []]
    integ = _openalex_integrity(item)
    oa = item.get("open_access") or {}
    return {
        "service": "openalex",
        "doi": (item.get("doi") or "").replace("https://doi.org/", "") or None,
        "openalex_id": item.get("id"),
        "title": item.get("title") or item.get("display_name"),
        "authors": [name for name in authors if name],
        "year": item.get("publication_year"),
        "venue": ((item.get("primary_location") or {}).get("source") or {}).get("display_name"),
        "cited_by_count": item.get("cited_by_count"),
        "oa_url": oa.get("oa_url"),
        "is_retracted": integ["is_retracted"],
        "work_type": integ["work_type"],
        "published_doi": integ["published_doi"],
        "integrity_signals": integ["signals"],
    }


def _arxiv_items(body) -> list[dict]:
    if not isinstance(body, str) or "<entry>" not in body:
        return []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    items: list[dict] = []
    for entry in root.findall("atom:entry", ns):
        raw_id = (entry.findtext("atom:id", "", ns) or "").strip()
        aid = extract_arxiv_id(raw_id)
        title = re.sub(r"\s+", " ", (entry.findtext("atom:title", "", ns) or "")).strip()
        if not title:
            continue
        authors = [
            re.sub(r"\s+", " ", (a.findtext("atom:name", "", ns) or "")).strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = (entry.findtext("atom:published", "", ns) or "").strip()
        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
        pub_doi = (entry.findtext("arxiv:doi", "", ns) or "").strip() or None
        journal_ref = (entry.findtext("arxiv:journal_ref", "", ns) or "").strip() or None
        signals: list[str] = []
        if pub_doi:
            signals.append(f"arxiv:published-doi({pub_doi})")
        clean_aid = re.sub(r"v\d+$", "", aid) if aid else None
        items.append({
            "service": "arxiv",
            "doi": pub_doi or (f"10.48550/arXiv.{clean_aid}" if clean_aid else None),
            "arxiv_id": aid,
            "title": title,
            "authors": [a for a in authors if a],
            "year": year,
            "venue": journal_ref or "arXiv",
            "oa_url": f"https://arxiv.org/pdf/{aid}.pdf" if aid else None,
            "is_retracted": False,
            "work_type": "preprint" if not pub_doi else "journal-article",
            "published_doi": pub_doi,
            "integrity_signals": signals,
        })
    return items


def _score(ref: dict, match: dict) -> float:
    score = 0.0
    if ref.get("doi") and match.get("doi") and _norm(ref["doi"]) == _norm(match["doi"]):
        score += 0.7
    if ref.get("arxiv_id") and match.get("arxiv_id"):
        a1 = re.sub(r"v\d+$", "", _norm(ref["arxiv_id"]))
        a2 = re.sub(r"v\d+$", "", _norm(match["arxiv_id"]))
        if a1 == a2:
            score += 0.7
    if ref.get("title") and match.get("title"):
        a, b = _norm(ref["title"]), _norm(match["title"])
        if a == b:
            score += 0.3
        elif a in b or b in a:
            score += 0.2
        elif set(a.split()) & set(b.split()):
            score += 0.1
    if ref.get("year") and match.get("year") and str(ref["year"]) == str(match["year"]):
        score += 0.1
    if ref.get("author") and match.get("authors"):
        family = _norm(ref["author"]).split()[-1]
        if any(family in _norm(name) for name in match["authors"]):
            score += 0.1
    return min(score, 1.0)


def _crossref_items(body):
    if not isinstance(body, dict):
        return []
    message = body.get("message")
    if not isinstance(message, dict):
        return []
    if message.get("DOI"):
        return [message]
    return list(message.get("items") or [])


def _openalex_items(body):
    if not isinstance(body, dict):
        return []
    if body.get("id") or body.get("doi"):
        return [body]
    return list(body.get("results") or [])


def _pubmed_items(body):
    if not isinstance(body, dict):
        return []
    result = (body.get("esearchresult") or {})
    return [{"pmid": pmid} for pmid in result.get("idlist") or []]


def parse_text_refs(text: str) -> list[dict]:
    refs = []
    for index, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        doi = None
        doi_match = re.search(r"10\.\d{4,9}/\S+", line)
        if doi_match:
            doi = doi_match.group(0).rstrip(".)],;")
        arxiv_id = extract_arxiv_id(line)
        year = None
        year_match = re.search(r"\b(19|20)\d{2}\b", line)
        if year_match:
            year = year_match.group(0)
        author = line.split(",")[0].split("(")[0].strip()
        refs.append({
            "id": f"T{index}",
            "doi": doi,
            "arxiv_id": arxiv_id,
            "author": author,
            "year": year,
            "title": line,
        })
    return refs


def _summarize_integrity(candidates: list[dict], best: dict | None) -> dict:
    if not best:
        return {"status": "unknown", "is_retracted": False, "published_doi": None, "signals": []}
    # Merge integrity signals across high-confidence matching candidates for the same work
    best_doi = _norm(best.get("doi"))
    best_title = _norm(best.get("title"))
    is_retracted = bool(best.get("is_retracted"))
    signals: list[str] = list(best.get("integrity_signals") or [])
    published_doi = best.get("published_doi")
    work_type = best.get("work_type")

    for c in candidates:
        same_doi = best_doi and _norm(c.get("doi")) == best_doi
        same_title = best_title and _norm(c.get("title")) == best_title
        if same_doi or same_title:
            if c.get("is_retracted"):
                is_retracted = True
            for sig in c.get("integrity_signals") or []:
                if sig not in signals:
                    signals.append(sig)
            if not published_doi and c.get("published_doi"):
                published_doi = c["published_doi"]

    if is_retracted:
        status = "retracted"
    elif any("update-to" in s or "is-updated-by" in s or "correction" in s or "concern" in s for s in signals):
        status = "updated-or-corrected"
    elif published_doi and (work_type == "preprint" or (best.get("arxiv_id") and published_doi != best.get("doi"))):
        status = "preprint-published"
    elif work_type == "preprint" or (best.get("arxiv_id") and not published_doi):
        status = "preprint-only"
    else:
        status = "clean"

    return {
        "status": status,
        "is_retracted": is_retracted,
        "published_doi": published_doi,
        "signals": signals,
    }


def resolve_one(
    ref: dict,
    services: list[str],
    mailto: str | None,
    cache_dir: Path | None,
    cache_only: bool,
    min_interval: float,
    last_request: list[float],
) -> dict:
    doi = (ref.get("doi") or "").replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    arxiv_id = ref.get("arxiv_id") or extract_arxiv_id(doi) or extract_arxiv_id(ref.get("title"))
    if arxiv_id and not ref.get("arxiv_id"):
        ref = {**ref, "arxiv_id": arxiv_id}
    bibliographic = " ".join(str(ref.get(key) or "") for key in ("author", "year", "title")).strip()
    queries = []
    candidates = []

    def add(service: str, url: str, extractor, expect_xml: bool = False):
        result = query_service(service, url, cache_dir, cache_only, min_interval, last_request, expect_xml=expect_xml)
        queries.append({
            "service": service,
            "url": url,
            "http_status": result.get("http_status"),
            "error": result.get("error"),
        })
        if result.get("http_status") == 200:
            for item in extractor(result.get("body")):
                if service == "crossref":
                    match = _match_from_crossref(item)
                elif service == "openalex":
                    match = _match_from_openalex(item)
                elif service == "arxiv":
                    match = item
                else:
                    match = {
                        "service": "pubmed",
                        "doi": doi or None,
                        "title": ref.get("title"),
                        "authors": [ref.get("author")] if ref.get("author") else [],
                        "year": ref.get("year"),
                        "venue": None,
                        "pmid": item.get("pmid"),
                        "is_retracted": False,
                        "integrity_signals": [],
                    }
                match["match_score"] = _score(ref, match)
                candidates.append(match)

    params = {"mailto": mailto} if mailto else {}
    if "crossref" in services:
        if doi:
            add("crossref", f"{CROSSREF}/works/{urllib.parse.quote(doi)}?{urllib.parse.urlencode(params)}", _crossref_items)
        elif bibliographic:
            query = dict(params)
            query["query.bibliographic"] = bibliographic
            query["rows"] = "3"
            add("crossref", f"{CROSSREF}/works?{urllib.parse.urlencode(query)}", _crossref_items)
    if "openalex" in services:
        if doi:
            add("openalex", f"{OPENALEX}/works/doi:{urllib.parse.quote(doi)}?{urllib.parse.urlencode(params)}", _openalex_items)
        elif bibliographic:
            query = dict(params)
            query["search"] = bibliographic
            query["per_page"] = "3"
            add("openalex", f"{OPENALEX}/works?{urllib.parse.urlencode(query)}", _openalex_items)
    if "pubmed" in services and bibliographic:
        query = {"db": "pubmed", "term": bibliographic, "retmode": "json", "retmax": "3"}
        if mailto:
            query["email"] = mailto
            query["tool"] = "lj-evidence"
        add("pubmed", f"{PUBMED}/esearch.fcgi?{urllib.parse.urlencode(query)}", _pubmed_items)
    if "arxiv" in services and (arxiv_id or (not doi and ref.get("title"))):
        if arxiv_id:
            clean_aid = re.sub(r"v\d+$", "", arxiv_id)
            add("arxiv", f"{ARXIV}?id_list={urllib.parse.quote(clean_aid)}", _arxiv_items, expect_xml=True)
        else:
            q = urllib.parse.quote(f'ti:"{ref.get("title", "")[:120]}"')
            add("arxiv", f"{ARXIV}?search_query={q}&max_results=3", _arxiv_items, expect_xml=True)

    best = max(candidates, key=lambda item: item.get("match_score", 0), default=None)
    reachable = [row for row in queries if row["http_status"] is not None]
    ok_empty = [row for row in reachable if row["http_status"] in (200, 404)]
    unreachable = [row for row in queries if row["http_status"] is None or (row["http_status"] >= 500)]
    if best and best.get("match_score", 0) >= 0.2:
        verdict = "resolved"
    elif unreachable and not (best and best.get("match_score", 0) >= 0.2):
        verdict = "api-unreachable"
    elif ok_empty:
        verdict = "no-match"
    else:
        verdict = "api-unreachable"

    integrity = _summarize_integrity(candidates, best)

    return {
        "id": ref.get("id"),
        "input": {key: ref.get(key) for key in ("doi", "arxiv_id", "author", "year", "title", "claim")},
        "queries": queries,
        "best_match": best,
        "integrity": integrity,
        "verdict": verdict,
        "checked_at": _now(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve citations & check retraction/preprint integrity via Crossref/OpenAlex/PubMed/arXiv."
    )
    parser.add_argument("refs", nargs="?", help="JSON array of {id, doi?, arxiv_id?, author?, year?, title?, claim?}")
    parser.add_argument("--from-text", dest="from_text")
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache")
    parser.add_argument("--mailto")
    parser.add_argument("--services", default="crossref,openalex,pubmed,arxiv")
    parser.add_argument("--from-cache-only", action="store_true")
    parser.add_argument("--min-interval", type=float, default=1.0)
    args = parser.parse_args()

    if args.from_text:
        refs = parse_text_refs(Path(args.from_text).read_text(encoding="utf-8-sig"))
    elif args.refs:
        refs = json.loads(Path(args.refs).read_text(encoding="utf-8-sig"))
        if not isinstance(refs, list):
            raise SystemExit("refs JSON must be an array")
    else:
        parser.error("provide refs.json or --from-text")

    services = [name.strip() for name in args.services.split(",") if name.strip()]
    cache_dir = Path(args.cache) if args.cache else None
    last_request = [0.0]
    ledger = [
        resolve_one(ref, services, args.mailto, cache_dir, args.from_cache_only, args.min_interval, last_request)
        for ref in refs
    ]
    Path(args.out).write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    retracted = sum(1 for r in ledger if r.get("integrity", {}).get("is_retracted"))
    print(f"wrote {len(ledger)} records to {args.out} (retracted={retracted})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
