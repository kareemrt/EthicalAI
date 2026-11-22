"""CSV loading: turns raw rows into (group, selected) pairs for each audit view."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .metrics import median

TRUTHY = {"1", "true", "t", "yes", "y", "selected", "hired", "advanced", "pass", "passed"}
MISSING = {"", "na", "n/a", "unknown", "none", "null", "declined", "prefer not to say"}


@dataclass
class View:
    """One slice of the data: a single attribute, or an intersection of several."""

    name: str
    records: list[tuple[str, bool]] = field(default_factory=list)
    unknown: int = 0


@dataclass
class Dataset:
    mode: str  # "selection" or "scoring"
    rows: int
    threshold: float | None  # median score in scoring mode
    views: list[View]


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip().lower() in MISSING


def load(path: str | Path, groups: list[str], selected: str | None = None, score: str | None = None) -> Dataset:
    if bool(selected) == bool(score):
        raise ValueError("pass exactly one of --selected or --score")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        wanted = groups + [selected or score]
        missing_cols = [c for c in wanted if c not in header]
        if missing_cols:
            raise ValueError(f"column(s) not found: {', '.join(missing_cols)} (have: {', '.join(header)})")
        rows = list(reader)

    if score:
        try:
            scores = [float(r[score]) for r in rows]
        except ValueError as exc:
            raise ValueError(f"non-numeric value in score column '{score}': {exc}") from None
        threshold = median(scores) if scores else 0.0
        outcomes = [s > threshold for s in scores]
    else:
        threshold = None
        outcomes = [r[selected].strip().lower() in TRUTHY for r in rows]

    view_cols = [[g] for g in groups]
    if len(groups) > 1:
        view_cols.append(groups)

    views = []
    for cols in view_cols:
        view = View(" × ".join(cols))
        for row, outcome in zip(rows, outcomes):
            values = [row[c] for c in cols]
            if any(_is_missing(v) for v in values):
                view.unknown += 1
            else:
                view.records.append((" · ".join(v.strip() for v in values), outcome))
        views.append(view)

    return Dataset("scoring" if score else "selection", len(rows), threshold, views)
