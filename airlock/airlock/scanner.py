"""Run every detector over a piece of text and collect a Report."""
from __future__ import annotations

from .detectors import ALL
from .findings import Report, Source


def scan(text: str, source: str = "<text>") -> Report:
    src = Source(text, source)
    seen = set()
    findings = []
    for detector in ALL:
        for f in detector.detect(src):
            key = (f.rule, f.line, f.col)
            if key not in seen:
                seen.add(key)
                findings.append(f)
    findings.sort(key=lambda f: (-f.severity, f.line, f.col))
    return Report(source, findings)
