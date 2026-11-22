"""CSV loading and column preparation."""

from __future__ import annotations

import csv
from pathlib import Path

TRUE = {"1", "true", "yes", "y", "t", "selected", "hired", "pass", "advance"}


def load(path: str | Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [{k.strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def require(rows: list[dict], *cols: str) -> None:
    missing = [c for c in cols if c and c not in rows[0]]
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}; have: {', '.join(rows[0])}")


def as_bool(value: str) -> bool:
    return value.lower() in TRUE


def as_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"not a number: {value!r}") from None


def column(rows: list[dict], *cols: str, unknown: str = "Unknown") -> list[str]:
    """One column, or several joined into an intersectional label like 'Female × Black'."""
    return [" × ".join(r[c] or unknown for c in cols) for r in rows]
