"""Run every rule over a page and turn the findings into a score."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import Request, urlopen

from .dom import Document
from .rules import RULES, SEVERITY_WEIGHT, Finding

SEVERITIES = ("high", "medium", "low")
GRADES = ((95, "A"), (80, "B"), (65, "C"), (50, "D"), (0, "F"))


@dataclass
class Report:
    source: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        return max(0, 100 - sum(SEVERITY_WEIGHT[f.severity] for f in self.findings))

    @property
    def grade(self) -> str:
        return next(g for cutoff, g in GRADES if self.score >= cutoff)

    def counts(self) -> dict[str, int]:
        return {s: sum(f.severity == s for f in self.findings) for s in SEVERITIES}

    def to_dict(self):
        return {"source": self.source, "score": self.score, "grade": self.grade,
                "counts": self.counts(), "findings": [f.to_dict() for f in self.findings]}


def scan_html(html: str, source: str = "<string>", only: set[str] | None = None) -> Report:
    doc = Document(html, source)
    found, seen = [], set()
    for r in RULES:
        if only and r.id not in only:
            continue
        for f in r.check(doc):
            key = (f.rule, f.line, f.evidence)
            if key not in seen:
                seen.add(key)
                found.append(f)
    found.sort(key=lambda f: (SEVERITIES.index(f.severity), f.line))
    return Report(source, found)


def load(target: str, timeout: float = 15) -> str:
    """Read a local file, or fetch a URL (static HTML only — no JavaScript)."""
    if target.startswith(("http://", "https://")):
        req = Request(target, headers={"User-Agent": "candor/0.1 (dark-pattern scanner)"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace")
    return Path(target).read_text(encoding="utf-8", errors="replace")


def expand(targets: list[str]) -> list[str]:
    """Turn directories into the .html/.htm files they contain."""
    out = []
    for t in targets:
        p = Path(t)
        if not t.startswith(("http://", "https://")) and p.is_dir():
            out += sorted(str(f) for f in p.rglob("*") if f.suffix.lower() in (".html", ".htm"))
        else:
            out.append(t)
    return out
