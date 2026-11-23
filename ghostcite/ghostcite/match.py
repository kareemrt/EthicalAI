"""Decide whether a registry record is the work the text actually describes."""
from __future__ import annotations

import re
import unicodedata

from .models import Record

_STOP = set(
    "a an and are as at be by for from has in into is it its of on or that the this to via "
    "was were what when which with without towards toward using based study analysis new".split()
)
_ID = re.compile(r"https?://\S+|\b10\.\d{4,9}/\S+|arxiv:\S+|isbn\S*|pmid:?\s*\d+", re.I)


def words(text: str) -> set[str]:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]+", text) if len(w) > 2 and w not in _STOP}


def coverage(title: str, context: str) -> float:
    """Share of the record title's meaningful words that appear in the citing text."""
    t = words(title)
    return len(t & words(context)) / len(t) if t else 0.0


def describes(context: str, min_words: int = 4) -> bool:
    """True if the citing line says enough (beyond the identifier) to compare against."""
    return len(words(_ID.sub(" ", context))) >= min_words


def compare(record: Record, context: str, threshold: float = 0.5) -> str | None:
    """Return a mismatch reason, or None if the record plausibly matches the context."""
    if not record.title or not describes(context):
        return None
    score = coverage(record.title, context)
    if score >= threshold:
        return None
    reason = f"resolves to a different work: \"{_short(record.title)}\""
    years = {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", _ID.sub(" ", context))}
    if record.year and years and all(abs(y - record.year) > 1 for y in years):
        reason += f" ({record.year})"
    return reason


def _short(s: str, n: int = 80) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"
