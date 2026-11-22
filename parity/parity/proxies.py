"""Proxy detection: which ordinary-looking features encode a protected attribute?

Removing a protected column does not remove bias if, say, ZIP code predicts race.
We measure association with bias-corrected Cramér's V (Bergsma, 2013), which is
0 for independence and 1 for a perfect one-to-one mapping.
"""

import math
from collections import Counter

from .data import to_float

STRONG, MODERATE = 0.30, 0.15


def _bin_numeric(values: list[str], bins: int = 5) -> list[str] | None:
    """Quantile-bin a column if it is mostly numeric with many distinct values."""
    nums = [to_float(v) for v in values]
    known = sorted(n for n in nums if n is not None)
    if len(known) < 0.9 * len(values) or len(set(known)) <= 10:
        return None
    cuts = [known[int(len(known) * i / bins)] for i in range(1, bins)]
    return ["NA" if n is None else f"q{sum(n >= c for c in cuts) + 1}" for n in nums]


def cramers_v(x: list[str], y: list[str]) -> float:
    """Bias-corrected Cramér's V between two categorical sequences."""
    n = len(x)
    if n < 2:
        return 0.0
    joint, cx, cy = Counter(zip(x, y)), Counter(x), Counter(y)
    chi2 = sum((joint[(a, b)] - cx[a] * cy[b] / n) ** 2 / (cx[a] * cy[b] / n)
               for a in cx for b in cy)
    r, k = len(cx), len(cy)
    phi2 = max(0.0, chi2 / n - (k - 1) * (r - 1) / (n - 1))
    r_c = r - (r - 1) ** 2 / (n - 1)
    k_c = k - (k - 1) ** 2 / (n - 1)
    denom = min(k_c - 1, r_c - 1)
    return math.sqrt(phi2 / denom) if denom > 0 else 0.0


def find_proxies(rows: list[dict], protected: list[str], exclude: list[str] = ()) -> list[dict]:
    """Score every non-protected column against every protected attribute.

    Returns rows sorted strongest-first:
    ``{"feature", "attribute", "v", "level"}`` with level in strong/moderate/weak.
    """
    if not rows:
        return []
    skip = set(protected) | set(exclude)
    found = []
    for col in rows[0]:
        if col in skip:
            continue
        raw = [r[col] for r in rows]
        if len(set(raw)) > 0.5 * len(rows) and _bin_numeric(raw) is None:
            continue  # identifier-like column (names, IDs): no signal, only noise
        values = _bin_numeric(raw) or raw
        for attr in protected:
            v = cramers_v(values, [r[attr] for r in rows])
            level = "strong" if v >= STRONG else "moderate" if v >= MODERATE else "weak"
            found.append({"feature": col, "attribute": attr, "v": round(v, 3), "level": level})
    return sorted(found, key=lambda d: -d["v"])
