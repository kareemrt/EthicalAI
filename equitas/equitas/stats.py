"""Small, dependency-free statistics helpers."""
from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n (95% by default).

    Better behaved than the normal approximation for small groups and for
    rates near 0 or 1 — exactly the cases a bias audit cares about.
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test (k1/n1 vs k2/n2)."""
    if not n1 or not n2:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def ratio(a: float | None, b: float | None) -> float | None:
    """a / b, or None when undefined."""
    if a is None or not b:
        return None
    return a / b
