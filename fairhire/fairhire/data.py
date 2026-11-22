"""Load decision records from CSV and turn them into binary outcomes."""

from __future__ import annotations

import csv
from statistics import median
from typing import Iterable

TRUE = {"1", "true", "t", "yes", "y", "selected", "hired", "pass", "passed", "advance", "advanced"}
FALSE = {"0", "false", "f", "no", "n", "rejected", "declined", "fail", "failed", ""}
UNKNOWN = "Unknown"


def load_csv(path: str) -> list[dict[str, str]]:
    """Read a CSV into a list of row dicts (header row required)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def parse_outcome(value: str) -> bool:
    """Interpret a yes/no style cell. Raises ValueError on anything ambiguous."""
    v = value.strip().lower()
    if v in TRUE:
        return True
    if v in FALSE:
        return False
    raise ValueError(f"cannot interpret outcome value {value!r} as selected / not selected")


def outcomes(rows: list[dict[str, str]], outcome: str | None = None, score: str | None = None) -> list[bool]:
    """Return one boolean per row.

    * ``outcome`` — a selection column (hired / advanced / rejected ...).
    * ``score``   — a numeric column; per LL144 a row counts as "selected" when
      its score is strictly above the median score of the whole sample.
    """
    if (outcome is None) == (score is None):
        raise ValueError("pass exactly one of outcome= or score=")
    _require(rows, [outcome or score])
    if outcome:
        return [parse_outcome(r[outcome]) for r in rows]
    values = [float(r[score]) for r in rows]
    cut = median(values)
    return [v > cut for v in values]


def category(row: dict[str, str], attrs: Iterable[str]) -> str:
    """Category label for a row, e.g. ``"Female"`` or ``"Female × Asian"``."""
    parts = [row.get(a, "") or UNKNOWN for a in attrs]
    return UNKNOWN if UNKNOWN in parts else " × ".join(parts)


def _require(rows: list[dict[str, str]], cols: Iterable[str]) -> None:
    if not rows:
        raise ValueError("dataset is empty")
    missing = [c for c in cols if c not in rows[0]]
    if missing:
        raise ValueError(f"column(s) not found: {', '.join(missing)}; available: {', '.join(rows[0])}")
