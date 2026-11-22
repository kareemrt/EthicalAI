"""Loading CSV data and turning rows into audit records."""
from __future__ import annotations

import csv
from statistics import median
from typing import Optional, Sequence

TRUTHY = {
    "1", "true", "t", "yes", "y", "pass", "positive",
    "selected", "hired", "approved", "accepted", "admitted", "offer",
}
MISSING = "(unknown)"


def load(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def require(rows: list[dict], columns: Sequence[str]) -> None:
    if not rows:
        raise ValueError("the CSV file has no data rows")
    missing = [c for c in columns if c not in rows[0]]
    if missing:
        raise ValueError(f"column(s) not found: {', '.join(missing)}. "
                         f"Available: {', '.join(rows[0])}")


def to_bool(value: str, positive: Optional[str] = None) -> bool:
    v = (value or "").strip().lower()
    return v == positive.lower() if positive else v in TRUTHY


def decisions_from_scores(rows: list[dict], column: str, cutoff: str = "median") -> list[bool]:
    """Binarize a continuous score.

    With ``cutoff="median"`` this is NYC Local Law 144's *scoring rate*:
    the share of people who score above the sample median.
    """
    scores = [float(r[column]) for r in rows]
    line = median(scores) if cutoff == "median" else float(cutoff)
    return [s > line for s in scores]


def group_key(row: dict, columns: Sequence[str]) -> str:
    return " × ".join((row.get(c) or "").strip() or MISSING for c in columns)


def to_records(
    rows: list[dict],
    groups: Sequence[str],
    decisions: list[bool],
    label: Optional[str] = None,
) -> list[tuple[str, bool, Optional[bool]]]:
    return [
        (group_key(r, groups), d, to_bool(r[label]) if label else None)
        for r, d in zip(rows, decisions)
    ]
