"""Load applicant outcomes from a CSV file into a small, normalized dataset.

Each row becomes ``(categories, positive)``: a tuple holding one category per
demographic column (``None`` when unknown) and whether the applicant received
the favourable outcome.

Two modes mirror NYC Local Law 144:
  * selection - a yes/no column, e.g. "advanced to interview".
  * scoring   - a numeric column; positive means "scored above the median".
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Optional

POSITIVE = {"1", "true", "yes", "y", "selected", "hired", "pass", "passed",
            "advance", "advanced", "offer", "accepted"}
UNKNOWN = {"", "unknown", "na", "n/a", "none", "null", "declined",
           "prefer not to say", "not disclosed", "undisclosed"}

Row = tuple[tuple[Optional[str], ...], bool]


@dataclass(frozen=True)
class Dataset:
    attributes: tuple[str, ...]
    rows: list[Row]
    mode: str                        # "selection" | "scoring"
    outcome: str                     # source column name
    cutoff: Optional[float] = None   # median score (scoring mode only)

    @property
    def positive_rate(self) -> float:
        return sum(hit for _, hit in self.rows) / len(self.rows)


def load(path: str, groups: Iterable[str], outcome: Optional[str] = None,
         score: Optional[str] = None, positive: Optional[Iterable[str]] = None) -> Dataset:
    """Read ``path`` and return a :class:`Dataset`.

    Exactly one of ``outcome`` (selection mode) or ``score`` (scoring mode)
    must be given. ``positive`` overrides the values counted as a "yes".
    """
    groups = tuple(groups)
    if (outcome is None) == (score is None):
        raise ValueError("specify exactly one of --outcome or --score")
    if not groups:
        raise ValueError("specify at least one demographic column with --groups")

    target = outcome or score
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in (*groups, target) if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"column(s) not found in {path}: {', '.join(missing)}")
        raw = list(reader)
    if not raw:
        raise ValueError(f"{path} has no data rows")

    labels = [tuple(_category(r[g]) for g in groups) for r in raw]
    if score:
        values = [_number(r[score], line) for line, r in enumerate(raw, start=2)]
        cutoff = median(values)
        hits = [v > cutoff for v in values]
    else:
        accepted = {p.strip().lower() for p in positive} if positive else POSITIVE
        hits = [(r[outcome] or "").strip().lower() in accepted for r in raw]
        cutoff = None

    return Dataset(groups, list(zip(labels, hits)),
                   "scoring" if score else "selection", target, cutoff)


def _category(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return None if value.lower() in UNKNOWN else value


def _number(value: Optional[str], line: int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"line {line}: score {value!r} is not a number") from None
