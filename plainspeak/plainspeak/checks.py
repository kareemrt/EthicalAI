"""The checks. Each one is a small pure function over text -> findings.

Two kinds of output:
  * Finding  - a located problem (span + message + suggestion), highlightable.
  * Essential - a yes/no question every notice must answer for the reader.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .text import WORD, Sentence, syllables

LONG_SENTENCE = 25  # words; most plain-language guides cap at 20-25.


@dataclass(frozen=True)
class Finding:
    kind: str  # "jargon" | "passive" | "long"
    start: int
    end: int
    text: str
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class Essential:
    key: str
    question: str
    ok: bool
    evidence: str = ""
    advice: str = ""


# --------------------------------------------------------------------------
# Readability
# --------------------------------------------------------------------------

@dataclass
class Readability:
    words: int = 0
    sentences: int = 0
    syllables: int = 0
    complex_words: int = 0  # 3+ syllables
    grade: float = 0.0  # Flesch-Kincaid grade level
    ease: float = 100.0  # Flesch reading ease, 0-100
    avg_sentence: float = 0.0
    you_per_100: float = 0.0
    lengths: list[int] = field(default_factory=list)


def readability(sents: list[Sentence]) -> Readability:
    body = [s for s in sents if not s.is_fragment] or sents
    words = [w for s in body for w in s.words]
    r = Readability(words=len(words), sentences=len(body))
    if not words:
        return r
    sylls = [syllables(w) for w in words]
    r.syllables = sum(sylls)
    r.complex_words = sum(1 for n in sylls if n >= 3)
    wps, spw = len(words) / len(body), r.syllables / len(words)
    r.avg_sentence = round(wps, 1)
    r.grade = round(max(0.0, 0.39 * wps + 11.8 * spw - 15.59), 1)
    r.ease = round(min(100.0, max(0.0, 206.835 - 1.015 * wps - 84.6 * spw)), 1)
    you = sum(1 for w in words if w.lower() in {"you", "your", "yours", "you're", "you’re"})
    r.you_per_100 = round(100 * you / len(words), 1)
    r.lengths = [len(s.words) for s in body]
    return r


# --------------------------------------------------------------------------
# Jargon
# --------------------------------------------------------------------------

@lru_cache(maxsize=None)
def jargon_table() -> tuple[dict[str, str], re.Pattern]:
    table = {}
    path = Path(__file__).with_name("data") / "jargon.tsv"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            phrase, plain = line.split("\t", 1)
            table[phrase.lower()] = plain.strip()
    # Longest first so "in order to" wins over "order".
    alts = sorted(table, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(a) for a in alts) + r")\b", re.I)
    return table, pattern


def in_name(text: str, m: re.Match) -> bool:
    """True for words inside a Title Case name, e.g. "Nutrition Assistance Program"."""
    word = m.group(0)
    if not word[0].isupper() or word.isupper():
        return False
    prev = re.search(r"([A-Za-z]+)[ \t]+$", text[: m.start()])
    nxt = re.match(r"[ \t]+([A-Za-z]+)", text[m.end():])
    return bool((prev and prev.group(1)[0].isupper()) or (prev and nxt and nxt.group(1)[0].isupper()))


def find_jargon(text: str) -> list[Finding]:
    table, pattern = jargon_table()
    out = []
    for m in pattern.finditer(text):
        if in_name(text, m):
            continue
        plain = table[m.group(0).lower()]
        msg = f"Bureaucratic word: “{m.group(0)}”"
        out.append(Finding("jargon", m.start(), m.end(), m.group(0), msg, plain))
    return out


# --------------------------------------------------------------------------
# Passive voice
# --------------------------------------------------------------------------

_IRREGULAR = (
    "been|born|bought|brought|built|caught|chosen|done|drawn|driven|found|"
    "forgotten|given|gone|held|hidden|kept|known|laid|left|lent|lost|made|"
    "meant|met|paid|put|read|run|said|seen|sent|set|shown|sold|spent|taken|"
    "told|thought|understood|withheld|won|written"
)
_PASSIVE = re.compile(
    r"\b(am|is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(?:not\s+)?"
    rf"(\w+ed|{_IRREGULAR})\b(?:\s+by\b)?",
    re.I,
)
# Common "-ed" adjectives that read fine after "is/are".
_NOT_PASSIVE = {"interested", "concerned", "tired", "married", "pleased", "based", "located", "related"}


def find_passive(text: str) -> list[Finding]:
    out = []
    for m in _PASSIVE.finditer(text):
        if m.group(2).lower() in _NOT_PASSIVE:
            continue
        out.append(Finding(
            "passive", m.start(), m.end(), m.group(0),
            "Passive voice hides who acts.",
            "Say who does it: “We sent…”, “You must…”",
        ))
    return out


# --------------------------------------------------------------------------
# Long sentences
# --------------------------------------------------------------------------

def find_long(sents: list[Sentence], limit: int = LONG_SENTENCE) -> list[Finding]:
    return [
        Finding("long", s.start, s.end, s.text,
                f"{len(s.words)} words in one sentence (aim for under {limit}).",
                "Split into two or three short sentences, or use a list.")
        for s in sents if len(s.words) > limit
    ]


# --------------------------------------------------------------------------
# Essentials: can the reader act on this notice?
# --------------------------------------------------------------------------

_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_DEADLINE = re.compile(
    rf"\b(?:{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?"
    r"|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}"
    r"|within\s+\w+\s+(?:calendar\s+|business\s+)?days)\b",
    re.I,
)
_CONTACT = re.compile(
    r"(?:\(?\b\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}\b|1-8\d\d-\w{3}-\w{4}"
    r"|\b[\w.+-]+@[\w-]+\.\w[\w.]*\w|\b(?:https?://|www\.)[^\s,;)]*[^\s.,;)])",
    re.I,
)
_ACTION = re.compile(
    r"(?:^|[.!?:•*-]\s*|\n\s*(?:\d+[.)]\s*)?)(call|send|sign|bring|visit|go|"
    r"fill|mail|return|submit|contact|complete|upload|email|text|apply|ask|"
    r"tell|show|log in|write)\b",
    re.I | re.M,
)
_RIGHTS = re.compile(r"\b(appeal|fair hearing|hearing|disagree|review of this decision|reconsideration)\b", re.I)


def essentials(text: str, rd: Readability) -> list[Essential]:
    def first(rx: re.Pattern) -> str:
        m = rx.search(text)
        return (m.group(m.lastindex or 0)).strip() if m else ""

    deadline, contact, action, rights = (first(r) for r in (_DEADLINE, _CONTACT, _ACTION, _RIGHTS))
    return [
        Essential("deadline", "Is there a clear date to act by?", bool(deadline), deadline,
                  "State the exact date: “by March 3, 2027”, not “promptly”."),
        Essential("action", "Does it say exactly what to do?", bool(action), action,
                  "Start a sentence with a verb: “Call us”, “Send a copy of…”."),
        Essential("contact", "Is there a way to get help?", bool(contact), contact,
                  "Give a phone number, hours, and a website."),
        Essential("rights", "Does it explain how to disagree or appeal?", bool(rights), rights,
                  "Tell readers they can ask for a review, and how."),
        Essential("you", "Does it speak to the reader as “you”?", rd.you_per_100 >= 2.0,
                  f"{rd.you_per_100} per 100 words",
                  "Write to the person: “You must…” instead of “The applicant shall…”."),
    ]
