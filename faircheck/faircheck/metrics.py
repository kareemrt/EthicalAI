"""Pure statistical helpers. No I/O, no state — easy to test and reuse."""

from math import erfc, sqrt


def rate(hits: int, total: int) -> float:
    """Share of `total` that are `hits` (0.0 when the group is empty)."""
    return hits / total if total else 0.0


def impact_ratios(rates: dict[str, float]) -> dict[str, float]:
    """Each group's rate divided by the highest group's rate.

    This is the "impact ratio" defined by NYC Local Law 144 and the basis of
    the EEOC four-fifths rule: a ratio below 0.8 is evidence of adverse impact.
    """
    best = max(rates.values(), default=0.0)
    return {g: (r / best if best else 0.0) for g, r in rates.items()}


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value for H0: both groups share the same underlying rate.

    Uses the pooled two-proportion z-test, the standard companion to the
    four-fifths rule in adverse-impact analysis.
    """
    if not n1 or not n2:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return erfc(abs(z) / sqrt(2))


def median(values: list[float]) -> float:
    s = sorted(values)
    if not s:
        raise ValueError("median of empty list")
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
