"""Load a CSV of decisions and turn each row into a binary outcome."""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

TRUTHY = {"1", "true", "yes", "y", "selected", "hired", "pass", "passed", "approved", "accept", "accepted", "advance"}
MISSING = {"", "na", "n/a", "nan", "null", "none", "unknown", "?", "prefer not to say", "declined"}
UNKNOWN = "(unknown)"


@dataclass
class Record:
    groups: dict[str, str]      # attribute -> category
    selected: bool              # the decision being audited
    label: bool | None = None   # optional ground truth ("was actually qualified")


def _truthy(value: str, positive: str | None) -> bool:
    v = value.strip().lower()
    return v == positive.lower() if positive else v in TRUTHY


def _category(value: str | None) -> str:
    v = (value or "").strip()
    return UNKNOWN if v.lower() in MISSING else v


def load(
    path: str | Path,
    attrs: list[str],
    outcome: str | None = None,
    score: str | None = None,
    threshold: float | None = None,
    label: str | None = None,
    positive: str | None = None,
) -> list[Record]:
    """Read ``path`` and return one :class:`Record` per row.

    Exactly one of ``outcome`` (a yes/no decision column) or ``score`` (a
    numeric column) must be given. For scores, a row counts as "selected" when
    it scores above ``threshold`` — or above the median if no threshold is set,
    matching the *scoring rate* defined by NYC Local Law 144.
    """
    if (outcome is None) == (score is None):
        raise ValueError("pass exactly one of --outcome or --score")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path} has no data rows")

    needed = [*attrs, outcome or score] + ([label] if label else [])
    missing = [c for c in needed if c not in rows[0]]
    if missing:
        raise ValueError(f"column(s) not found: {', '.join(missing)} (have: {', '.join(rows[0])})")

    if score:
        values = [float(r[score]) for r in rows]
        cut = threshold if threshold is not None else statistics.median(values)
        decisions = [v > cut for v in values]
    else:
        decisions = [_truthy(r[outcome], positive) for r in rows]

    return [
        Record(
            groups={a: _category(r[a]) for a in attrs},
            selected=sel,
            label=_truthy(r[label], None) if label else None,
        )
        for r, sel in zip(rows, decisions)
    ]
