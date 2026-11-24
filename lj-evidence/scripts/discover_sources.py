#!/usr/bin/env python3
"""Active scholarly source discovery & citation snowballing for lj-evidence (v2).

Zero third-party dependencies (Python stdlib only).
Supports:
  1. Multi-database topic discovery across OpenAlex, Semantic Scholar, and arXiv
  2. Citation snowballing from a seed DOI (--seed-doi):
     - --backward: referenced works (intellectual ancestry)
     - --forward: citing works (follow-up, uptake, refutation)
  3. Deduplication by normalized DOI / arXiv ID / title, with retraction flags,
     citation counts, and legal OA PDF URLs preserved.

Output: structured JSON (--out) and/or compact Markdown ledger (--md-out).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_ENV_EMAIL = (os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("OPENALEX_EMAIL") or "").strip()
USER_AGENT = f"lj-evidence-discover/2.1 (mailto:{_ENV_EMAIL})" if _ENV_EMAIL else "lj-evidence-discover/2.1"
OPENALEX = "https://api.openalex.org"
S2 = "https://api.semanticscholar.org/graph/v1"
ARXIV = "https://export.arxiv.org/api/query"


def _http_get(url: str, timeout: int = 25, headers: dict[str, str] | None = None, retries: int = 2) -> tuple[int, str | None, str | None]:
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace"), None
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return exc.code, None, f"HTTP {exc.code}"
        except Exception as exc:
            return 0, None, str(exc)
    return 0, None, "retry-exhausted"


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _reconstruct_abstract(inv_idx: dict[str, list[int]] | None, max_chars: int = 420) -> str:
    if not isinstance(inv_idx, dict) or not inv_idx:
        return ""
    pos: list[tuple[int, str]] = []
    for word, idxs in inv_idx.items():
        if isinstance(idxs, list):
            for i in idxs:
                pos.append((i, word))
    pos.sort(key=lambda x: x[0])
    text = " ".join(w for _, w in pos)
    return (text[:max_chars].rsplit(" ", 1)[0] + "…") if len(text) > max_chars else text


def _openalex_to_record(w: dict[str, Any], route: str) -> dict[str, Any]:
    doi = (w.get("doi") or "").replace("https://doi.org/", "").strip() or None
    authors = [
        (a.get("author") or {}).get("display_name", "")
        for a in (w.get("authorships") or [])[:6]
    ]
    authors = [a for a in authors if a]
    pl = w.get("primary_location") or {}
    venue = ((pl.get("source") or {}).get("display_name") or "").strip()
    best_oa = w.get("best_oa_location") or {}
    oa_pdf = best_oa.get("pdf_url") or (w.get("open_access") or {}).get("oa_url") or None
    arxiv_id = None
    if doi and doi.lower().startswith("10.48550/arxiv."):
        arxiv_id = doi.split("arXiv.", 1)[-1]
    return {
        "title": (w.get("display_name") or w.get("title") or "").strip(),
        "authors": authors,
        "year": w.get("publication_year"),
        "venue": venue,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": w.get("id"),
        "cited_by_count": w.get("cited_by_count") or 0,
        "is_retracted": bool(w.get("is_retracted")),
        "work_type": w.get("type") or "",
        "oa_pdf_url": oa_pdf,
        "abstract_snippet": _reconstruct_abstract(w.get("abstract_inverted_index")),
        "routes": [route],
    }


def search_openalex(
    query: str,
    year_from: int | None,
    year_to: int | None,
    limit: int,
    sort: str,
    mailto: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: dict[str, str] = {"search": query, "per-page": str(min(limit, 50))}
    filters: list[str] = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    if sort == "cited":
        params["sort"] = "cited_by_count:desc"
    elif sort == "recent":
        params["sort"] = "publication_date:desc"
    if mailto:
        params["mailto"] = mailto
    url = f"{OPENALEX}/works?{urllib.parse.urlencode(params)}"
    st, raw, err = _http_get(url)
    log = {"source": "openalex", "route": "topic-search", "url": url, "http_status": st, "error": err, "count": 0}
    if st != 200 or not raw:
        return [], log
    data = json.loads(raw)
    recs = [_openalex_to_record(w, "openalex:search") for w in data.get("results") or []]
    log["count"] = len(recs)
    return recs, log


def snowball_openalex(
    seed_doi: str,
    backward: bool,
    forward: bool,
    year_from: int | None,
    limit: int,
    mailto: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    logs: list[dict[str, Any]] = []
    clean_doi = seed_doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    params = {"mailto": mailto} if mailto else {}
    seed_url = f"{OPENALEX}/works/https://doi.org/{urllib.parse.quote(clean_doi, safe='')}"
    if params:
        seed_url += f"?{urllib.parse.urlencode(params)}"
    st, raw, err = _http_get(seed_url)
    logs.append({"source": "openalex", "route": "seed-lookup", "url": seed_url, "http_status": st, "error": err})
    if st != 200 or not raw:
        return None, [], logs
    seed_raw = json.loads(raw)
    seed_rec = _openalex_to_record(seed_raw, "openalex:seed")
    oa_short_id = (seed_raw.get("id") or "").rsplit("/", 1)[-1]
    out: list[dict[str, Any]] = []

    if forward and oa_short_id:
        f_filters = [f"cites:{oa_short_id}"]
        if year_from:
            f_filters.append(f"from_publication_date:{year_from}-01-01")
        fp = {
            "filter": ",".join(f_filters),
            "sort": "cited_by_count:desc",
            "per-page": str(min(limit, 50)),
        }
        if mailto:
            fp["mailto"] = mailto
        f_url = f"{OPENALEX}/works?{urllib.parse.urlencode(fp)}"
        fst, fraw, ferr = _http_get(f_url)
        recs = [_openalex_to_record(w, "openalex:forward-cites") for w in (json.loads(fraw).get("results") or [])] if (fst == 200 and fraw) else []
        logs.append({"source": "openalex", "route": "forward-cites", "url": f_url, "http_status": fst, "error": ferr, "count": len(recs)})
        out.extend(recs)

    if backward:
        ref_ids = [(r.rsplit("/", 1)[-1]) for r in (seed_raw.get("referenced_works") or [])[:min(limit, 40)]]
        if ref_ids:
            bp = {
                "filter": f"openalex:{'|'.join(ref_ids)}",
                "sort": "cited_by_count:desc",
                "per-page": str(min(len(ref_ids), 50)),
            }
            if mailto:
                bp["mailto"] = mailto
            b_url = f"{OPENALEX}/works?{urllib.parse.urlencode(bp)}"
            bst, braw, berr = _http_get(b_url)
            recs = [_openalex_to_record(w, "openalex:backward-refs") for w in (json.loads(braw).get("results") or [])] if (bst == 200 and braw) else []
            logs.append({"source": "openalex", "route": "backward-refs", "url": b_url, "http_status": bst, "error": berr, "count": len(recs)})
            out.extend(recs)

    return seed_rec, out, logs


def search_s2(
    query: str,
    year_from: int | None,
    year_to: int | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: dict[str, str] = {
        "query": query,
        "limit": str(min(limit, 30)),
        "fields": "title,authors,year,venue,citationCount,externalIds,openAccessPdf,abstract",
    }
    if year_from or year_to:
        params["year"] = f"{year_from or ''}-{year_to or ''}"
    url = f"{S2}/paper/search?{urllib.parse.urlencode(params)}"
    hdrs = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        hdrs["x-api-key"] = api_key
    st, raw, err = _http_get(url, headers=hdrs)
    log = {"source": "semantic-scholar", "route": "topic-search", "url": url, "http_status": st, "error": err, "count": 0}
    if st != 200 or not raw:
        return [], log
    data = json.loads(raw)
    recs: list[dict[str, Any]] = []
    for p in data.get("data") or []:
        ext = p.get("externalIds") or {}
        doi = ext.get("DOI") or None
        aid = ext.get("ArXiv") or None
        abs_text = (p.get("abstract") or "").strip()
        if len(abs_text) > 420:
            abs_text = abs_text[:420].rsplit(" ", 1)[0] + "…"
        oa_url = (p.get("openAccessPdf") or {}).get("url") or (f"https://arxiv.org/pdf/{aid}.pdf" if aid else None)
        recs.append({
            "title": (p.get("title") or "").strip(),
            "authors": [a.get("name", "") for a in (p.get("authors") or [])[:6] if a.get("name")],
            "year": p.get("year"),
            "venue": (p.get("venue") or "").strip(),
            "doi": doi,
            "arxiv_id": aid,
            "openalex_id": None,
            "cited_by_count": p.get("citationCount") or 0,
            "is_retracted": False,
            "work_type": "preprint" if (aid and not doi) else "",
            "oa_pdf_url": oa_url,
            "abstract_snippet": abs_text,
            "routes": ["s2:search"],
        })
    log["count"] = len(recs)
    return recs, log


def search_arxiv(
    query: str,
    year_from: int | None,
    year_to: int | None,
    limit: int,
    sort: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sort_by = "submittedDate" if sort == "recent" else "relevance"
    params = {
        "search_query": f"all:{query}",
        "start": "0",
        "max_results": str(min(limit, 30)),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    url = f"{ARXIV}?{urllib.parse.urlencode(params)}"
    st, raw, err = _http_get(url)
    log = {"source": "arxiv", "route": "topic-search", "url": url, "http_status": st, "error": err, "count": 0}
    if st != 200 or not raw:
        return [], log
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        log["error"] = f"xml parse error: {exc}"
        return [], log
    recs: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        raw_id = (entry.findtext("atom:id", "", ns) or "").strip()
        m = re.search(r"arxiv\.org/abs/([^\s]+)", raw_id)
        aid = re.sub(r"v\d+$", "", m.group(1)) if m else None
        published = (entry.findtext("atom:published", "", ns) or "").strip()
        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
        if year_from and year and year < year_from:
            continue
        if year_to and year and year > year_to:
            continue
        title = re.sub(r"\s+", " ", (entry.findtext("atom:title", "", ns) or "")).strip()
        summary = re.sub(r"\s+", " ", (entry.findtext("atom:summary", "", ns) or "")).strip()
        if len(summary) > 420:
            summary = summary[:420].rsplit(" ", 1)[0] + "…"
        authors = [
            re.sub(r"\s+", " ", (a.findtext("atom:name", "", ns) or "")).strip()
            for a in entry.findall("atom:author", ns)[:6]
        ]
        pub_doi = (entry.findtext("arxiv:doi", "", ns) or "").strip() or None
        jref = (entry.findtext("arxiv:journal_ref", "", ns) or "").strip() or None
        recs.append({
            "title": title,
            "authors": [a for a in authors if a],
            "year": year,
            "venue": jref or "arXiv",
            "doi": pub_doi or (f"10.48550/arXiv.{aid}" if aid else None),
            "arxiv_id": aid,
            "openalex_id": None,
            "cited_by_count": 0,
            "is_retracted": False,
            "work_type": "journal-article" if pub_doi else "preprint",
            "oa_pdf_url": f"https://arxiv.org/pdf/{aid}.pdf" if aid else None,
            "abstract_snippet": summary,
            "routes": ["arxiv:search"],
        })
    log["count"] = len(recs)
    return recs, log


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for r in records:
        doi_k = f"doi:{r['doi'].lower()}" if r.get("doi") else ""
        aid_k = f"arxiv:{r['arxiv_id'].lower()}" if r.get("arxiv_id") else ""
        tit_k = f"title:{_norm_title(r.get('title', ''))}"
        matched_key = None
        for k in (doi_k, aid_k, tit_k):
            if k and k in by_key:
                matched_key = k
                break
        if matched_key:
            cur = by_key[matched_key]
            cur["cited_by_count"] = max(cur.get("cited_by_count") or 0, r.get("cited_by_count") or 0)
            cur["is_retracted"] = bool(cur.get("is_retracted") or r.get("is_retracted"))
            for field in ("doi", "arxiv_id", "openalex_id", "venue", "oa_pdf_url", "abstract_snippet"):
                if not cur.get(field) and r.get(field):
                    cur[field] = r[field]
            for rt in r.get("routes") or []:
                if rt not in cur["routes"]:
                    cur["routes"].append(rt)
        else:
            primary_k = doi_k or aid_k or tit_k
            if not primary_k or primary_k == "title:":
                continue
            by_key[primary_k] = dict(r)
            order.append(primary_k)
            for alias in (doi_k, aid_k, tit_k):
                if alias and alias != "title:" and alias not in by_key:
                    by_key[alias] = by_key[primary_k]
    return [by_key[k] for k in order]


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Source Discovery Ledger — {payload.get('query') or payload.get('seed_doi')}",
        "",
        f"- **Generated**: `{payload['generated_at']}`",
        f"- **Unique candidates**: `{len(payload['results'])}` (retracted flagged: `{sum(1 for r in payload['results'] if r['is_retracted'])}`)",
        "- **Routes run**: " + ", ".join(f"`{lg['source']}:{lg['route']}` (HTTP {lg['http_status']}, n={lg.get('count', '-')})" for lg in payload["search_log"]),
        "",
        "| Year | Cites | Status | Title | Authors / Venue | ID / OA | Routes |",
        "|---:|---:|---|---|---|---|---|",
    ]
    for r in payload["results"]:
        st = "🔴 RETRACTED" if r["is_retracted"] else ("preprint" if r.get("work_type") == "preprint" else "ok")
        au = ", ".join((r.get("authors") or [])[:2]) + (" et al." if len(r.get("authors") or []) > 2 else "")
        id_parts = []
        if r.get("doi"):
            id_parts.append(f"`{r['doi']}`")
        elif r.get("arxiv_id"):
            id_parts.append(f"`arXiv:{r['arxiv_id']}`")
        if r.get("oa_pdf_url"):
            id_parts.append(f"[OA PDF]({r['oa_pdf_url']})")
        title_safe = (r.get("title") or "").replace("|", "\\|")
        venue_safe = (r.get("venue") or "").replace("|", "\\|")
        lines.append(
            f"| {r.get('year') or '-'} | {r.get('cited_by_count') or 0} | {st} | {title_safe} | {au} · *{venue_safe}* | {' · '.join(id_parts)} | `{', '.join(r.get('routes') or [])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Active multi-database literature discovery & citation snowballing.")
    ap.add_argument("--query", default="", help="Topic search query across OpenAlex / Semantic Scholar / arXiv")
    ap.add_argument("--seed-doi", default="", help="Seed DOI for citation snowballing")
    ap.add_argument("--backward", action="store_true", help="Include backward referenced works from --seed-doi")
    ap.add_argument("--forward", action="store_true", help="Include forward citing works from --seed-doi")
    ap.add_argument("--sources", default="openalex,s2,arxiv", help="Comma-separated sources for --query (default: openalex,s2,arxiv)")
    ap.add_argument("--year-from", type=int, default=None, help="Filter lower publication year (inclusive)")
    ap.add_argument("--year-to", type=int, default=None, help="Filter upper publication year (inclusive)")
    ap.add_argument("--limit", type=int, default=15, help="Max results per source/direction (default: 15)")
    ap.add_argument("--sort", choices=["relevance", "cited", "recent"], default="relevance", help="Sort order for topic queries")
    ap.add_argument("--mailto", default=os.environ.get("UNPAYWALL_EMAIL", ""), help="Polite-pool email for OpenAlex")
    ap.add_argument("--out", default="", help="Write structured JSON ledger to path")
    ap.add_argument("--md-out", default="", help="Write Markdown table ledger to path")
    args = ap.parse_args()

    if not args.query and not args.seed_doi:
        ap.error("Provide --query <text> and/or --seed-doi <doi>.")

    all_recs: list[dict[str, Any]] = []
    search_log: list[dict[str, Any]] = []
    seed_rec = None

    if args.query:
        srcs = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
        if "openalex" in srcs:
            r, lg = search_openalex(args.query, args.year_from, args.year_to, args.limit, args.sort, args.mailto or None)
            all_recs.extend(r)
            search_log.append(lg)
        if "s2" in srcs:
            time.sleep(0.3)
            r, lg = search_s2(args.query, args.year_from, args.year_to, args.limit)
            all_recs.extend(r)
            search_log.append(lg)
        if "arxiv" in srcs:
            time.sleep(0.3)
            r, lg = search_arxiv(args.query, args.year_from, args.year_to, args.limit, args.sort)
            all_recs.extend(r)
            search_log.append(lg)

    if args.seed_doi:
        do_back = args.backward or not args.forward
        do_fwd = args.forward or not args.backward
        seed_rec, recs, lgs = snowball_openalex(args.seed_doi, do_back, do_fwd, args.year_from, args.limit, args.mailto or None)
        all_recs.extend(recs)
        search_log.extend(lgs)

    deduped = deduplicate(all_recs)
    if args.sort == "cited":
        deduped.sort(key=lambda r: (r.get("cited_by_count") or 0, r.get("year") or 0), reverse=True)
    elif args.sort == "recent":
        deduped.sort(key=lambda r: (r.get("year") or 0, r.get("cited_by_count") or 0), reverse=True)
    else:
        deduped.sort(key=lambda r: (len(r.get("routes") or []), r.get("cited_by_count") or 0, r.get("year") or 0), reverse=True)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "query": args.query or None,
        "seed_doi": args.seed_doi or None,
        "seed_record": seed_rec,
        "year_from": args.year_from,
        "year_to": args.year_to,
        "search_log": search_log,
        "results": deduped,
    }

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON discovery ledger: {out_p} ({len(deduped)} unique works)")

    if args.md_out:
        md_p = Path(args.md_out)
        md_p.parent.mkdir(parents=True, exist_ok=True)
        md_p.write_text(render_markdown(payload), encoding="utf-8")
        print(f"Wrote Markdown discovery ledger: {md_p}")

    if not args.out and not args.md_out:
        print(render_markdown(payload))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
