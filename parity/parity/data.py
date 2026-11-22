"""Load decision records from CSV into a compact in-memory form."""

import csv
from dataclasses import dataclass
from pathlib import Path

UNKNOWN = "Unknown"

POSITIVE = {
    "1", "true", "t", "yes", "y", "pass", "positive",
    "selected", "hired", "approved", "accepted", "advance", "advanced",
}


@dataclass(frozen=True, slots=True)
class Record:
    groups: tuple[str, ...]   # one value per audited attribute
    decision: bool            # did the system grant the favourable outcome?
    label: bool | None        # ground truth: was the person actually qualified?


def parse_bool(value: str, cutoff: float | None = None) -> bool:
    """Interpret a cell as a yes/no outcome.

    With ``cutoff`` the cell is treated as a numeric score and the outcome
    is ``score >= cutoff``. Otherwise common truthy spellings are accepted.
    """
    value = value.strip()
    if cutoff is not None:
        return float(value) >= cutoff
    return value.lower() in POSITIVE


def load(
    path: str | Path,
    groups: list[str],
    decision: str,
    label: str | None = None,
    cutoff: float | None = None,
) -> list[Record]:
    """Read ``path`` and return one Record per row with a usable decision.

    Blank protected-attribute cells become ``"Unknown"`` rather than being
    dropped: hiding people with undisclosed demographics hides bias too.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cols = set(reader.fieldnames or [])
        needed = [*groups, decision, *([label] if label else [])]
        missing = [c for c in needed if c not in cols]
        if missing:
            raise ValueError(
                f"column(s) not found: {', '.join(missing)}. "
                f"Available: {', '.join(sorted(cols))}"
            )

        records = []
        for row in reader:
            raw = (row[decision] or "").strip()
            if not raw:
                continue
            records.append(Record(
                groups=tuple((row[g] or "").strip() or UNKNOWN for g in groups),
                decision=parse_bool(raw, cutoff),
                label=parse_bool(row[label] or "") if label else None,
            ))
    if not records:
        raise ValueError(f"no rows with a value in '{decision}'")
    return records
