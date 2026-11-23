"""Checks that need no network: checksums, date sanity and syntax.

Each check returns a reason string when the citation *cannot* be real, else None.
"""
from __future__ import annotations

import datetime as _dt
import re
from urllib.parse import urlparse

from .models import Citation


def isbn_problem(isbn: str) -> str | None:
    if len(isbn) == 10:
        if not re.fullmatch(r"\d{9}[\dX]", isbn):
            return "ISBN-10 contains invalid characters"
        digits = [10 if c == "X" else int(c) for c in isbn]
        if sum((10 - i) * d for i, d in enumerate(digits)) % 11:
            return "ISBN-10 checksum fails"
        return None
    if len(isbn) == 13:
        if not isbn.isdigit() or not isbn.startswith(("978", "979")):
            return "ISBN-13 must be 13 digits starting with 978 or 979"
        if sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn)) % 10:
            return "ISBN-13 checksum fails"
        return None
    return f"ISBN has {len(isbn)} digits (expected 10 or 13)"


def arxiv_problem(arxiv_id: str, today: _dt.date | None = None) -> str | None:
    today = today or _dt.date.today()
    m = re.fullmatch(r"(\d{2})(\d{2})\.(\d{4,5})", arxiv_id)
    if not m:
        m_old = re.fullmatch(r"[a-z\-]+(?:\.[a-z]{2})?/(\d{2})(\d{2})\d{3}", arxiv_id, re.I)
        if not m_old:
            return "not a valid arXiv identifier"
        yy, mm = int(m_old.group(1)), int(m_old.group(2))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if not 1 <= mm <= 12:
            return f"month {mm:02d} does not exist"
        if year > 2007 or (year == 2007 and mm > 3):
            return "old-style arXiv IDs were retired in March 2007"
        return None
    yy, mm, num = int(m.group(1)), int(m.group(2)), m.group(3)
    year = 2000 + yy
    if not 1 <= mm <= 12:
        return f"month {mm:02d} does not exist"
    if (year, mm) < (2007, 4):
        return "new-style arXiv IDs start in April 2007"
    if (year, mm) > (today.year, today.month):
        return f"dated {year}-{mm:02d}, which is in the future"
    if year >= 2015 and len(num) != 5:
        return "arXiv IDs since 2015 use a 5-digit sequence number"
    if year < 2015 and len(num) != 4:
        return "arXiv IDs before 2015 use a 4-digit sequence number"
    return None


def doi_problem(doi: str) -> str | None:
    prefix, _, suffix = doi.partition("/")
    if not re.fullmatch(r"10\.\d{4,9}(\.\d+)*", prefix):
        return "DOI prefix is malformed"
    if not suffix:
        return "DOI has an empty suffix"
    return None


_PLACEHOLDERS = {"example.com", "example.org", "example.net", "localhost"}


def url_problem(url: str) -> str | None:
    p = urlparse(url)
    host = p.hostname or ""
    if "." not in host or host.endswith("."):
        return "URL has no valid host"
    base = host.removeprefix("www.")
    if base.endswith((".example", ".invalid", ".test", ".localhost")) or base in _PLACEHOLDERS:
        return "URL points to a reserved placeholder domain"
    return None


_ANY_YEAR = re.compile(r"(?<![\d/.\-])((?:19|20)\d{2})(?![\d/.\-])")
_PAREN_YEAR = re.compile(r"\(((?:19|20)\d{2})[a-z]?\)")


def year_problem(context: str, bare: bool, today: _dt.date | None = None) -> str | None:
    """A publication year after today. Prose like "by 2030" is ignored: we only trust years
    written as "(2027)" — or any year at all inside a bare reference-list entry."""
    today = today or _dt.date.today()
    years = (_ANY_YEAR if bare else _PAREN_YEAR).findall(context)
    future = [y for y in map(int, years) if y > today.year]
    return f"cites the year {future[0]}, which is in the future" if future else None


def check(c: Citation, today: _dt.date | None = None) -> str | None:
    """Return why `c` is impossible, or None if it passes every offline check."""
    problem = {
        "isbn": lambda: isbn_problem(c.value),
        "arxiv": lambda: arxiv_problem(c.value, today),
        "doi": lambda: doi_problem(c.value),
        "url": lambda: url_problem(c.value),
        "pmid": lambda: None if c.value.lstrip("0") else "PMID cannot be zero",
        "ref": lambda: None,
    }[c.kind]()
    bare = c.kind == "ref"
    return problem or year_problem(c.value if bare else c.context, bare, today)
