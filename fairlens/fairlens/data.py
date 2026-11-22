"""CSV loading and grouping. Streams rows, so memory scales with #groups, not #rows."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .metrics import GroupStats

TRUTHY = {"1", "true", "t", "yes", "y", "selected", "hired", "approved", "pass", "accept", "accepted"}
MISSING = {"", "na", "n/a", "nan", "null", "none", "unknown", "?"}


def is_positive(value: str, positive: str | None = None) -> bool:
    v = value.strip().lower()
    return v == positive.lower() if positive is not None else v in TRUTHY


def read_rows(path: str | Path) -> Iterable[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: file is empty")
        yield from reader


def tally(rows: Iterable[dict[str, str]], attributes: list[str], outcome: str,
          label: str | None = None, positive: str | None = None) -> tuple[dict[str, list[GroupStats]], int]:
    """Count outcomes per group for each attribute key.

    `attributes` may contain intersectional keys like "sex*race"; their group
    name is the joined values ("Female × Black"). Rows with a missing value for
    an attribute are skipped for that attribute only. Returns (stats, rows_seen).
    """
    stats: dict[str, dict[str, GroupStats]] = {a: {} for a in attributes}
    seen = 0
    for row in rows:
        if seen == 0:
            needed = {outcome, *(c for a in attributes for c in a.split("*"))} | ({label} if label else set())
            missing = sorted(c for c in needed if c not in row)
            if missing:
                raise KeyError(f"column(s) not found: {', '.join(missing)}. Available: {', '.join(row)}")
        seen += 1
        selected = is_positive(row[outcome], positive)
        qualified = is_positive(row[label]) if label else None
        for attr in attributes:
            values = [row[c].strip() for c in attr.split("*")]
            if any(v.lower() in MISSING for v in values):
                continue
            name = " × ".join(values)
            g = stats[attr].setdefault(name, GroupStats(name))
            g.n += 1
            g.selected += selected
            if qualified is not None:
                if qualified:
                    g.tp += selected
                    g.fn += not selected
                else:
                    g.fp += selected
                    g.tn += not selected
    return {a: list(groups.values()) for a, groups in stats.items()}, seen
