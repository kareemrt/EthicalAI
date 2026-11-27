"""Load decision records from CSV into a simple, uniform shape.

Every record becomes ``(attributes, outcome)`` where ``attributes`` maps each
protected-attribute column to its value (or ``None`` when unknown) and
``outcome`` is ``True`` when the person received the favourable result
(hired, shortlisted, approved...).
"""

from __future__ import annotations

import csv
from statistics import median
from typing import Iterable

Record = tuple[dict[str, str | None], bool]

MISSING = {"", "na", "n/a", "nan", "null", "none", "unknown", "?", "-"}
POSITIVE = {"1", "true", "yes", "y", "selected", "hired", "approved", "pass", "advanced"}


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return None if value.lower() in MISSING else value


def load_csv(
    path: str,
    attributes: Iterable[str],
    outcome: str | None = None,
    score: str | None = None,
) -> tuple[list[Record], dict]:
    """Read ``path`` and return ``(records, meta)``.

    Pass exactly one of ``outcome`` (a yes/no column) or ``score`` (a numeric
    column). For scores, the favourable outcome is "scored above the sample
    median" -- the *scoring rate* defined by NYC Local Law 144.
    """
    if (outcome is None) == (score is None):
        raise ValueError("Provide exactly one of --outcome or --score.")

    attributes = list(attributes)
    target = outcome or score
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        absent = [c for c in (*attributes, target) if c not in (reader.fieldnames or [])]
        if absent:
            raise ValueError(f"Column(s) not found in {path}: {', '.join(absent)}")
        rows = list(reader)

    meta = {"source": path, "rows": len(rows), "mode": "outcome" if outcome else "score", "dropped": 0}

    if score:
        values = []
        for row in rows:
            try:
                values.append(float(row[score]))
            except (TypeError, ValueError):
                values.append(None)
        valid = [v for v in values if v is not None]
        if not valid:
            raise ValueError(f"No numeric values in score column '{score}'.")
        cut = median(valid)
        meta["threshold"] = cut
        outcomes = [None if v is None else v > cut for v in values]
    else:
        outcomes = [None if _clean(r[outcome]) is None else r[outcome].strip().lower() in POSITIVE for r in rows]

    records: list[Record] = []
    for row, result in zip(rows, outcomes):
        if result is None:  # no usable outcome -> cannot contribute to a rate
            meta["dropped"] += 1
            continue
        records.append(({a: _clean(row[a]) for a in attributes}, result))
    return records, meta
