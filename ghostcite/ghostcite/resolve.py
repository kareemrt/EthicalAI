"""Online lookups against open scholarly registries.

Every resolver takes a Citation and an HTTP `get` function and returns a Finding.
The `get` function is injectable, so tests run fully offline.
"""
from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable
from urllib.parse import quote, urlencode

from . import match
from .models import (MISMATCH, NOT_FOUND, UNCHECKED, UNMATCHED, VERIFIED, Citation, Finding,
                     Record)

USER_AGENT = "ghostcite/0.1 (open-source citation checker)"
Get = Callable[[str], "tuple[int, str]"]


class Offline(Exception):
    """Raised when the network is unavailable, so the citation stays unchecked."""


def http_get(url: str, timeout: float = 12.0) -> tuple[int, str]:
    """Minimal GET: returns (status, body). Status 0 means the host does not resolve."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.gaierror):
            return 0, ""
        raise Offline(f"could not connect: {_short_reason(e.reason)}") from e
    except (TimeoutError, socket.timeout, ConnectionError) as e:
        raise Offline(str(e)) from e


def _short_reason(reason: object) -> str:
    return str(reason).split(":")[0][:40]


def _verdict(c: Citation, rec: Record) -> Finding:
    why = match.compare(rec, c.context)
    if why:
        return Finding(c, MISMATCH, why, rec)
    return Finding(c, VERIFIED, f"found in {rec.source}", rec)


# ── DOI ──────────────────────────────────────────────────────────────────────

def doi(c: Citation, get: Get) -> Finding:
    status, body = get("https://api.crossref.org/works/" + quote(c.value, safe="/"))
    if status == 200:
        m = json.loads(body)["message"]
        return _verdict(c, _crossref_record(m))
    # Not every DOI is Crossref (e.g. DataCite datasets) — ask the DOI system itself.
    status, body = get("https://doi.org/api/handles/" + quote(c.value, safe="/"))
    if status == 200 and json.loads(body).get("responseCode") == 1:
        return Finding(c, VERIFIED, "registered at doi.org (no metadata to compare)")
    if status in (200, 404):
        return Finding(c, NOT_FOUND, "DOI is not registered at doi.org")
    return Finding(c, UNCHECKED, f"doi.org returned HTTP {status}")


def _crossref_record(m: dict) -> Record:
    parts = (m.get("issued") or {}).get("date-parts") or [[None]]
    return Record(
        title=" ".join(m.get("title") or []),
        year=parts[0][0],
        authors=[a.get("family", "") for a in m.get("author", [])][:5],
        source="Crossref",
        id=m.get("DOI", ""),
    )


# ── arXiv ────────────────────────────────────────────────────────────────────

_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def arxiv(c: Citation, get: Get) -> Finding:
    status, body = get("https://export.arxiv.org/api/query?" + urlencode({"id_list": c.value}))
    if status != 200:
        return Finding(c, UNCHECKED, f"arXiv returned HTTP {status}")
    entry = ET.fromstring(body).find("a:entry", _ATOM)
    title = entry.findtext("a:title", "", _ATOM) if entry is not None else ""
    if entry is None or not title or "/api/errors" in entry.findtext("a:id", "", _ATOM):
        return Finding(c, NOT_FOUND, "no such arXiv paper")
    rec = Record(
        title=" ".join(title.split()),
        year=int(entry.findtext("a:published", "0", _ATOM)[:4] or 0) or None,
        authors=[a.findtext("a:name", "", _ATOM).split()[-1]
                 for a in entry.findall("a:author", _ATOM)][:5],
        source="arXiv",
        id=c.value,
    )
    return _verdict(c, rec)


# ── ISBN ─────────────────────────────────────────────────────────────────────

def isbn(c: Citation, get: Get) -> Finding:
    status, body = get(f"https://openlibrary.org/isbn/{c.value}.json")
    if status == 404:
        return Finding(c, UNMATCHED, "not in Open Library (its coverage is incomplete)")
    if status != 200:
        return Finding(c, UNCHECKED, f"Open Library returned HTTP {status}")
    data = json.loads(body)
    year = re.search(r"\b(1[5-9]|20)\d{2}\b", data.get("publish_date", ""))
    rec = Record(title=data.get("title", ""), year=int(year.group(0)) if year else None,
                 source="Open Library", id=c.value)
    return _verdict(c, rec)


# ── PubMed ───────────────────────────────────────────────────────────────────

def pmid(c: Citation, get: Get) -> Finding:
    q = urlencode({"db": "pubmed", "id": c.value, "retmode": "json"})
    status, body = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + q)
    if status != 200:
        return Finding(c, UNCHECKED, f"PubMed returned HTTP {status}")
    item = json.loads(body).get("result", {}).get(c.value, {})
    if not item or "error" in item:
        return Finding(c, NOT_FOUND, "no such PubMed record")
    year = re.match(r"\d{4}", item.get("pubdate", ""))
    rec = Record(title=item.get("title", "").rstrip("."),
                 year=int(year.group(0)) if year else None,
                 authors=[a["name"].split()[0] for a in item.get("authors", [])][:5],
                 source="PubMed", id=c.value)
    return _verdict(c, rec)


# ── URL ──────────────────────────────────────────────────────────────────────

def url(c: Citation, get: Get) -> Finding:
    status, _ = get(c.value)
    if status == 0:
        return Finding(c, NOT_FOUND, "domain does not exist")
    if status in (404, 410):
        return Finding(c, NOT_FOUND, f"page does not exist (HTTP {status})")
    if 200 <= status < 400:
        return Finding(c, VERIFIED, f"page is live (HTTP {status})")
    return Finding(c, UNCHECKED, f"site returned HTTP {status} (may block automated checks)")


# ── Bare references (no identifier) ──────────────────────────────────────────

def ref(c: Citation, get: Get) -> Finding:
    q = urlencode({"query.bibliographic": c.value[:300], "rows": 3,
                   "select": "DOI,title,issued,author"})
    status, body = get("https://api.crossref.org/works?" + q)
    if status != 200:
        return Finding(c, UNCHECKED, f"Crossref search returned HTTP {status}")
    items = json.loads(body)["message"].get("items", [])
    best = max((_crossref_record(m) for m in items),
               key=lambda r: match.coverage(r.title, c.value), default=None)
    if best and match.coverage(best.title, c.value) >= 0.8:
        return Finding(c, VERIFIED, f"matches doi:{best.id} in Crossref", best)
    near = f"; closest: \"{match._short(best.title, 60)}\"" if best and best.title else ""
    return Finding(c, UNMATCHED, "no close match in Crossref" + near, best)


RESOLVERS = {"doi": doi, "arxiv": arxiv, "isbn": isbn, "pmid": pmid, "url": url, "ref": ref}
