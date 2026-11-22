"""Run every check, then roll the results into one 0-100 score."""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import checks
from .text import sentences


@dataclass
class Report:
    source: str
    text: str
    readability: checks.Readability
    findings: list[checks.Finding]
    essentials: list[checks.Essential]
    penalties: dict[str, float]
    target_grade: float

    @property
    def score(self) -> int:
        return max(0, round(100 - sum(self.penalties.values())))

    @property
    def grade(self) -> str:
        s = self.score
        return "A" if s >= 90 else "B" if s >= 80 else "C" if s >= 70 else "D" if s >= 60 else "F"

    def of(self, kind: str) -> list[checks.Finding]:
        return [f for f in self.findings if f.kind == kind]

    def to_dict(self) -> dict:
        r = self.readability
        return {
            "source": self.source,
            "score": self.score,
            "grade": self.grade,
            "penalties": {k: round(v, 1) for k, v in self.penalties.items()},
            "readability": {
                "grade_level": r.grade, "target_grade": self.target_grade,
                "reading_ease": r.ease, "words": r.words, "sentences": r.sentences,
                "avg_sentence_words": r.avg_sentence, "you_per_100_words": r.you_per_100,
            },
            "essentials": [vars(e) for e in self.essentials],
            "findings": [vars(f) for f in self.findings],
        }


def analyze(text: str, source: str = "<text>", target_grade: float = 8.0) -> Report:
    sents = sentences(text)
    rd = checks.readability(sents)
    findings = sorted(
        checks.find_jargon(text) + checks.find_passive(text) + checks.find_long(sents),
        key=lambda f: (f.start, -f.end),
    )
    ess = checks.essentials(text, rd)

    per100 = 100 / max(rd.words, 1)
    body = max(rd.sentences, 1)
    jargon, passive = len([f for f in findings if f.kind == "jargon"]), len([f for f in findings if f.kind == "passive"])
    long_ = len([f for f in findings if f.kind == "long"])
    # Each penalty is capped so no single problem can zero the score alone.
    penalties = {
        "reading level": min(35.0, max(0.0, rd.grade - target_grade) * 5),
        "jargon": min(20.0, jargon * per100 * 4),
        "passive voice": min(10.0, passive / body * 30),
        "long sentences": min(15.0, long_ / body * 50),
        "missing essentials": 4.0 * sum(not e.ok for e in ess),
    }
    return Report(source, text, rd, findings, ess, penalties, target_grade)


def fix(text: str) -> str:
    """Mechanically swap jargon for plain words. A first draft, not a final one."""
    table, pattern = checks.jargon_table()

    def swap(m: re.Match) -> str:
        plain = table[m.group(0).lower()]
        if plain == "(delete)":
            return ""
        if "(" in plain or checks.in_name(text, m):
            return m.group(0)  # advice-only, or part of a proper name
        return plain[0].upper() + plain[1:] if m.group(0)[0].isupper() else plain

    out = pattern.sub(swap, text)
    out = re.sub(r"(^|[.!?]\s+) *([a-z])", lambda m: m.group(1) + m.group(2).upper(), out, flags=re.M)
    return re.sub(r"[ \t]{2,}", " ", out).replace(" ,", ",")
