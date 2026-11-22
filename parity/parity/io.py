"""Reading decision logs and turning raw outcome columns into selected / not-selected."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

TRUE = {"1", "true", "yes", "y", "selected", "pass", "hired", "advance", "approved", "t"}
FALSE = {"0", "false", "no", "n", "rejected", "fail", "declined", "denied", "f"}
UNKNOWN = "Unknown"


def load_csv(path: str | Path) -> list[dict[str, str]]:
    """Load a CSV into a list of row dicts (header row required)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def require_columns(rows: list[dict[str, str]], columns: list[str]) -> None:
    if not rows:
        raise ValueError("the input contains no rows")
    missing = [c for c in columns if c not in rows[0]]
    if missing:
        have = ", ".join(rows[0].keys())
        raise ValueError(f"missing column(s): {', '.join(missing)} (available: {have})")


def to_binary(values: list[str], threshold: float | None = None) -> tuple[list[bool], str, float | None]:
    """Convert an outcome column to booleans.

    Returns ``(selected, mode, cutoff)`` where mode is:
      * ``"selection"`` — the column already holds yes/no style decisions;
      * ``"score"`` — numeric scores, binarised at ``threshold`` or, by default,
        at the sample median (the "scoring rate" used by NYC Local Law 144).
    """
    cleaned = [v.strip().lower() for v in values]
    if threshold is None and all(v in TRUE or v in FALSE for v in cleaned):
        return [v in TRUE for v in cleaned], "selection", None

    try:
        scores = [float(v) for v in cleaned]
    except ValueError as exc:
        raise ValueError(f"outcome column is neither yes/no nor numeric: {exc}") from None
    cutoff = statistics.median(scores) if threshold is None else threshold
    return [s > cutoff for s in scores], "score", cutoff


def group_value(row: dict[str, str], column: str) -> str:
    value = (row.get(column) or "").strip()
    return value or UNKNOWN
