"""Text utilities: normalisation, sentence spans, tokens, numbers, quotes.

Everything here is deliberately simple, deterministic and dependency-free.
"""
import re
import unicodedata

# Words that carry little meaning on their own. Negations and quantifiers
# ("all", "only", "some") are *not* here: they change what a claim asserts.
STOPWORDS = frozenset("""
a an the and or but if of to in on at by for with from as is are was were be been
being it its this that these those which who whom whose what when where why how
than then so such there their they them he she his her we our you your i me my
has have had do does did will would shall should can could may might must also
into over under about after before between during through per via just very
other both either own same too here up out off
""".split())

NEGATIONS = re.compile(
    r"\b(?:not|no|never|none|nor|neither|nobody|nothing|cannot|without)\b|n't\b"
)

_NEGATION_WORDS = frozenset("not no never none nor neither nobody nothing cannot without".split())

ABBREVIATIONS = frozenset(
    "e.g i.e mr mrs ms dr prof st vs etc inc ltd jr sr no fig u.s approx est dept".split()
)

CITATION = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")
_BOUNDARY = re.compile(r"[.!?]+(?:[\"')\]]|\[\d[\d,\s–-]*\])*(?=\s|$)|\n")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_NUMBER = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])\d+(?:\.\d+)?")
_QUOTE = re.compile(r'"([^"\n]{4,})"')
_WORD = re.compile(r"[a-z]+|\d+(?:\.\d+)?")


def normalize(s: str) -> str:
    """Unicode-normalise and straighten typographic quotes and dashes."""
    s = unicodedata.normalize("NFKC", s)
    return (s.replace("“", '"').replace("”", '"')
             .replace("‘", "'").replace("’", "'"))


def sentence_spans(s: str):
    """Yield (start, end) offsets of sentences / list items in ``s``."""
    start = 0
    for m in _BOUNDARY.finditer(s):
        head = s[start:m.start()]
        if m.group() != "\n":
            last = re.search(r"([\w.]+)$", head)
            word = last.group(1).lower().rstrip(".") if last else ""
            if word in ABBREVIATIONS or (len(word) == 1 and word.isalpha()):
                continue
            if head.strip().isdigit():  # "1." at the start of a numbered list
                continue
        span = _trim(s, start, m.end())
        if span:
            yield span
        start = m.end()
    span = _trim(s, start, len(s))
    if span:
        yield span


def _trim(s, a, b):
    seg = s[a:b]
    bullet = _BULLET.match(seg)
    if bullet:
        a += bullet.end()
        seg = s[a:b]
    lead = len(seg) - len(seg.lstrip())
    trail = len(seg) - len(seg.rstrip())
    a, b = a + lead, b - trail
    return (a, b) if b > a else None


def citations(s: str):
    """Return the 1-based source numbers cited as [1], [2, 3] or [1-3]."""
    found = []
    for group in CITATION.findall(s):
        for part in re.split(r"\s*,\s*", group):
            bounds = re.split(r"\s*[–-]\s*", part)
            lo, hi = int(bounds[0]), int(bounds[-1])
            found.extend(range(lo, hi + 1))
    return sorted(set(found))


def strip_citations(s: str) -> str:
    return CITATION.sub(" ", s)


def stem(w: str) -> str:
    """A tiny suffix stripper: enough to match 'replaced' with 'replacement'."""
    if w.isdigit() or len(w) <= 3:
        return w
    for suf, rep in (("ies", "y"), ("ied", "y"), ("ment", ""), ("ing", ""), ("ed", ""),
                     ("es", ""), ("ly", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: len(w) - len(suf)] + rep
            break
    return w[:-1] if w.endswith("e") and len(w) > 4 else w


def _words(s: str):
    s = re.sub(r"(?<=\d),(?=\d{3})", "", strip_citations(s).lower())
    return [w for w in _WORD.findall(s)
            if w not in STOPWORDS and w not in _NEGATION_WORDS and (len(w) > 1 or w.isdigit())]


def tokens(s: str):
    """Content tokens: lower-cased, stop-words removed, lightly stemmed.

    Negation words are dropped here too; polarity is checked separately so
    that "does not remove" and "removes" can be recognised as a contradiction.
    """
    return [stem(w) for w in _words(s)]


def missing_words(s: str, present: set):
    """Original words of ``s`` whose tokens are not in ``present``."""
    out = []
    for w in _words(s):
        if stem(w) not in present and w not in out:
            out.append(w)
    return out


def numbers(s: str):
    """Numbers as canonical strings: '18,412' -> '18412', '70.0' -> '70'."""
    out = set()
    for n in _NUMBER.findall(strip_citations(s)):
        n = n.replace(",", "")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n)
    return out


def quotes(s: str):
    return _QUOTE.findall(s)


def negated(s: str) -> bool:
    return bool(NEGATIONS.search(s.lower()))


def squash(s: str) -> str:
    """Lower-case, drop punctuation, collapse whitespace (for verbatim checks)."""
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))
