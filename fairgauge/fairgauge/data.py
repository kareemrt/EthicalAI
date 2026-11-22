"""Load decision records from a CSV file.

A record is one person who passed through an automated decision:
their demographic categories, whether they were selected (or scored
above the median), and optionally whether they were truly qualified.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from statistics import median

TRUTHY = {"1", "true", "t", "yes", "y", "selected", "hired", "pass", "passed", "approved", "accept", "accepted"}
UNKNOWN = "Unknown"


@dataclass(frozen=True)
class Record:
    groups: dict[str, str]        # attribute -> category, e.g. {"sex": "Female"}
    selected: bool                # favourable outcome from the tool
    actual: bool | None = None    # ground truth (qualified?), if known


def _truthy(value: str) -> bool:
    return value.strip().lower() in TRUTHY


def load(
    path: str,
    attributes: list[str],
    selected: str | None = None,
    score: str | None = None,
    outcome: str | None = None,
) -> list[Record]:
    """Read *path* and return one Record per row.

    Exactly one of *selected* (a yes/no column) or *score* (a numeric
    column) must be given. With *score*, a person counts as "selected"
    when their score is above the median of the whole sample - the
    "scoring rate" definition used by NYC Local Law 144 bias audits.
    """
    if (selected is None) == (score is None):
        raise ValueError("provide exactly one of --selected or --score")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path} has no data rows")

    needed = [*attributes, selected or score] + ([outcome] if outcome else [])
    missing = [c for c in needed if c not in rows[0]]
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}; found: {', '.join(rows[0])}")

    if score:
        scores = [_number(r[score]) for r in rows]
        valid = [s for s in scores if s is not None]
        if not valid:
            raise ValueError(f"column '{score}' has no numeric values")
        cut = median(valid)
        picks = [s is not None and s > cut for s in scores]
    else:
        picks = [_truthy(r[selected]) for r in rows]

    return [
        Record(
            groups={a: (r[a].strip() or UNKNOWN) for a in attributes},
            selected=pick,
            actual=_truthy(r[outcome]) if outcome else None,
        )
        for r, pick in zip(rows, picks)
    ]


def _number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
