"""Text primitives: sentences, words, syllables.

Everything here returns character offsets into the original text, so findings
can be highlighted exactly where they occur.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")

# Abbreviations that end in "." but do not end a sentence.
_ABBREV = {
    "mr", "mrs", "ms", "dr", "st", "no", "vs", "etc", "e.g", "i.e", "u.s",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct",
    "nov", "dec", "inc", "ltd", "dept", "ave", "apt", "p.o", "a.m", "p.m",
}

# A candidate boundary: terminal punctuation followed by whitespace, a blank
# line, or a line break.
_CANDIDATE = re.compile(r"[.!?][\"')\]]*\s+|\n\s*\n|\n")


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    text: str

    @property
    def words(self) -> list[str]:
        return WORD.findall(self.text)

    @property
    def is_fragment(self) -> bool:
        """Headings, salutations and labels: short and unpunctuated."""
        stripped = self.text.rstrip()
        return len(self.words) <= 6 and not stripped.endswith((".", "!", "?"))


def _ends_sentence(text: str, m: re.Match) -> bool:
    chunk = m.group(0)
    if chunk[0] in ".!?":
        # Ignore "Dr. Smith", "e.g. this", "Jan. 5".
        before = text[: m.start()].rsplit(None, 1)
        last = before[-1].lower().rstrip(".") if before else ""
        if last.strip("(\"'") in _ABBREV or re.fullmatch(r"[a-z]", last):
            return False
        nxt = text[m.end(): m.end() + 1]
        return not nxt or not nxt.islower()
    if "\n" in chunk.strip(" \t") and chunk.count("\n") > 1:
        return True  # blank line = paragraph break
    # Single line break: a boundary unless the line was hard-wrapped mid-sentence.
    line_start = text.rfind("\n", 0, m.start()) + 1
    line = text[line_start: m.start()].rstrip()
    if not line:
        return True
    if re.match(r"\s*(dear|hello|hi)\b", line, re.I):
        return True
    nxt = text[m.end(): m.end() + 1]
    return not (line[-1].islower() or line[-1] == ",") or nxt in "-*•"


def sentences(text: str) -> list[Sentence]:
    out, start = [], 0
    for m in _CANDIDATE.finditer(text):
        if not _ends_sentence(text, m):
            continue
        end = m.start() + (1 if text[m.start()] in ".!?" else 0)
        # Keep closing quotes/brackets with the sentence.
        while end < len(text) and text[end] in "\"')]":
            end += 1
        _push(out, text, start, end)
        start = m.end()
    _push(out, text, start, len(text))
    return out


def _push(out: list[Sentence], text: str, start: int, end: int) -> None:
    chunk = text[start:end]
    lead = len(chunk) - len(chunk.lstrip())
    chunk = chunk.strip()
    if WORD.search(chunk):
        out.append(Sentence(start + lead, start + lead + len(chunk), chunk))


def syllables(word: str) -> int:
    """Classic vowel-group heuristic; good to within ~1 syllable for English."""
    w = word.lower().strip("'’-")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|[^laeiouy]ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))
