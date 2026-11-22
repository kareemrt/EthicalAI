"""Loading tabular data and inferring what kind of values each column holds."""

import csv
import re

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ZIP = re.compile(r"^\d{5}$")


def load_csv(path):
    """Read a CSV file into (header, rows). Each row is a dict of strings."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [{k: (v or "").strip() for k, v in row.items()} for row in reader]
        return list(reader.fieldnames or []), rows


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def infer_kind(column, values):
    """Classify a column as 'zip', 'date', 'numeric' or 'categorical'.

    The kind decides how the column is generalized: ZIP codes lose trailing
    digits, dates lose precision, numbers become ranges, categories merge.
    """
    present = [v for v in values if v]
    if not present:
        return "categorical"
    name = column.lower()
    if ("zip" in name or "postal" in name) and all(ZIP.match(v) for v in present):
        return "zip"
    if all(DATE.match(v) for v in present):
        return "date"
    if all(_is_number(v) for v in present):
        return "numeric"
    return "categorical"
