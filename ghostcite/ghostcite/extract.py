"""Find citations in free text: DOIs, arXiv IDs, ISBNs, PMIDs, URLs and bare references."""
from __future__ import annotations

import re

from .models import Citation

_TRAIL = ".,;:)]}>'\"”’"

DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
ARXIV = re.compile(
    r"(?:arxiv(?:\.org/(?:abs|pdf)/|:\s?))"
    r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?",
    re.I,
)
ISBN = re.compile(r"\bISBN(?:-1[03])?:?\s*((?:97[89][\s\-]?)?(?:\d[\s\-]?){9}[\dXx])\b")
PMID = re.compile(r"\bPMID:?\s*(\d{1,8})\b")
URL = re.compile(r"https?://[^\s<>\"'`]+", re.I)

# A "bare" reference: a line in a reference list that names a year but no identifier.
_LIST_MARK = re.compile(r"^\s*(?:\[\d+\]|\d+[.)]|[-*•])\s+")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_REF_HEADING = re.compile(r"^\s*#*\s*(references|bibliography|sources|works cited|citations)\b", re.I)


def _clean(token: str) -> str:
    token = token.rstrip(_TRAIL)
    # Keep balanced parentheses that belong to the identifier, e.g. 10.1016/S0140-6736(20)30183-5
    while token.count("(") < token.count(")") and token.endswith(")"):
        token = token[:-1]
    return token


def _looks_like_reference(line: str, in_refs: bool) -> bool:
    text = _LIST_MARK.sub("", line).strip()
    if len(text.split()) < 6 or not _YEAR.search(text):
        return False
    return in_refs or bool(_LIST_MARK.match(line))


def _context(lines: list[str], i: int) -> str:
    """The citing text: a list item on its own, or prose joined with its neighbouring lines."""
    if _LIST_MARK.match(lines[i]):
        return lines[i].strip()
    lo, hi = i, i
    if i > 0 and lines[i - 1].strip() and not _LIST_MARK.match(lines[i - 1]):
        lo = i - 1
    if i + 1 < len(lines) and lines[i + 1].strip() and not _LIST_MARK.match(lines[i + 1]):
        hi = i + 1
    return " ".join(l.strip() for l in lines[lo:hi + 1] if not l.startswith("#"))


def extract(text: str) -> list[Citation]:
    """Return every citation in `text`, de-duplicated, in reading order."""
    lines = text.splitlines()
    found: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    in_refs = False

    def add(kind: str, value: str, n: int) -> None:
        key = (kind, value.lower())
        if key not in seen:
            seen.add(key)
            found.append(Citation(kind, value, n, _context(lines, n - 1)))

    for n, line in enumerate(lines, 1):
        if _REF_HEADING.match(line):
            in_refs = True
            continue
        if line.startswith("#"):
            in_refs = False

        spans: list[tuple[int, int]] = []  # regions already claimed by an identifier

        for m in DOI.finditer(line):
            add("doi", _clean(m.group(1)), n)
            spans.append(m.span())
        for m in ARXIV.finditer(line):
            add("arxiv", m.group(1), n)
            spans.append(m.span())
        for m in ISBN.finditer(line):
            add("isbn", re.sub(r"[\s\-]", "", m.group(1)).upper(), n)
            spans.append(m.span())
        for m in PMID.finditer(line):
            add("pmid", m.group(1), n)
            spans.append(m.span())
        for m in URL.finditer(line):
            # doi.org / arxiv.org links were already captured as identifiers above
            if not any(s <= m.start() < e or m.start() <= s < m.end() for s, e in spans):
                add("url", _clean(m.group(0)), n)
                spans.append(m.span())

        if not spans and _looks_like_reference(line, in_refs):
            add("ref", _LIST_MARK.sub("", line).strip(), n)

    return found
