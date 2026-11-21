"""Reading decision logs and normalising messy real-world values."""

import csv

# Values that mean "we don't know this person's category".
# NYC LL144 requires these people to be counted and reported, not silently dropped.
MISSING = {"", "na", "n/a", "nan", "none", "null", "unknown", "?", "-",
           "declined", "prefer not to say", "not specified"}

POSITIVE = {"1", "true", "t", "yes", "y", "selected", "hired", "pass",
            "advance", "advanced", "approved", "accept", "accepted"}


def load_rows(path):
    """Read a CSV into a list of dicts with whitespace-trimmed keys and values."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()}
                for row in reader]


def is_missing(value):
    return value is None or value.strip().lower() in MISSING


def is_positive(value):
    """Interpret an outcome cell (1/0, yes/no, hired/rejected, ...) as a bool."""
    return value.strip().lower() in POSITIVE


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def require_columns(rows, columns):
    """Fail early with a friendly message instead of a KeyError deep inside."""
    if not rows:
        raise ValueError("the file has no data rows")
    absent = [c for c in columns if c not in rows[0]]
    if absent:
        have = ", ".join(rows[0].keys())
        raise ValueError(f"column(s) not found: {', '.join(absent)}  (available: {have})")
