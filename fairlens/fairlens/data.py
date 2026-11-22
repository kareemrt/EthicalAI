"""Load decision logs from CSV and turn them into a clean, typed dataset."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import median

UNKNOWN = "Unknown"
TRUTHY = {"1", "true", "t", "yes", "y", "selected", "hired", "pass", "passed",
          "advance", "advanced", "approved", "accept", "accepted"}
FALSY = {"0", "false", "f", "no", "n", "rejected", "reject", "fail", "failed",
         "declined", "denied"}


@dataclass(frozen=True)
class Dataset:
    """Rows of a decision log plus the decision (and optional ground truth) per row."""

    rows: list[dict[str, str]]
    selected: list[bool]
    actual: list[bool] | None = None
    mode: str = "selection"          # "selection" (yes/no) or "scoring" (above median)
    threshold: float | None = None   # median score when mode == "scoring"

    def __len__(self) -> int:
        return len(self.rows)

    def groups(self, *attrs: str) -> list[str]:
        """Group label for each row; joins several attributes into an intersection."""
        out = []
        for row in self.rows:
            values = [(row.get(a) or "").strip() for a in attrs]
            out.append(UNKNOWN if not all(values) else " · ".join(values))
        return out


def to_bool(value: str, column: str) -> bool:
    v = (value or "").strip().lower()
    if v in TRUTHY:
        return True
    if v in FALSY:
        return False
    raise ValueError(f"Column '{column}': can't read {value!r} as yes/no")


def load(path: str | Path, *, outcome: str | None = None, score: str | None = None,
         label: str | None = None) -> Dataset:
    """Read a CSV decision log.

    Pass exactly one of ``outcome`` (a yes/no decision column) or ``score``
    (a numeric column; per NYC Local Law 144, a "selection" is a score above
    the sample median). ``label`` is an optional ground-truth column
    (e.g. "was actually qualified") that unlocks error-rate metrics.
    """
    if (outcome is None) == (score is None):
        raise ValueError("Provide exactly one of --outcome or --score")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path} has no data rows")

    for col in filter(None, (outcome, score, label)):
        if col not in rows[0]:
            raise ValueError(f"Column '{col}' not found. Available: {', '.join(rows[0])}")

    threshold = None
    if outcome:
        selected = [to_bool(r[outcome], outcome) for r in rows]
    else:
        scores = [float(r[score]) for r in rows]
        threshold = median(scores)
        selected = [s > threshold for s in scores]

    actual = [to_bool(r[label], label) for r in rows] if label else None
    return Dataset(rows, selected, actual, "selection" if outcome else "scoring", threshold)
