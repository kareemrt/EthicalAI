"""Core engine: sources in, scored findings out."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .markup import extract_html, extract_text
from .patterns import BY_ID, SEVERITIES, TEXT_PATTERNS, Pattern

MARKUP_EXT = {".html", ".htm", ".xhtml", ".vue", ".svelte", ".jsx", ".tsx", ".astro", ".hbs", ".erb", ".jinja", ".j2"}
TEXT_EXT = {".txt", ".md", ".markdown"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".next"}
IGNORE_MARK = "candor-ignore"
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " "})


@dataclass(frozen=True)
class Finding:
    pattern: Pattern
    file: str
    line: int
    excerpt: str

    def to_dict(self) -> dict:
        p = self.pattern
        return {"id": p.id, "name": p.name, "category": p.category, "severity": p.severity,
                "file": self.file, "line": self.line, "excerpt": self.excerpt,
                "why": p.why, "fix": p.fix, "refs": list(p.refs)}


@dataclass
class FileResult:
    file: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        return max(0, 100 - sum(f.pattern.weight for f in self.findings))


@dataclass
class Report:
    files: list[FileResult]

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.files for f in r.findings]

    @property
    def score(self) -> int:
        """A product is only as honest as its least honest page."""
        return min((r.score for r in self.files), default=100)

    @property
    def grade(self) -> str:
        s = self.score
        return "A" if s >= 90 else "B" if s >= 75 else "C" if s >= 60 else "D" if s >= 40 else "F"

    def counts(self) -> dict[str, int]:
        c = dict.fromkeys(SEVERITIES, 0)
        for f in self.findings:
            c[f.pattern.severity] += 1
        return c

    def to_dict(self) -> dict:
        return {"score": self.score, "grade": self.grade, "counts": self.counts(),
                "files": [{"file": r.file, "score": r.score} for r in self.files],
                "findings": [f.to_dict() for f in self.findings]}


def _excerpt(text: str, start: int, end: int, pad: int = 40) -> str:
    a, b = max(0, start - pad), min(len(text), end + pad)
    return ("…" if a else "") + text[a:b].strip() + ("…" if b < len(text) else "")


def scan_text(source: str, name: str = "<input>", kind: str | None = None) -> FileResult:
    """Scan one document. `kind` is 'html' or 'text'; guessed from content if omitted."""
    source = source.translate(QUOTES)
    if kind is None:
        kind = "html" if "<" in source and ">" in source else "text"
    if kind == "html":
        blocks, signals = extract_html(source)
    else:
        blocks, signals = extract_text(source), []

    ignored = {n + d for n, l in enumerate(source.splitlines(), 1) if IGNORE_MARK in l for d in (0, 1)}
    found: dict[tuple[str, int, str], Finding] = {}

    def add(pattern: Pattern, line: int, excerpt: str) -> None:
        if line not in ignored:
            found.setdefault((pattern.id, line, excerpt), Finding(pattern, name, line, excerpt))

    for line, text in blocks:
        for pattern in TEXT_PATTERNS:
            for rx in pattern.regexes:
                m = rx.search(text)
                if m:
                    add(pattern, line, _excerpt(text, m.start(), m.end()))
                    break  # one hit per pattern per block is enough
    for pid, line, excerpt in signals:
        add(BY_ID[pid], line, excerpt[:160])

    rank = {s: i for i, s in enumerate(SEVERITIES)}
    ordered = sorted(found.values(), key=lambda f: (f.line, rank[f.pattern.severity]))
    return FileResult(name, ordered)


def iter_files(paths: Iterable[str]) -> Iterable[Path]:
    exts = MARKUP_EXT | TEXT_EXT
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                for f in sorted(files):
                    if Path(f).suffix.lower() in exts:
                        yield Path(root, f)


def scan_paths(paths: Iterable[str], min_severity: str = "low") -> Report:
    keep = set(SEVERITIES[: SEVERITIES.index(min_severity) + 1])
    results = []
    for path in iter_files(paths):
        kind = "text" if path.suffix.lower() in TEXT_EXT else "html"
        res = scan_text(path.read_text(encoding="utf-8", errors="replace"), str(path), kind)
        res.findings = [f for f in res.findings if f.pattern.severity in keep]
        results.append(res)
    return Report(results)
