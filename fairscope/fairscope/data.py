"""Loading decision records and turning them into (group, outcome, label) columns."""

from __future__ import annotations

import csv
from statistics import median

TRUE = {"1", "true", "t", "yes", "y", "selected", "hired", "approved", "advanced", "pass"}
FALSE = {"0", "false", "f", "no", "n", "rejected", "denied", "declined", "fail", ""}
UNKNOWN = "Unknown"


def load_rows(path: str) -> list[dict[str, str]]:
    """Read a CSV file into a list of dicts (header row required)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path}: no data rows found")
    return rows


def require(rows: list[dict[str, str]], *cols: str | None) -> None:
    """Fail early, with a helpful message, if a column is missing."""
    have = set(rows[0])
    missing = [c for c in cols if c and c not in have]
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}. Available: {', '.join(sorted(have))}")


def to_bool(value: str, column: str) -> bool:
    v = value.strip().lower()
    if v in TRUE:
        return True
    if v in FALSE:
        return False
    raise ValueError(f"column '{column}': cannot read {value!r} as yes/no")


def outcomes(rows, outcome: str | None = None, score: str | None = None, cutoff: float | None = None) -> list[bool]:
    """Binary 'selected' flags, either from a yes/no column or by thresholding a score.

    With a score and no cutoff, the overall median is used — the "scoring rate"
    definition used by NYC Local Law 144 for systems that only output scores.
    """
    if outcome:
        return [to_bool(r[outcome], outcome) for r in rows]
    if not score:
        raise ValueError("provide either an outcome column or a score column")
    values = []
    for r in rows:
        try:
            values.append(float(r[score]))
        except ValueError:
            raise ValueError(f"column '{score}': {r[score]!r} is not a number") from None
    line = median(values) if cutoff is None else cutoff
    return [v > line for v in values]


def groups(rows, attrs: list[str]) -> list[str]:
    """Group label per row; several attributes are joined into an intersectional label."""
    return [" × ".join(r[a].strip() or UNKNOWN for a in attrs) for r in rows]
