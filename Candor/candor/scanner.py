"""Run every rule over a page and condense the result into a score."""
from __future__ import annotations

from dataclasses import dataclass, field

from .page import Page
from .rules import RULES, SEVERITIES, Rule

# Points deducted per distinct finding; repeats of one rule are capped so a
# single noisy pattern can't sink the score on its own.
PENALTY = {"high": 15, "medium": 8, "low": 3}
MAX_PER_RULE = 2


@dataclass
class Finding:
    rule: Rule
    evidence: str
    where: str
    line: int

    def as_dict(self) -> dict:
        r = self.rule
        return {"rule": r.id, "name": r.name, "category": r.category,
                "severity": r.severity, "evidence": self.evidence,
                "where": self.where, "line": self.line,
                "why": r.why, "fix": r.fix, "refs": list(r.refs)}


@dataclass
class Report:
    source: str
    title: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        lost, per_rule = 0, {}
        for f in self.findings:
            per_rule[f.rule.id] = per_rule.get(f.rule.id, 0) + 1
            if per_rule[f.rule.id] <= MAX_PER_RULE:
                lost += PENALTY[f.rule.severity]
        return max(0, 100 - lost)

    @property
    def grade(self) -> str:
        s = self.score
        return "A" if s >= 90 else "B" if s >= 75 else "C" if s >= 60 else "D" if s >= 40 else "F"

    def count(self, severity: str) -> int:
        return sum(f.rule.severity == severity for f in self.findings)

    def worst(self) -> str | None:
        return next((s for s in SEVERITIES if self.count(s)), None)

    def as_dict(self) -> dict:
        return {"source": self.source, "title": self.title, "score": self.score,
                "grade": self.grade,
                "summary": {s: self.count(s) for s in SEVERITIES},
                "findings": [f.as_dict() for f in self.findings]}


def scan(html: str, source: str = "<string>", only: set[str] | None = None) -> Report:
    """Scan one HTML document. ``only`` restricts to a set of rule IDs."""
    page = Page(html)
    report = Report(source, page.title)
    for r in RULES:
        if only and r.id not in only:
            continue
        for el, evidence in r.check(page):
            report.findings.append(Finding(r, _clip(evidence), el.selector, el.line))
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    report.findings.sort(key=lambda f: (rank[f.rule.severity], f.line))
    return report


def _clip(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"
