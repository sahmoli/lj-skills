#!/usr/bin/env python3
"""Legal Open-Access full-text fetcher, semantic verifier & provenance ledger (lj-evidence v2.1).

Repository-first legal cascade (zero anti-bot bypass, zero Sci-Hub):
  0. Revalidate cached local PDF via `verify_pdf.py` (never blindly trust file size)
  1. Explicit legal URL / arXiv direct
  2. Europe PMC / PMC OA (PDF + optional JATS XML structured fallback with `<!-- jats-sec:... -->` anchors)
  3. OpenAIRE Graph v3 (OPEN institutional repositories & PMC copies)
  4. Unpaywall (requires user's `$UNPAYWALL_EMAIL` or `--email`; published > accepted > submitted)
  5. OpenAlex (`best_oa_location`, `locations`, retraction warning `is_retracted`)
  6. Optional official Wiley TDM API (`$WILEY_TDM_TOKEN`, only when configured by user)
  7. Semantic Scholar `openAccessPdf` + ArXiv ID
  8. Crossref metadata + deterministic OA publisher patterns (PLOS / MDPI / Frontiers / BMC)
     + single-level `citation_pdf_url` / PDF-anchor scrape on repository/landing HTML

All downloaded PDFs pass three-state `verify_pdf.py` (`verified` / `needs-review` / `rejected`).
Only `verified` PDFs are filed and appended to `_provenance.jsonl`; `needs-review` goes to
`_needs_review/` and `rejected` goes to `_rejected/`.
Remaining paywalled/WAF papers can be opened in the user's normal desktop browser (`--open-wanted`)
so institutional VPN / Zotero Connector can download them cleanly, then harvested by `ingest_local.py`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from verify_pdf import clean_doi, validate as validate_pdf  # noqa: E402

TIMEOUT = 25
MAX_PDF_BYTES = 60 * 1024 * 1024
ARXIV_RE = re.compile(
    r"(?:arxiv:\s*|10\.48550/arxiv\.|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)
BROWSER_LIKE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VERSION_RANK = {
    "publishedversion": 0,
    "published": 0,
    "acceptedversion": 1,
    "accepted": 1,
    "submittedversion": 2,
    "submitted": 2,
    "": 3,
}


def default_papers_dir() -> str:
    env_dir = os.environ.get("LJ_PAPERS_DIR", "").strip()
    if env_dir:
        return env_dir
    return str(Path.cwd() / "papers")


def default_inbox_dir() -> str:
    env_dir = os.environ.get("LJ_INBOX_DIR", "").strip()
    if env_dir:
        return env_dir
    papers = Path(default_papers_dir())
    # If papers lives at <hub>/10_raw/papers, default inbox is <hub>/00_inbox
    if papers.name == "papers" and papers.parent.name == "10_raw":
        cand = papers.parent.parent / "00_inbox"
        if cand.is_dir():
            return str(cand)
    return str(Path.cwd())


def build_api_ua(email: str = "") -> str:
    if email:
        return f"lj-evidence-oa-fetcher/2.1 (mailto:{email})"
    return "lj-evidence-oa-fetcher/2.1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_arxiv_id(text: str | None) -> str | None:
    if not text:
        return None
    m = ARXIV_RE.search(text)
    if m:
        return m.group(1)
    bare = re.fullmatch(r"\s*(\d{4}\.\d{4,5}(?:v\d+)?)\s*", text)
    return bare.group(1) if bare else None


def slugify_paper(year: int | str | None, first_author: str, short_title: str) -> str:
    yr = re.sub(r"[^0-9]", "", str(year or ""))[:4] or "nd"
    au = re.sub(r"[^a-z0-9]+", "-", (first_author or "").lower()).strip("-") or "anon"
    words = [
        w
        for w in re.findall(r"[a-z0-9]+", (short_title or "").lower())
        if w not in {"the", "a", "an", "of", "on", "in", "for", "and", "to", "is", "are"}
    ]
    tail = "-".join(words[:4]) or "paper"
    return f"{yr}-{au}-{tail}"


def http_get_json(url: str, timeout: int = TIMEOUT, email: str = "") -> tuple[int, Any | None, str | None]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": build_api_ua(email), "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw), None
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}"
    except Exception as e:
        return 0, None, str(e)


def classify_html(html_text: str, status_code: int = 200) -> str:
    low = (html_text or "")[:12000].lower()
    if status_code in (403, 429, 503) and any(
        k in low for k in ("cloudflare", "just a moment", "cf-mitigated", "challenge-platform", "attention required")
    ):
        return "waf-html"
    if any(k in low for k in ("cf-mitigated", "just a moment", "challenge-platform", "enable javascript and cookies", "attention required")):
        return "waf-html"
    if any(k in low for k in ("institutional login", "sign in to access", "purchase pdf", "subscribe to read", "buy this article", "access through your institution", "get access")):
        return "paywall-html"
    if status_code == 401 or status_code == 402:
        return "paywall-html"
    if status_code == 403:
        return "waf-html"
    return "landing-html"


def extract_pdf_links_from_html(html_text: str, base_url: str) -> list[str]:
    """Extract candidate PDF URLs (citation_pdf_url meta tag + PDF anchor links), 1 level deep."""
    found: list[str] = []
    seen: set[str] = set()

    def push(raw_u: str) -> None:
        u = htmlmod.unescape(raw_u.strip())
        if not u or u.startswith(("javascript:", "mailto:", "#")):
            return
        full = urllib.parse.urljoin(base_url, u)
        if not full.lower().startswith(("http://", "https://")):
            return
        if re.search(r"\.(?:jpe?g|png|gif|svg|css|js|ico|woff2?)(?:\?|$)", full, re.I):
            return
        # Skip obvious ad/media-kit links
        if re.search(r"media[-_]?kit|rate[-_]?card|advertis", full, re.I):
            return
        key = full.split("#")[0]
        if key not in seen:
            seen.add(key)
            found.append(full)

    # 1) High-signal Google Scholar / HighWire meta tag
    for m in re.finditer(
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    ):
        push(m.group(1))
    for m in re.finditer(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        html_text,
        re.IGNORECASE,
    ):
        push(m.group(1))

    # 2) Anchor tags pointing to PDFs or repository bitstreams
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.IGNORECASE | re.DOTALL):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        if re.search(r"\.pdf(?:\?|$)|/bitstream/|/download/|/pdf/|pdfdirect|blobtype=pdf|type=printable", href, re.I) or re.search(r"\bpdf\b|full\s*text\s*pdf|download\s*pdf", text, re.I):
            push(href)

    return found[:6]


def try_download_pdf(
    url: str,
    timeout: int = 35,
    referer: str = "",
    extra_headers: dict[str, str] | None = None,
) -> tuple[bytes | None, str, str, list[str]]:
    """Fetch URL. Returns (pdf_bytes_or_None, failure_class_or_ok, detail, scraped_pdf_links)."""
    if not url or not url.lower().startswith(("http://", "https://")):
        return None, "network", "invalid-url", []
    headers = {
        "User-Agent": BROWSER_LIKE_UA,
        "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final_url = resp.geturl() or url
            ctype = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read(MAX_PDF_BYTES)
            if data[:5] == b"%PDF-":
                if len(data) < 20_000:
                    return None, "truncated-no-eof", f"too-small ({len(data)} bytes)", []
                return data, "ok", f"ok ({len(data)} bytes, {ctype})", []
            html_text = data[:120_000].decode("utf-8", errors="replace")
            fclass = classify_html(html_text, resp.status)
            scraped = extract_pdf_links_from_html(html_text, final_url) if fclass == "landing-html" else []
            return None, fclass, f"{fclass} (http={resp.status}, ctype={ctype}, bytes={len(data)})", scraped
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(16_000).decode("utf-8", errors="replace")
        except Exception:
            pass
        fclass = classify_html(body, e.code)
        return None, fclass, f"{fclass} (HTTP {e.code})", []
    except Exception as e:
        return None, "network", f"network ({e})", []


def fetch_jats_xml_markdown(pmcid: str, meta: dict[str, Any], out_dir: Path, slug: str, email: str = "") -> dict[str, Any] | None:
    """Fetch official Europe PMC JATS fullTextXML and render section-anchored Markdown (NEVER fabricates PDF pages)."""
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{urllib.parse.quote(pmcid, safe='')}/fullTextXML"
    req = urllib.request.Request(url, headers={"User-Agent": build_api_ua(email), "Accept": "application/xml,text/xml"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            xml_bytes = resp.read(25 * 1024 * 1024)
    except Exception:
        return None

    if not xml_bytes or b"<article" not in xml_bytes[:4000]:
        return None

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    def txt_of(el: ET.Element | None) -> str:
        if el is None:
            return ""
        return re.sub(r"\s+", " ", "".join(el.itertext())).strip()

    sections: list[tuple[str, str, str]] = []  # (anchor_id, heading, body_md)

    abstract_el = root.find(".//abstract")
    if abstract_el is not None:
        abs_txt = txt_of(abstract_el)
        if abs_txt:
            sections.append(("sec:abstract", "Abstract", abs_txt))

    body_el = root.find(".//body")
    sec_idx = 0
    if body_el is not None:
        for sec in body_el.findall("./sec"):
            sec_idx += 1
            heading = txt_of(sec.find("title")) or f"Section {sec_idx}"
            sec_id = re.sub(r"[^a-z0-9_-]+", "-", heading.lower()).strip("-")[:32] or f"s{sec_idx}"
            paras = [txt_of(p) for p in sec.findall(".//p") if txt_of(p)]
            # Also capture table captions/rows cleanly
            for tw in sec.findall(".//table-wrap"):
                cap = txt_of(tw.find("caption"))
                if cap:
                    paras.append(f"**Table**: {cap}")
            for fig in sec.findall(".//fig"):
                cap = txt_of(fig.find("caption"))
                if cap:
                    paras.append(f"**Figure**: {cap}")
            if paras:
                sections.append((f"sec:{sec_idx}-{sec_id}", heading, "\n\n".join(paras)))

    if not sections:
        return None

    xml_sha = sha256_bytes(xml_bytes)
    xml_path = out_dir / f"{slug}.jats.xml"
    md_path = out_dir / f"{slug}.md"
    xml_path.write_bytes(xml_bytes)

    def yq(v: str) -> str:
        return '"' + (v or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'

    today = dt.date.today().isoformat()
    title = meta.get("title") or slug
    authors_year = meta.get("authors_year") or ""
    venue = meta.get("venue") or ""
    doi = meta.get("doi") or ""

    lines = [
        "---",
        f"slug: {slug}",
        f"title: {yq(title)}",
        f"authors_year: {yq(authors_year)}",
        f"venue: {yq(venue)}",
        f"doi: {yq(doi)}",
        f"pmcid: {yq(pmcid)}",
        "source_format: jats_xml",
        "read_status: ready",
        "provenance: source",
        "privacy: private",
        f"xml_sha256: {yq(xml_sha)}",
        'converter: "europepmc-jats-xml"',
        f"updated: {today}",
        "---",
        "",
        f"# {authors_year + ' · ' if authors_year else ''}{title}",
        "",
        f"> - 原版来源：Europe PMC JATS XML（`{pmcid}`，`DOI: {doi or '无'}`，`SHA-256: {xml_sha[:12]}`）",
        "> - **锚点提醒**：本文档来自官方 JATS XML，使用 `<!-- jats-sec:... -->` 语义节锚点（**无物理 PDF 页码**）；如需物理页码或排版图表复核，请同时获取 PDF。",
        "",
        "---",
        "",
    ]
    for anchor_id, heading, body_md in sections:
        lines.append(f"## {heading}")
        lines.append(f"<!-- jats-{anchor_id} -->")
        lines.append("")
        lines.append(body_md)
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "slug": slug,
        "pmcid": pmcid,
        "xml_path": str(xml_path),
        "md_path": str(md_path),
        "xml_sha256": xml_sha,
        "bytes": len(xml_bytes),
        "sections": len(sections),
        "source_url": url,
    }


def discover_oa_candidates(
    doi: str = "",
    email: str | None = None,
    known_url: str | None = None,
    arxiv_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (metadata, repository-first ordered candidate list)."""
    doi = clean_doi(doi)
    meta: dict[str, Any] = {"doi": doi}
    cands: list[dict[str, Any]] = []
    seen: set[str] = set()
    email_str = (email or "").strip()

    def add(
        url: str | None,
        api: str,
        priority: int,
        version: str | None = None,
        lic: str | None = None,
        status: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if not url:
            return
        u = url.strip()
        if not u.lower().startswith(("http://", "https://")):
            return
        key = u.split("#")[0]
        if key not in seen:
            seen.add(key)
            cands.append({
                "url": u,
                "source_api": api,
                "priority": priority,
                "version": version or "",
                "license": lic or "",
                "oa_status": status or "",
                "headers": headers or {},
            })

    # 1. Explicit legal URL & arXiv direct (priority 5–10)
    if known_url:
        add(known_url, "explicit-legal-url", 5, version="author-or-repo", status="explicit")

    detected_arxiv = arxiv_id or extract_arxiv_id(doi)
    if detected_arxiv:
        meta["arxiv_id"] = detected_arxiv
        add(
            f"https://arxiv.org/pdf/{detected_arxiv}.pdf",
            "arxiv-direct",
            10,
            version="submittedVersion",
            lic="unknown",
            status="green/arxiv",
        )
        if not doi:
            clean_aid = re.sub(r"v\d+$", "", detected_arxiv)
            doi = f"10.48550/arXiv.{clean_aid}"
            meta["doi"] = doi

    if not doi:
        cands.sort(key=lambda c: c["priority"])
        return meta, cands

    # 2. Deterministic PLOS CC-BY Gold OA PDF (zero WAF, priority 12)
    plos_map = {
        "pone": "plosone",
        "pcbi": "ploscompbiol",
        "pbio": "plosbiology",
        "pgen": "plosgenetics",
        "ppat": "plospathogens",
        "pmed": "plosmedicine",
        "pntd": "plosntds",
        "pclm": "climate",
        "pwat": "water",
        "pgph": "globalpublichealth",
        "pstr": "sustainabilitytransformation",
        "pdig": "digitalhealth",
    }
    pm = re.match(r"^10\.1371/journal\.([a-z]+)\.\d+$", doi, re.IGNORECASE)
    if pm and pm.group(1).lower() in plos_map:
        jpath = plos_map[pm.group(1).lower()]
        add(
            f"https://journals.plos.org/{jpath}/article/file?id={urllib.parse.quote(doi, safe='')}&type=printable",
            "plos-direct-oa",
            12,
            version="publishedVersion",
            lic="cc-by",
            status="gold",
        )

    # 3. Europe PMC (PMC Open Access PDF + PMCID for JATS XML fallback, priority 15)
    epmc_q = urllib.parse.quote(f'DOI:"{doi}"')
    st, data, _ = http_get_json(
        f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={epmc_q}&format=json&resultType=core",
        email=email_str,
    )
    if st == 200 and isinstance(data, dict):
        results = (data.get("resultList") or {}).get("result") or []
        for rec in results[:2]:
            pmcid = rec.get("pmcid")
            is_oa = str(rec.get("isOpenAccess", "")).upper() == "Y"
            if rec.get("title"):
                meta.setdefault("title", rec["title"])
            if rec.get("pubYear"):
                meta.setdefault("year", int(rec["pubYear"]) if str(rec["pubYear"]).isdigit() else rec["pubYear"])
            if pmcid and is_oa:
                meta["pmcid"] = pmcid
                meta["epmc_license"] = rec.get("license") or "pmc-oa"
                add(
                    f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
                    "europepmc-oa",
                    15,
                    version="publishedVersion",
                    lic=rec.get("license") or "pmc-oa",
                    status="gold/pmc",
                )

    # 4. OpenAIRE Graph v3 (OPEN institutional repositories & PMC copies, priority 20–24)
    st, data, _ = http_get_json(
        f"https://api.openaire.eu/graph/v3/research-products?pid={urllib.parse.quote(doi, safe='')}&pageSize=3",
        email=email_str,
    )
    if st == 200 and isinstance(data, dict):
        for res in data.get("results") or []:
            if res.get("mainTitle"):
                meta.setdefault("title", res["mainTitle"])
            pub_date = res.get("publicationDate") or ""
            if len(pub_date) >= 4 and pub_date[:4].isdigit():
                meta.setdefault("year", int(pub_date[:4]))
            for inst in res.get("instances") or []:
                access = ((inst.get("accessRight") or {}).get("label") or "").upper()
                if access and access not in ("OPEN", "UNKNOWN"):
                    continue
                lic = inst.get("license") or ""
                for u in inst.get("urls") or []:
                    if not isinstance(u, str):
                        continue
                    # Deprioritize direct publisher WAF hosts inside OpenAIRE; prioritize repositories/PMC
                    is_waf_host = bool(re.search(r"onlinelibrary\.wiley\.com|sciencedirect\.com|tandfonline\.com", u, re.I))
                    pri = 65 if is_waf_host else (20 if re.search(r"\.pdf|bitstream|download|pmc", u, re.I) else 24)
                    add(u, "openaire-repo", pri, version="publishedVersion", lic=lic, status=access.lower() or "open")

    # 5. Unpaywall (user-configured email only; version ranked published > accepted > submitted, priority 28–33)
    if email_str:
        up_url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='')}?email={urllib.parse.quote(email_str)}"
        st, data, _ = http_get_json(up_url, email=email_str)
        if st == 200 and isinstance(data, dict):
            if data.get("title"):
                meta.setdefault("title", data["title"])
            if data.get("year"):
                meta.setdefault("year", data["year"])
            if data.get("journal_name"):
                meta.setdefault("venue", data["journal_name"])
            locs = []
            if data.get("best_oa_location"):
                locs.append(data["best_oa_location"])
            locs.extend(data.get("oa_locations") or [])
            for loc in locs:
                if not isinstance(loc, dict):
                    continue
                ver = (loc.get("version") or "").lower()
                host_type = (loc.get("host_type") or "").lower()
                u_pdf = loc.get("url_for_pdf")
                u_land = loc.get("url")
                # Prefer repository copies over WAF-heavy publisher URLs in non-browser mode
                repo_bonus = 0 if host_type == "repository" else 12
                pri = 28 + VERSION_RANK.get(ver, 3) + repo_bonus
                if u_pdf:
                    add(u_pdf, f"unpaywall-{host_type or 'loc'}", pri, loc.get("version"), loc.get("license"), data.get("oa_status"))
                elif u_land:
                    add(u_land, f"unpaywall-landing", pri + 5, loc.get("version"), loc.get("license"), data.get("oa_status"))

    # 6. OpenAlex (integrity `is_retracted` + repository/best OA locations, priority 35–48)
    oa_url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi, safe='')}"
    if email_str:
        oa_url += f"?mailto={urllib.parse.quote(email_str)}"
    st, data, _ = http_get_json(oa_url, email=email_str)
    if st == 200 and isinstance(data, dict):
        meta.setdefault("title", data.get("display_name") or data.get("title") or "")
        meta.setdefault("year", data.get("publication_year"))
        if "is_retracted" in data and data["is_retracted"] is not None:
            meta["is_retracted"] = bool(data["is_retracted"])
            meta["retraction_status"] = "flagged" if meta["is_retracted"] else "checked_clear"
        else:
            meta.setdefault("is_retracted", None)
            meta.setdefault("retraction_status", "unknown")
        auths = data.get("authorships") or []
        if auths:
            names = [a.get("author", {}).get("display_name", "") for a in auths if a.get("author")]
            meta.setdefault("authors", [n for n in names if n])
        pl = data.get("primary_location") or {}
        src = pl.get("source") or {}
        if src.get("display_name"):
            meta.setdefault("venue", src["display_name"])
        oa_info = data.get("open_access") or {}
        oa_status = oa_info.get("oa_status") or ""
        best = data.get("best_oa_location") or {}
        if best.get("pdf_url"):
            is_waf = bool(re.search(r"onlinelibrary\.wiley\.com|sciencedirect\.com", best["pdf_url"], re.I))
            add(best["pdf_url"], "openalex-best", 55 if is_waf else 35, best.get("version"), best.get("license"), oa_status)
        for loc in data.get("locations") or []:
            if isinstance(loc, dict) and loc.get("is_oa"):
                u = loc.get("pdf_url") or loc.get("landing_page_url")
                if u:
                    is_waf = bool(re.search(r"onlinelibrary\.wiley\.com|sciencedirect\.com", u, re.I))
                    pri = 58 if is_waf else (38 if loc.get("pdf_url") else 46)
                    add(u, "openalex-location", pri, loc.get("version"), loc.get("license"), oa_status)

    # 7. Optional official Wiley TDM API hook (only when user supplies WILEY_TDM_TOKEN)
    wiley_token = os.environ.get("WILEY_TDM_TOKEN", "").strip()
    if wiley_token and re.match(r"^10\.(1002|1111|1046|1890)/", doi, re.I):
        add(
            f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{urllib.parse.quote(doi, safe='')}",
            "wiley-tdm-api",
            42,
            version="publishedVersion",
            status="tdm-authorized",
            headers={"Wiley-TDM-Client-Token": wiley_token, "Accept": "application/pdf"},
        )

    # 8. Semantic Scholar (priority 48–50)
    s2_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi, safe='')}?fields=openAccessPdf,title,year,venue,externalIds"
    st, data, _ = http_get_json(s2_url, email=email_str)
    if st == 200 and isinstance(data, dict):
        oapdf = data.get("openAccessPdf") or {}
        if oapdf.get("url"):
            add(oapdf["url"], "semantic-scholar-oa", 48, status=oapdf.get("status") or "oa")
        s2_arxiv = (data.get("externalIds") or {}).get("ArXiv")
        if s2_arxiv:
            add(
                f"https://arxiv.org/pdf/{s2_arxiv}.pdf",
                "s2-arxiv-direct",
                11,
                version="submittedVersion",
                lic="unknown",
                status="green/arxiv",
            )

    # 9. Crossref metadata + fallback OA publisher landing/direct patterns (priority 70+)
    st, data, _ = http_get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}", email=email_str)
    if st == 200 and isinstance(data, dict):
        m = data.get("message") or {}
        if m.get("title"):
            meta.setdefault("title", (m["title"] or [""])[0])
        if m.get("container-title"):
            meta.setdefault("venue", (m["container-title"] or [""])[0])
        issued = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        if issued:
            meta.setdefault("year", issued)
        if not meta.get("authors"):
            auths = m.get("author") or []
            names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in auths if a.get("family")]
            if names:
                meta["authors"] = names
        for lnk in m.get("link") or []:
            if isinstance(lnk, dict) and (lnk.get("content-type") or "").lower() == "application/pdf":
                add(lnk.get("URL"), "crossref-pdf-link", 68, version="publishedVersion", status="crossref")
        landing = ((m.get("resource") or {}).get("primary") or {}).get("URL", "")
        if landing:
            meta["landing_url"] = landing
            # Deterministic Springer/Frontiers/MDPI/Nature OA PDF patterns as fallback
            if re.search(r"link\.springer\.com/article/", landing, re.I):
                add(f"https://link.springer.com/content/pdf/{doi}.pdf", "springer-direct", 62, version="publishedVersion")
            elif re.search(r"frontiersin\.org/articles/", landing, re.I):
                add(landing.rstrip("/") + "/pdf", "frontiers-direct", 60, version="publishedVersion", lic="cc-by", status="gold")
            elif re.search(r"mdpi\.com/", landing, re.I):
                add(landing.rstrip("/") + "/pdf", "mdpi-direct", 60, version="publishedVersion", lic="cc-by", status="gold")
            elif re.search(r"nature\.com/articles/", landing, re.I):
                add(landing.rstrip("/") + ".pdf", "nature-direct", 64, version="publishedVersion")

    cands.sort(key=lambda c: c["priority"])
    return meta, cands


