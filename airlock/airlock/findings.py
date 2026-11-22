"""Core data types: where text came from, what was found, and how bad it is."""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def __str__(self) -> str:
        return self.name.lower()


# Probability-style weights: each finding independently "raises the alarm".
_WEIGHT = {Severity.LOW: 0.10, Severity.MEDIUM: 0.30, Severity.HIGH: 0.60}


@dataclass(frozen=True)
class Finding:
    rule: str           # dotted id, e.g. "unicode.tag-smuggling"
    severity: Severity
    message: str        # one human sentence: what and why it matters
    line: int           # 1-based
    col: int            # 1-based
    excerpt: str = ""   # short, printable evidence

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": str(self.severity),
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "excerpt": self.excerpt,
        }


class Source:
    """Text plus a fast index -> (line, col) lookup."""

    def __init__(self, text: str, name: str = "<text>"):
        self.text = text
        self.name = name
        self._starts = [0] + [m.end() for m in re.finditer("\n", text)]

    def pos(self, index: int) -> tuple[int, int]:
        line = bisect_right(self._starts, index)
        return line, index - self._starts[line - 1] + 1

    def finding(self, rule: str, severity: Severity, message: str,
                start: int, end: int | None = None, excerpt: str | None = None) -> Finding:
        line, col = self.pos(start)
        if excerpt is None:
            excerpt = self.text[start:end if end is not None else start + 60]
        return Finding(rule, severity, message, line, col, shorten(excerpt))


@dataclass
class Report:
    source: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        """0-100. Combines findings as independent signals: 1 - prod(1 - w)."""
        calm = 1.0
        for f in self.findings:
            calm *= 1 - _WEIGHT[f.severity]
        return round(100 * (1 - calm))

    @property
    def worst(self) -> Severity | None:
        return max((f.severity for f in self.findings), default=None)

    @property
    def verdict(self) -> str:
        if not self.findings:
            return "clean"
        if self.worst is Severity.HIGH or self.score >= 60:
            return "dangerous"
        return "suspicious"

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "verdict": self.verdict,
            "score": self.score,
            "findings": [f.to_dict() for f in self.findings],
        }


def shorten(text: str, width: int = 80) -> str:
    """Collapse whitespace and truncate so evidence fits on one line."""
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"
