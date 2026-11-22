"""Small, dependency-free statistics helpers.

Everything here works on plain counts so the audit never needs NumPy/SciPy.
"""

from __future__ import annotations

import math


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n (well-behaved at small n)."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value for H0: p1 == p2 using the pooled z-test."""
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def fisher_exact(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher exact p-value for a 2x2 table (used when counts are small)."""
    total_k, total_n = k1 + k2, n1 + n2

    def log_pmf(x: int) -> float:  # hypergeometric, via log-gamma for stability
        return (_log_comb(n1, x) + _log_comb(n2, total_k - x)) - _log_comb(total_n, total_k)

    lo, hi = max(0, total_k - n2), min(total_k, n1)
    observed = log_pmf(k1)
    eps = 1e-7  # tolerance so ties with the observed table are counted
    p = sum(math.exp(lp) for lp in map(log_pmf, range(lo, hi + 1)) if lp <= observed + eps)
    return min(1.0, p)


def compare_rates(k1: int, n1: int, k2: int, n2: int) -> float:
    """Pick the right test: Fisher when any expected cell < 5, otherwise the z-test."""
    total_k, total_n = k1 + k2, n1 + n2
    if total_n == 0:
        return 1.0
    expected = [
        n * share
        for n in (n1, n2)
        for share in (total_k / total_n, 1 - total_k / total_n)
    ]
    if min(expected) < 5:
        return fisher_exact(k1, n1, k2, n2)
    return two_proportion_z(k1, n1, k2, n2)


def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
