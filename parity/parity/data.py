"""Loading and normalising decision records."""

import csv
from pathlib import Path

TRUTHY = {"1", "true", "yes", "y", "selected", "hired", "approved", "pass"}


def load_csv(path: str | Path) -> list[dict[str, str]]:
    """Read a CSV into a list of row dicts, stripping whitespace from every cell."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def is_selected(value: str) -> bool:
    """Interpret a binary outcome cell ('1', 'yes', 'hired', ...) as True/False."""
    return value.strip().lower() in TRUTHY


def to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def outcomes(rows: list[dict], outcome: str | None = None, score: str | None = None) -> list[bool]:
    """Return one boolean per row.

    * ``outcome`` — a binary column (selection rate).
    * ``score``   — a numeric column; a row counts as "selected" when it scores
      above the overall median (the NYC Local Law 144 *scoring rate*).
    """
    if outcome:
        return [is_selected(r[outcome]) for r in rows]
    if score:
        values = [to_float(r[score]) for r in rows]
        known = sorted(v for v in values if v is not None)
        if not known:
            raise ValueError(f"column '{score}' has no numeric values")
        mid = len(known) // 2
        median = known[mid] if len(known) % 2 else (known[mid - 1] + known[mid]) / 2
        return [v is not None and v > median for v in values]
    raise ValueError("pass either an outcome column or a score column")
