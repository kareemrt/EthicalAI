"""Load decision logs from CSV into a uniform list of records."""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

UNKNOWN = "Unknown"
TRUE = {"1", "true", "t", "yes", "y", "selected", "hired", "approved", "accept", "accepted", "pass", "positive"}
FALSE = {"0", "false", "f", "no", "n", "rejected", "denied", "declined", "reject", "fail", "negative", ""}


@dataclass(frozen=True)
class Record:
    groups: dict[str, str]  # attribute -> group value, e.g. {"sex": "Female"}
    pred: int               # 1 = favourable decision (hired, approved, ...)
    label: int | None       # 1 = truly qualified / should be favourable (optional)


def to_binary(value: str, column: str) -> int:
    v = str(value).strip().lower()
    if v in TRUE:
        return 1
    if v in FALSE:
        return 0
    raise ValueError(f"Column '{column}': cannot read {value!r} as yes/no (use 1/0, true/false, yes/no)")


def load(
    path: str | Path,
    groups: list[str],
    outcome: str | None = None,
    score: str | None = None,
    threshold: float | None = None,
    label: str | None = None,
) -> tuple[list[Record], str]:
    """Read a CSV and return (records, human description of the outcome).

    Pass either `outcome` (a yes/no column) or `score` (numeric; favourable
    when >= threshold, defaulting to the median as NYC Local Law 144 does
    for its "scoring rate").
    """
    if bool(outcome) == bool(score):
        raise ValueError("Pass exactly one of --outcome or --score")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path} has no data rows")

    needed = [*groups, outcome or score] + ([label] if label else [])
    missing = [c for c in needed if c not in rows[0]]
    if missing:
        raise ValueError(f"Missing column(s): {', '.join(missing)}. Found: {', '.join(rows[0])}")

    if score:
        values = [float(r[score]) for r in rows]
        cut = statistics.median(values) if threshold is None else threshold
        preds = [int(v >= cut) for v in values]
        how = f"{score} ≥ {cut:g}" + (" (median)" if threshold is None else "")
    else:
        preds = [to_binary(r[outcome], outcome) for r in rows]
        how = f"{outcome} = yes"

    records = [
        Record(
            groups={g: (r[g].strip() or UNKNOWN) for g in groups},
            pred=p,
            label=to_binary(r[label], label) if label else None,
        )
        for r, p in zip(rows, preds)
    ]
    return records, how
