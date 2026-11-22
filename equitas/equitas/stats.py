"""Small, dependency-free statistics helpers.

Everything here works on plain counts so it stays fast and easy to verify by hand.
"""
from __future__ import annotations

import math

Z95 = 1.959963984540054  # two-sided 95% normal quantile


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n.

    Preferred over the naive normal interval because it behaves well for
    small groups and for rates near 0 or 1 — exactly where bias hides.
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _log_hypergeom(a: int, row1: int, col1: int, n: int) -> float:
    """log P(X = a) for the hypergeometric distribution of a 2x2 table."""
    lc = lambda x, y: math.lgamma(x + 1) - math.lgamma(y + 1) - math.lgamma(x - y + 1)
    return lc(row1, a) + lc(n - row1, col1 - a) - lc(n, col1)


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test p-value for the table [[a, b], [c, d]]."""
    row1, col1, n = a + b, a + c, a + b + c + d
    lo, hi = max(0, col1 - (n - row1)), min(row1, col1)
    observed = _log_hypergeom(a, row1, col1, n)
    eps = 1e-7  # tolerance for floating-point ties
    total = sum(
        math.exp(lp)
        for x in range(lo, hi + 1)
        if (lp := _log_hypergeom(x, row1, col1, n)) <= observed + eps
    )
    return min(1.0, total)


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value that two selection rates differ.

    Uses a pooled z-test when every expected cell count is >= 5, otherwise
    falls back to Fisher's exact test, which is valid at any sample size.
    """
    if n1 == 0 or n2 == 0:
        return 1.0
    n = n1 + n2
    pooled = (k1 + k2) / n
    expected = (n1 * pooled, n1 * (1 - pooled), n2 * pooled, n2 * (1 - pooled))
    if min(expected) < 5:
        return fisher_exact(k1, n1 - k1, k2, n2 - k2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))