def parse_wanted_note(note_path: Path) -> list[dict[str, Any]]:
    """Parse unchecked `- [ ]` entries from house-format `*wanted*.md` notes."""
    text = note_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    items: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None

    for line in lines:
        m_item = re.match(r"^\s*-\s*\[\s*\]\s+(.*)$", line)
        if m_item:
            if cur:
                items.append(cur)
            rest = m_item.group(1)
            slug_m = re.search(r"`([^`]+?)\.pdf`", rest, re.I)
            slug = slug_m.group(1).strip() if slug_m else ""
            # Match single-asterisk *Title*, never bold **slug**
            rest_no_bold = re.sub(r"\*\*.*?\*\*", "", rest)
            title_m = re.search(r"(?<!\*)\*([^*]+)\*(?!\*)", rest_no_bold)
            title = title_m.group(1).strip() if title_m else ""
            ay_m = re.search(r"—\s*([^·*]+?)(?:·|\*|$)", rest)
            authors_year = ay_m.group(1).strip() if ay_m else ""
            venue_m = re.search(r"\(([^()]+)\)\s*$", rest)
            venue = venue_m.group(1).strip() if venue_m else ""
            doi_inline = re.search(r"(10\.\d{4,9}/[^\s\])>`\"']+)", rest)
            cur = {
                "slug": slug,
                "doi": clean_doi(doi_inline.group(1)) if doi_inline else "",
                "title": title,
                "authors_year": authors_year,
                "venue": venue,
                "why_read": "",
                "wanted_note": str(note_path),
            }
            continue

        if re.match(r"^\s*-\s*\[[xX]\]\s+", line):
            if cur:
                items.append(cur)
                cur = None
            continue

        if cur and line.startswith(("  ", "\t")):
            if not cur["doi"]:
                dm = re.search(r"(10\.\d{4,9}/[^\s\])>`\"']+)", line)
                if dm:
                    cur["doi"] = clean_doi(dm.group(1))
            if not cur.get("arxiv_id"):
                aid = extract_arxiv_id(line)
                if aid:
                    cur["arxiv_id"] = aid
            wm = re.search(r"用途[：:]\s*(.+)$", line)
            if wm:
                cur["why_read"] = wm.group(1).strip()
        elif cur and not line.strip():
            items.append(cur)
            cur = None

    if cur:
        items.append(cur)
    return items


