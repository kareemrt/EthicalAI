"""Small, dependency-free statistics helpers."""

from __future__ import annotations

from math import erfc, sqrt

Z95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (robust for small n)."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value for H0: p1 == p2 (pooled two-proportion z-test)."""
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return erfc(abs(z) / sqrt(2))


def underpowered(x1: int, n1: int, x2: int, n2: int) -> bool:
    """True when the normal approximation is shaky (any expected cell < 5)."""
    total = n1 + n2
    if total == 0:
        return True
    pooled = (x1 + x2) / total
    return min(n1 * pooled, n1 * (1 - pooled), n2 * pooled, n2 * (1 - pooled)) < 5
