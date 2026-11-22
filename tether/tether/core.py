"""The checker: split an answer into claims and look for evidence in sources.

Scoring is IDF-weighted coverage: how much of a claim's *informative*
vocabulary appears in a single source passage. Words that never occur in the
sources get the highest weight, so invented details pull the score down hard.
On top of that score, four targeted checks catch the failure modes that
matter most in practice: fabricated quotes, invented numbers, flipped
negations and wrong citations.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from . import text

SUPPORTED, WEAK, UNSUPPORTED, SKIPPED = "supported", "weak", "unsupported", "skipped"
_RANK = {SUPPORTED: 0, WEAK: 1, UNSUPPORTED: 2}


@dataclass
class Source:
    name: str
    text: str


@dataclass
class Passage:
    source: int          # 0-based index into the source list
    start: int           # character offsets inside that source
    end: int
    text: str


@dataclass
class Claim:
    text: str
    start: int           # character offsets inside the answer
    end: int
    verdict: str = SKIPPED
    score: float = 0.0
    evidence: Passage = None
    cited: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    missing: list = field(default_factory=list)   # claim words absent from evidence

    def cap(self, verdict, flag):
        """Record a flag and downgrade the verdict to at most ``verdict``."""
        self.flags.append(flag)
        if _RANK[verdict] > _RANK[self.verdict]:
            self.verdict = verdict


@dataclass
class Report:
    claims: list
    sources: list
    answer: str = ""

    @property
    def checked(self):
        return [c for c in self.claims if c.verdict != SKIPPED]

    def count(self, verdict):
        return sum(c.verdict == verdict for c in self.claims)

    @property
    def groundedness(self):
        """Share of checkable claims that are fully supported (0..1)."""
        checked = self.checked
        return self.count(SUPPORTED) / len(checked) if checked else 1.0

    def to_dict(self):
        return {
            "groundedness": round(self.groundedness, 3),
            "counts": {v: self.count(v) for v in (SUPPORTED, WEAK, UNSUPPORTED, SKIPPED)},
            "sources": [s.name for s in self.sources],
            "claims": [asdict(c) for c in self.claims],
        }


class Index:
    """Sentence and two-sentence-window passages with an inverted index."""

    def __init__(self, sources):
        self.sources = sources
        self.passages, self.tokens, self.sentences = [], [], []
        df, units = defaultdict(int), 0
        for i, src in enumerate(sources):
            spans = list(text.sentence_spans(src.text))
            for j, (a, b) in enumerate(spans):
                units += 1
                for t in set(text.tokens(src.text[a:b])):
                    df[t] += 1
                self.sentences.append(len(self.passages))
                self._add(i, a, b)
                if j + 1 < len(spans):
                    self._add(i, a, spans[j + 1][1])
        self.idf = defaultdict(lambda: math.log((units + 1) / 0.5))
        for t, n in df.items():
            self.idf[t] = math.log((units + 1) / (n + 0.5))
        self.postings = defaultdict(set)
        for pid, toks in enumerate(self.tokens):
            for t in toks:
                self.postings[t].add(pid)
        self.squashed = [text.squash(s.text) for s in sources]

    def _add(self, i, a, b):
        chunk = self.sources[i].text[a:b]
        self.passages.append(Passage(i, a, b, chunk))
        self.tokens.append(set(text.tokens(chunk)))

    def contradiction(self, claim_tokens, claim_negated, cover=0.8, min_tokens=3):
        """A source sentence the claim restates (>= ``cover`` of its weight)
        but with the opposite polarity, e.g. "X does not remove Y" vs "X removes Y"."""
        ctoks = set(claim_tokens)
        for pid in self.sentences:
            toks = self.tokens[pid]
            if len(toks) < min_tokens:
                continue
            p = self.passages[pid]
            if text.negated(p.text) == claim_negated:
                continue
            total = sum(self.idf[t] for t in toks)
            if sum(self.idf[t] for t in toks & ctoks) / total >= cover:
                return p
        return None

    def best(self, claim_tokens, restrict=None):
        """Return (score, passage) of the best-covering passage."""
        weights = {t: self.idf[t] for t in set(claim_tokens)}
        total = sum(weights.values()) or 1.0
        bigrams = set(zip(claim_tokens, claim_tokens[1:]))
        candidates = set().union(*(self.postings.get(t, ()) for t in weights)) if weights else set()
        best = (0.0, None)
        for pid in candidates:
            p = self.passages[pid]
            if restrict is not None and p.source not in restrict:
                continue
            toks = self.tokens[pid]
            score = sum(w for t, w in weights.items() if t in toks) / total
            if bigrams:
                ptoks = text.tokens(p.text)
                pbig = set(zip(ptoks, ptoks[1:]))
                score = 0.75 * score + 0.25 * len(bigrams & pbig) / len(bigrams)
            # Prefer the shorter passage on ties: tighter evidence.
            if score > best[0] + 1e-9 or (abs(score - best[0]) < 1e-9 and best[1]
                                         and len(p.text) < len(best[1].text)):
                best = (score, p)
        return best


def check(answer, sources, supported=0.7, weak=0.4, min_tokens=3):
    """Check every sentence of ``answer`` against ``sources``.

    ``sources`` may be a list of strings or of ``Source`` objects. Citation
    markers such as ``[2]`` refer to sources by 1-based position.
    """
    sources = [s if isinstance(s, Source) else Source(f"source {i + 1}", s)
               for i, s in enumerate(sources)]
    sources = [Source(s.name, text.normalize(s.text)) for s in sources]
    answer = text.normalize(answer)
    index = Index(sources)
    claims = []
    for a, b in text.sentence_spans(answer):
        claim = Claim(answer[a:b], a, b, cited=text.citations(answer[a:b]))
        claims.append(claim)
        toks = text.tokens(claim.text)
        bare = text.strip_citations(claim.text).strip()
        if len(toks) < min_tokens or bare.endswith((":", "?")):
            continue
        _judge(claim, toks, index, supported, weak)
    return Report(claims, sources, answer)


def _judge(claim, toks, index, supported, weak):
    claim.score, claim.evidence = index.best(toks)
    claim.score = round(claim.score, 3)
    claim.verdict = (SUPPORTED if claim.score >= supported
                     else WEAK if claim.score >= weak else UNSUPPORTED)
    ev = claim.evidence.text if claim.evidence else ""
    claim.missing = text.missing_words(claim.text, set(text.tokens(ev)))

    # 1. Quotes must appear verbatim somewhere in the sources.
    for q in text.quotes(claim.text):
        if not any(text.squash(q) in s for s in index.squashed):
            claim.cap(UNSUPPORTED, f'quote not found in any source: "{q}"')

    # 2. Every number must be backed by the evidence (or at least a source).
    if claim.evidence:
        ev_nums = text.numbers(ev)
        all_nums = set().union(*(text.numbers(s.text) for s in index.sources))
        for n in sorted(text.numbers(claim.text) - ev_nums):
            if n in all_nums:
                claim.cap(WEAK, f"number {n} appears in sources but not in the matched passage")
            else:
                claim.cap(UNSUPPORTED, f"number {n} not found in any source")

    # 3. Restating a source sentence with flipped negation is a contradiction.
    hit = index.contradiction(toks, text.negated(text.strip_citations(claim.text)))
    if hit:
        claim.evidence = hit
        claim.missing = text.missing_words(claim.text, set(text.tokens(hit.text)))
        claim.cap(UNSUPPORTED, f'contradicts [{hit.source + 1}]: "{hit.text}"')

    # 4. Citations must point at real sources that actually hold the evidence.
    if claim.cited and claim.verdict != UNSUPPORTED:
        n = len(index.sources)
        bad = [c for c in claim.cited if not 1 <= c <= n]
        if bad:
            claim.cap(WEAK, f"cites non-existent source(s) {bad}")
        valid = {c - 1 for c in claim.cited if 1 <= c <= n}
        if valid and claim.evidence.source not in valid:
            cited_score, _ = index.best(toks, restrict=valid)
            if cited_score < weak:
                claim.cap(WEAK, f"miscited: evidence is in [{claim.evidence.source + 1}], "
                                f"not {sorted(c + 1 for c in valid)}")
