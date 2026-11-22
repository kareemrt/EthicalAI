"""Find columns that identify people directly, or indirectly in combination.

Direct identifiers (names, emails, record numbers) point at one person on
their own and should never be shared. Quasi-identifiers (ZIP, birth date,
sex...) are harmless alone but unique in combination: Latanya Sweeney showed
that ZIP + birth date + sex alone single out ~87% of Americans.
"""

import re

from .data import infer_kind

DIRECT_NAMES = re.compile(
    r"(^|_)(name|first_?name|last_?name|full_?name|email|e_?mail|phone|mobile|"
    r"ssn|social_security|passport|license|address|street|ip|ip_address|mrn|"
    r"account|iban|card)($|_)"
)
QUASI_NAMES = re.compile(
    r"(^|_)(age|dob|birth|birth_?date|birthday|zip|zipcode|postal|postcode|"
    r"gender|sex|race|ethnicity|ethnic|marital|occupation|job|city|county|"
    r"state|region|nationality|education|height|weight|language|religion_group)($|_)"
)
SENSITIVE_NAMES = re.compile(
    r"(^|_)(diagnosis|condition|disease|illness|icd|hiv|medication|drug|"
    r"income|salary|wage|debt|religion|sexual_orientation|orientation|"
    r"disability|criminal|conviction|outcome|treatment|test_result)($|_)"
)
VALUE_PATTERNS = {
    "email address": re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I),
    "US social security number": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "phone number": re.compile(r"^\+?(\d[\s().-]*){10,15}$"),
    "IP address": re.compile(r"^\d{1,3}(\.\d{1,3}){3}$"),
}


def _snake(column):
    return re.sub(r"[^a-z0-9]+", "_", column.lower()).strip("_")


def direct_identifiers(header, rows):
    """Return {column: reason} for columns that identify a person by themselves."""
    found = {}
    for col in header:
        values = [r[col] for r in rows if r[col]]
        if DIRECT_NAMES.search(_snake(col)):
            found[col] = "column name suggests a direct identifier"
            continue
        sample = values[:200]
        for label, pattern in VALUE_PATTERNS.items():
            if sample and sum(bool(pattern.match(v)) for v in sample) / len(sample) > 0.8:
                found[col] = f"values look like a {label}"
                break
        else:
            # Near-unique free-text columns behave like record IDs. Columns
            # that are known quasi-identifiers (e.g. birth_date) are excluded:
            # they are handled by generalization, not removal.
            name = _snake(col)
            if len(values) >= 20 and len(set(values)) / len(values) > 0.95 \
                    and not QUASI_NAMES.search(name) and not SENSITIVE_NAMES.search(name) \
                    and infer_kind(col, values) == "categorical":
                found[col] = "nearly every value is unique (acts like a record ID)"
    return found


def suggest_columns(header, exclude=()):
    """Guess quasi-identifier and sensitive columns from their names."""
    quasi, sensitive = [], []
    for col in header:
        if col in exclude:
            continue
        name = _snake(col)
        if SENSITIVE_NAMES.search(name):
            sensitive.append(col)
        elif QUASI_NAMES.search(name):
            quasi.append(col)
    return quasi, sensitive
