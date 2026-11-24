"""Reading decision logs and turning them into (group, outcome) pairs."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import median

TRUTHY = {"1", "true", "yes", "y", "selected", "hired", "pass", "approved", "advance"}
FALSY = {"0", "false", "no", "n", "rejected", "declined", "fail", "denied", ""}
UNKNOWN = {"", "unknown", "na", "n/a", "none", "null", "prefer not to say", "declined to state"}


class DataError(ValueError):
    """Raised for malformed input, with a message meant for humans."""


def load_rows(path: str | Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise DataError(f"{path}: no data rows found")
    return rows


def require_columns(rows: list[dict[str, str]], columns: list[str]) -> None:
    missing = [c for c in columns if c not in rows[0]]
    if missing:
        have = ", ".join(rows[0])
        raise DataError(f"missing column(s): {', '.join(missing)} (available: {have})")


def binary_outcomes(rows: list[dict[str, str]], column: str) -> list[bool]:
    """Parse a yes/no style column. Fails loudly on anything ambiguous."""
    out = []
    for i, row in enumerate(rows, start=2):  # line 1 is the header
        v = row[column].strip().lower()
        if v in TRUTHY:
            out.append(True)
        elif v in FALSY:
            out.append(False)
        else:
            raise DataError(f"line {i}: can't read {column}={row[column]!r} as yes/no "
                            "(use --score for numeric scores)")
    return out


def score_outcomes(rows: list[dict[str, str]], column: str) -> tuple[list[bool], float]:
    """LL144 'scoring rate': a person counts as selected if their score is
    above the median of the whole sample."""
    try:
        scores = [float(r[column]) for r in rows]
    except ValueError as e:
        raise DataError(f"{column}: non-numeric score ({e})") from None
    cut = median(scores)
    return [s > cut for s in scores], cut


def group_value(row: dict[str, str], column: str) -> str | None:
    v = row[column].strip()
    return None if v.lower() in UNKNOWN else v


def intersect_value(row: dict[str, str], columns: list[str]) -> str | None:
    parts = [group_value(row, c) for c in columns]
    return None if None in parts else " · ".join(parts)  # type: ignore[arg-type]