def append_provenance(ledger_path: Path, record: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_pdf_to_md(pdf_path: Path, meta: dict[str, Any], overwrite: bool = False) -> bool:
    script = SCRIPT_DIR / "pdf_to_md.py"
    if not script.exists():
        return False
    # Import and call convert_one directly to preserve full metadata in frontmatter
    try:
        from pdf_to_md import convert_one  # noqa: E402

        res = convert_one(pdf_path, meta, overwrite=overwrite, engine="pymupdf")
        return res.get("status") in ("converted", "skipped")
    except Exception as exc:
        print(f"[WARN]  pdf_to_md failed for {pdf_path.name}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch and verify legal Open-Access full texts (lj-evidence v2.1).")
    ap.add_argument("--manifest", help="JSON manifest file ({slug, doi?, arxiv_id?, title?, authors_year?, venue?, known_oa_url?})")
    ap.add_argument("--doi", action="append", default=[], help="Single DOI (repeatable)")
    ap.add_argument("--arxiv", action="append", default=[], help="Single arXiv ID (repeatable)")
    ap.add_argument("--wanted-note", action="append", default=[], help="Read unchecked items from a *wanted*.md file (repeatable)")
    ap.add_argument("--scan-inbox", action="store_true", help="Scan all *wanted*.md files in --inbox-dir and deduplicate by DOI")
    ap.add_argument("--inbox-dir", default=default_inbox_dir(), help="Inbox directory for --scan-inbox")
    ap.add_argument("--out-dir", default=default_papers_dir(), help="Target private papers dir (default: $LJ_PAPERS_DIR or ./papers)")
    ap.add_argument("--wanted-out", default="", help="Optional path to write remaining unresolved _wanted.md")
    ap.add_argument("--email", default=os.environ.get("UNPAYWALL_EMAIL", ""), help="Polite-pool email for Unpaywall/OpenAlex (default: $UNPAYWALL_EMAIL)")
    ap.add_argument("--limit", type=int, default=0, help="Optional cap on number of papers processed")
    ap.add_argument("--dry-run", action="store_true", help="Probe APIs and print ordered candidates without downloading")
    ap.add_argument("--convert", action="store_true", help="Convert newly verified PDFs to page-anchored Markdown immediately")
    ap.add_argument("--jats-fallback", action="store_true", default=True, help="Allow Europe PMC JATS XML structured fallback when OA PDF fails (default: on)")
    ap.add_argument("--no-jats-fallback", action="store_false", dest="jats_fallback", help="Disable JATS XML fallback")
    ap.add_argument("--open-wanted", action="store_true", help="Open remaining unresolved DOIs in your normal desktop browser (max 10 tabs)")
    ap.add_argument("--force", action="store_true", help="Re-download even if verified <slug>.pdf already exists")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing .md files when --convert is set")
    args = ap.parse_args()

    email = (args.email or "").strip()
    if not email:
        print("[INFO]  UNPAYWALL_EMAIL not set; skipping Unpaywall API. Set UNPAYWALL_EMAIL=<your@edu> for higher OA recall.", file=sys.stderr)

    items: list[dict[str, Any]] = []
    if args.manifest:
        raw = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
        items.extend(raw if isinstance(raw, list) else raw.get("papers", []))
    for wn in args.wanted_note:
        wp = Path(wn)
        if wp.exists():
            items.extend(parse_wanted_note(wp))
    if args.scan_inbox:
        inbox = Path(args.inbox_dir)
        if inbox.is_dir():
            for wp in sorted(inbox.glob("*wanted*.md")):
                items.extend(parse_wanted_note(wp))
    for d in args.doi:
        items.append({"doi": clean_doi(d)})
    for a in args.arxiv:
        items.append({"arxiv_id": a.strip()})

    # Deduplicate by DOI / slug when scanning multiple sources
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for it in items:
        key = (clean_doi(it.get("doi") or "").lower()) or (it.get("arxiv_id") or "").lower() or (it.get("slug") or "").lower()
        if key and key in seen_keys:
            continue
        if key:
            seen_keys.add(key)
        deduped.append(it)
    items = deduped
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    if not items:
        print("No inputs given. Pass --manifest, --wanted-note, --scan-inbox, --doi, or --arxiv.", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir = out_dir / "_rejected"
    review_dir = out_dir / "_needs_review"
    acq_dir = out_dir / "_acquisition"
    ledger = out_dir / "_provenance.jsonl"
    today = dt.date.today().isoformat()

    fetched: list[dict[str, Any]] = []
    jats_saved: list[dict[str, Any]] = []
    existing: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []
    wanted: list[dict[str, Any]] = []

    for item in items:
        doi = clean_doi(item.get("doi") or "")
        arxiv_id = extract_arxiv_id(item.get("arxiv_id")) or extract_arxiv_id(doi)
        known_url = item.get("known_oa_url")

        meta, cands = discover_oa_candidates(
            doi=doi,
            email=email or None,
            known_url=known_url,
            arxiv_id=arxiv_id,
        )
        if not doi and meta.get("doi"):
            doi = meta["doi"]

        title = item.get("title") or meta.get("title") or ""
        authors_year = item.get("authors_year") or ""
        first_author = (authors_year or ((meta.get("authors") or ["anon"])[0])).split()[0]
        year = item.get("year") or meta.get("year")
        venue = item.get("venue") or meta.get("venue") or ""
        slug = item.get("slug") or slugify_paper(year, first_author, title or arxiv_id or doi)
        pdf_path = out_dir / f"{slug}.pdf"

        if meta.get("is_retracted"):
            print(f"[WARN]  {slug} is flagged RETRACTED in OpenAlex!")

        if args.dry_run:
            top = ", ".join(f"{c['source_api']}(p{c['priority']})" for c in cands[:6]) or "none"
            pmcid_note = f" [JATS:{meta['pmcid']}]" if meta.get("pmcid") else ""
            print(f"[DRY]   {slug} | doi={doi or arxiv_id or 'NONE'}{pmcid_note} | cands({len(cands)}): {top}")
            continue

        # Stage 0: Revalidate cached local PDF (do NOT blindly trust >=8KB!)
        if pdf_path.exists() and not args.force:
            v = validate_pdf(pdf_path, title=title, doi=doi, authors_year=authors_year, year=year)
            if v["status"] == "verified":
                digest = sha256_bytes(pdf_path.read_bytes())
                print(f"[EXIST] {slug}.pdf verified ({v['pages']}p, {v['bytes']:,} bytes, sha256={digest[:12]})")
                if args.convert and not pdf_path.with_suffix(".md").exists():
                    run_pdf_to_md(pdf_path, {**item, **meta, "slug": slug, "title": title, "authors_year": authors_year, "venue": venue, "doi": doi}, overwrite=args.overwrite)
                existing.append({**item, **meta, "slug": slug, "pdf_path": str(pdf_path), "sha256": digest})
                continue
            print(f"[CACHE-INVALID] {slug}.pdf failed revalidation ({v['status']}: {v['reason']}); re-fetching...")
            target_q = review_dir if v["status"] == "needs-review" else rejected_dir
            target_q.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pdf_path), str(target_q / f"{slug}.cached-invalid.pdf"))

        if not doi and not arxiv_id and not known_url:
            wanted.append({
                "slug": slug, "doi": "", "arxiv_id": "", "title": title or slug,
                "authors_year": authors_year, "venue": venue, "why_read": item.get("why_read") or "",
                "failure_class": "no-doi", "attempts": ["no DOI, arXiv ID, or explicit URL"],
            })
            print(f"[WANT]  {slug} — no-doi")
            continue

        saved = False
        review_item: dict[str, Any] | None = None
        attempts: list[str] = []
        failure_classes: list[str] = []
        expanded_cands = list(cands)
        tried_urls: set[str] = set()
        idx = 0

        while idx < len(expanded_cands) and idx < 18:
            cand = expanded_cands[idx]
            idx += 1
            u = cand["url"]
            if u in tried_urls:
                continue
            tried_urls.add(u)

            data, fclass, detail, scraped = try_download_pdf(
                u,
                referer=meta.get("landing_url") or (f"https://doi.org/{doi}" if doi else ""),
                extra_headers=cand.get("headers") or None,
            )
            attempts.append(f"{cand['source_api']}: {detail}")
            if fclass != "ok":
                failure_classes.append(fclass)
                # Queue 1-level scraped PDF links from repository/landing HTML
                for su in scraped:
                    if su not in tried_urls:
                        expanded_cands.insert(
                            idx,
                            {
                                "url": su,
                                "source_api": f"{cand['source_api']}+scrape",
                                "priority": cand["priority"] + 1,
                                "version": cand.get("version", ""),
                                "license": cand.get("license", ""),
                                "oa_status": cand.get("oa_status", ""),
                                "headers": {},
                            },
                        )
                continue

            # Validate downloaded PDF semantically before accepting
            tmp_pdf = out_dir / f".{slug}.tmp.pdf"
            tmp_pdf.write_bytes(data)
            v = validate_pdf(tmp_pdf, title=title, doi=doi, authors_year=authors_year, year=year)

            if v["status"] == "verified":
                os.replace(tmp_pdf, pdf_path)
                digest = sha256_bytes(data)
                rec = {
                    "slug": slug,
                    "doi": doi,
                    "arxiv_id": arxiv_id or "",
                    "pmcid": meta.get("pmcid") or "",
                    "source_format": "pdf",
                    "is_retracted": meta.get("is_retracted", None),
                    "retraction_status": meta.get("retraction_status", "unknown"),
                    "title": title,
                    "authors_year": authors_year,
                    "venue": venue,
                    "pdf_file": pdf_path.name,
                    "pages": v["pages"],
                    "sha256": digest,
                    "bytes": len(data),
                    "source_url": u,
                    "source_api": cand["source_api"],
                    "oa_status": cand["oa_status"],
                    "version": cand["version"],
                    "license": cand["license"],
                    "verification": {"status": v["status"], "doi_found": v["doi_found"], "title_coverage": v["title_coverage"]},
                    "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "redistribution_note": "Local research copy only; OA access does not grant public redistribution unless license permits.",
                }
                append_provenance(ledger, rec)
                print(f"[OK]    {slug}.pdf <- {cand['source_api']} ({v['pages']}p, {len(data):,} bytes, cov={v['title_coverage']})")
                if args.convert:
                    run_pdf_to_md(pdf_path, {**item, **meta, **rec}, overwrite=args.overwrite)
                fetched.append({**item, **meta, **rec, "pdf_path": str(pdf_path)})
                saved = True
                break

            if v["status"] == "needs-review":
                review_dir.mkdir(parents=True, exist_ok=True)
                dest = review_dir / f"{slug}.pdf"
                os.replace(tmp_pdf, dest)
                attempts.append(f"{cand['source_api']}: needs-review ({v['reason']})")
                failure_classes.append("needs-review")
                review_item = {
                    "slug": slug, "doi": doi, "title": title, "path": str(dest),
                    "reason": v["reason"], "source_api": cand["source_api"], "source_url": u,
                }
                # Continue trying other candidates in case a cleaner verified copy exists!
                continue

            # Rejected (e.g., publisher media kit, wrong article, truncated)
            rejected_dir.mkdir(parents=True, exist_ok=True)
            os.replace(tmp_pdf, rejected_dir / f"{slug}.{cand['source_api']}.pdf")
            attempts.append(f"{cand['source_api']}: rejected ({v['reason']})")
            failure_classes.append("wrong-article" if "wrong-article" in v["reason"] else "truncated-no-eof")

        # JATS XML structured fallback if OA PDF failed but Europe PMC OA PMCID exists
        if not saved and args.jats_fallback and meta.get("pmcid"):
            jres = fetch_jats_xml_markdown(
                meta["pmcid"],
                {**item, **meta, "title": title, "authors_year": authors_year, "venue": venue, "doi": doi},
                out_dir,
                slug,
                email=email,
            )
            if jres:
                rec = {
                    "slug": slug,
                    "doi": doi,
                    "pmcid": meta["pmcid"],
                    "source_format": "jats_xml",
                    "is_retracted": meta.get("is_retracted", None),
                    "retraction_status": meta.get("retraction_status", "unknown"),
                    "title": title,
                    "authors_year": authors_year,
                    "venue": venue,
                    "md_file": Path(jres["md_path"]).name,
                    "xml_sha256": jres["xml_sha256"],
                    "sections": jres["sections"],
                    "source_url": jres["source_url"],
                    "source_api": "europepmc-jats-xml",
                    "oa_status": "gold/pmc",
                    "version": "publishedVersion",
                    "license": meta.get("epmc_license") or "pmc-oa",
                    "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "redistribution_note": "Structured JATS XML (no physical PDF page anchors).",
                }
                append_provenance(ledger, rec)
                print(f"[JATS]  {slug}.md <- europepmc-jats-xml ({jres['sections']} sections, {meta['pmcid']}; no PDF page anchors)")
                jats_saved.append(rec)
                saved = True

        if not saved:
            if review_item:
                needs_review.append(review_item)
                primary_class = "needs-review"
            elif "waf-html" in failure_classes:
                primary_class = "waf-html"
            elif "paywall-html" in failure_classes:
                primary_class = "paywall-html"
            elif "wrong-article" in failure_classes:
                primary_class = "wrong-article"
            elif "landing-html" in failure_classes:
                primary_class = "landing-html"
            elif "network" in failure_classes:
                primary_class = "network"
            else:
                primary_class = "no-oa"

            print(f"[WANT]  {slug} ({primary_class}) — doi={doi or arxiv_id} ({len(attempts)} attempts)")
            wanted.append({
                "slug": slug,
                "doi": doi,
                "arxiv_id": arxiv_id or "",
                "title": title or slug,
                "authors_year": authors_year,
                "venue": venue,
                "why_read": item.get("why_read") or "",
                "failure_class": primary_class,
                "attempts": attempts or ["no legal OA PDF URL returned by arXiv/EPMC/OpenAIRE/Unpaywall/OpenAlex/S2"],
            })

    if args.dry_run:
        return 0

    # Write acquisition report
    acq_dir.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "summary": {
            "fetched_pdf": len(fetched),
            "fetched_jats": len(jats_saved),
            "existing_verified": len(existing),
            "needs_review": len(needs_review),
            "wanted": len(wanted),
        },
        "fetched": fetched,
        "jats_saved": jats_saved,
        "needs_review": needs_review,
        "wanted": wanted,
    }
    (acq_dir / "acquisition-report.json").write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rep_lines = [
        f"# Acquisition Report ({today})",
        "",
        f"- Verified PDFs fetched: **{len(fetched)}**",
        f"- JATS XML fulltexts saved: **{len(jats_saved)}**",
        f"- Existing verified PDFs reused: **{len(existing)}**",
        f"- Routed to `_needs_review/`: **{len(needs_review)}**",
        f"- Remaining wanted: **{len(wanted)}**",
        "",
    ]
    if wanted:
        rep_lines.append("## Remaining Wanted by Failure Class")
        for w in wanted:
            rep_lines.append(f"- `{w['failure_class']}` · `{w['slug']}` · https://doi.org/{w['doi']}" if w["doi"] else f"- `{w['failure_class']}` · `{w['slug']}`")
    (acq_dir / "acquisition-report.md").write_text("\n".join(rep_lines) + "\n", encoding="utf-8")

    if args.wanted_out and wanted:
        wp = Path(args.wanted_out)
        wp.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "---",
            f"updated: {today}",
            "role: wanted-papers",
            "privacy: private",
            "---",
            "",
            f"# 待补全文文献清单（{today}）",
            "",
            f"以下文献经合法 OA 渠道（arXiv / Europe PMC / OpenAIRE / Unpaywall / OpenAlex / Semantic Scholar）未能直接取得已校验全文 PDF。请通过大学图书馆 / Zotero Connector 下载后，运行 `ingest_local.py` 自动校验、规范命名入 `{out_dir}`、转页码 Markdown 并勾销本清单：",
            "",
        ]
        for w in wanted:
            doi_link = f"https://doi.org/{w['doi']}" if w["doi"] else (f"https://arxiv.org/abs/{w['arxiv_id']}" if w["arxiv_id"] else "(无 DOI)")
            lines.append(f"- [ ] **`{w['slug']}.pdf`** — {w['authors_year']} · *{w['title']}* ({w['venue']})")
            lines.append(f"  - DOI / 出版社直链：{doi_link}")
            if w["why_read"]:
                lines.append(f"  - 用途：{w['why_read']}")
            lines.append(f"  - 失败分类：`{w['failure_class']}` · 检索记录：`{'; '.join(w['attempts'][:3])}`")
        lines.append("")
        wp.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote wanted list: {wp} ({len(wanted)} papers)")

    if args.open_wanted and wanted:
        to_open = [w for w in wanted if w.get("doi")][:10]
        print(f"[OPEN]  Opening {len(to_open)} unresolved DOI(s) in default browser for legal library/Zotero retrieval...")
        for w in to_open:
            webbrowser.open_new_tab(f"https://doi.org/{w['doi']}")

    print(
        f"\nSummary: fetched_pdf={len(fetched)}, fetched_jats={len(jats_saved)}, "
        f"existing={len(existing)}, needs_review={len(needs_review)}, wanted={len(wanted)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
