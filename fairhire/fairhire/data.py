"""Load and validate applicant-level decision data from CSV."""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from typing import Optional, Sequence

TRUE = {"1", "true", "t", "yes", "y", "selected", "advanced", "hired", "pass", "passed"}
FALSE = {"0", "false", "f", "no", "n", "rejected", "declined", "fail", "failed"}


@dataclass(frozen=True)
class Record:
    """One applicant: their demographic categories and what the tool decided."""

    groups: dict[str, str]
    selected: bool
    score: Optional[float] = None
    qualified: Optional[bool] = None  # ground truth, enables error-rate metrics


class DataError(ValueError):
    """Raised when the input file cannot be audited as given."""


def parse_bool(value: str, column: str, row: int) -> bool:
    v = value.strip().lower()
    if v in TRUE:
        return True
    if v in FALSE:
        return False
    raise DataError(f"row {row}: can't read {value!r} in column '{column}' as yes/no")


def load_csv(
    path: str,
    groups: Sequence[str],
    outcome: Optional[str] = None,
    score: Optional[str] = None,
    label: Optional[str] = None,
) -> list[Record]:
    """Read a CSV into Records.

    Provide `outcome` for binary decisions (selection rates), or only `score`
    for continuous scores — then an applicant counts as "selected" when they
    score above the sample median (the NYC Local Law 144 "scoring rate").
    """
    if not outcome and not score:
        raise DataError("give an --outcome column, a --score column, or both")

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in [*groups, outcome, score, label] if c and c not in (reader.fieldnames or [])]
        if missing:
            raise DataError(f"columns not found: {', '.join(missing)} (have: {', '.join(reader.fieldnames or [])})")
        rows = list(reader)

    if not rows:
        raise DataError("file has no data rows")

    scores: list[Optional[float]] = [None] * len(rows)
    if score:
        try:
            scores = [float(r[score]) for r in rows]
        except ValueError as e:
            raise DataError(f"non-numeric value in score column '{score}': {e}") from None
    cutoff = statistics.median(scores) if score and not outcome else None

    records = []
    for i, (r, s) in enumerate(zip(rows, scores), start=2):  # row 1 is the header
        selected = parse_bool(r[outcome], outcome, i) if outcome else s > cutoff
        records.append(
            Record(
                groups={g: (r[g].strip() or "Unknown") for g in groups},
                selected=selected,
                score=s,
                qualified=parse_bool(r[label], label, i) if label else None,
            )
        )
    return records
