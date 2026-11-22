"""Core: find sensitive spans, swap them for placeholders, swap them back."""

from __future__ import annotations

import json
import os
import re
from bisect import bisect_left
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .detectors import DETECTORS, Detector, term_detector

PLACEHOLDER = re.compile(r"\[\s*([A-Z][A-Z_]*?)_(\d+)\s*\]", re.I)


@dataclass(frozen=True)
class Finding:
    label: str
    kind: str
    start: int
    end: int
    value: str

    def masked(self) -> str:
        """Safe preview for logs: keep a hint of shape, never the content."""
        v = self.value
        return v[:2] + "…" + v[-2:] if len(v) > 8 else "•" * len(v)


def find(text: str, detectors: Iterable[Detector]) -> list[Finding]:
    """All non-overlapping findings, highest priority (then longest) first."""
    candidates = []
    for d in detectors:
        for m in d.pattern.finditer(text):
            start, end = m.span(d.group)
            value = m.group(d.group)
            if start < 0 or not value.strip():
                continue
            if d.validate and not d.validate(value):
                continue
            candidates.append((d.priority, end - start, start, end, d))

    # Greedy by priority; `starts`/`ends` stay sorted so each overlap check is O(log n).
    starts: list[int] = []
    ends: list[int] = []
    taken: list[Finding] = []
    for _, _, start, end, d in sorted(candidates, key=lambda c: (-c[0], -c[1], c[2])):
        i = bisect_left(starts, start)
        if (i < len(starts) and starts[i] < end) or (i > 0 and ends[i - 1] > start):
            continue
        starts.insert(i, start)
        ends.insert(i, end)
        taken.insert(i, Finding(d.label, d.kind, start, end, text[start:end]))
    return taken


@dataclass
class Vault:
    """Two-way map between originals and placeholders.

    Reusing one vault across a conversation keeps placeholders stable:
    the same email is [EMAIL_1] in every prompt and every reply.
    """
    forward: dict[str, str] = field(default_factory=dict)   # key -> placeholder
    reverse: dict[str, str] = field(default_factory=dict)   # placeholder -> original
    counters: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def _key(label: str, value: str) -> str:
        # Emails and user terms are case-insensitive; secrets and numbers are exact.
        case_insensitive = label == "EMAIL" or label not in _BUILTIN
        return f"{label}\x00{value.casefold() if case_insensitive else value}"

    def placeholder(self, label: str, value: str) -> str:
        key = self._key(label, value)
        if key not in self.forward:
            self.counters[label] = self.counters.get(label, 0) + 1
            token = f"[{label}_{self.counters[label]}]"
            self.forward[key] = token
            self.reverse[token] = value
        return self.forward[key]

    def restore(self, text: str) -> str:
        def swap(m: re.Match) -> str:
            token = f"[{m.group(1).upper()}_{m.group(2)}]"
            return self.reverse.get(token, m.group(0))
        return PLACEHOLDER.sub(swap, text)

    # Persistence — the vault holds the real data, so it is written owner-only.
    def save(self, path: str | Path) -> None:
        path = Path(path)
        data = json.dumps({"reverse": self.reverse, "counters": self.counters,
                           "forward": self.forward}, indent=2, ensure_ascii=False)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)

    @classmethod
    def load(cls, path: str | Path) -> "Vault":
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data["forward"], data["reverse"], data["counters"])


_BUILTIN = {d.label for d in DETECTORS}


class Veil:
    """High-level API.

    >>> v = Veil(terms=["Dana Whitfield"])
    >>> safe = v.scrub("Dana Whitfield <dana@acme.io> wants a refund")
    >>> safe
    '[TERM_1] <[EMAIL_1]> wants a refund'
    >>> v.restore("Reply sent to [EMAIL_1], cc [TERM_1].")
    'Reply sent to dana@acme.io, cc Dana Whitfield.'
    """

    def __init__(self, terms: Iterable[str] = (), only: Optional[Iterable[str]] = None,
                 skip: Iterable[str] = (), vault: Optional[Vault] = None):
        only_set = {s.upper() for s in only} if only else None
        skip_set = {s.upper() for s in skip}
        self.detectors = [d for d in DETECTORS
                          if (only_set is None or d.label in only_set) and d.label not in skip_set]
        self.detectors += [term_detector(*_parse_term(t)) for t in terms if t.strip()]
        self.vault = vault or Vault()

    def scan(self, text: str) -> list[Finding]:
        return find(text, self.detectors)

    def scrub(self, text: str) -> str:
        out, cursor = [], 0
        for f in self.scan(text):
            out += [text[cursor:f.start], self.vault.placeholder(f.label, f.value)]
            cursor = f.end
        return "".join(out) + text[cursor:]

    def restore(self, text: str) -> str:
        return self.vault.restore(text)


def _parse_term(raw: str) -> tuple[str, str]:
    """'Dana Whitfield' -> TERM;  'PERSON: Dana Whitfield' -> PERSON."""
    m = re.match(r"^([A-Z][A-Z_]*)\s*:\s*(.+)$", raw.strip())
    return (m.group(2).strip(), m.group(1)) if m else (raw.strip(), "TERM")
