"""Small, dependency-free statistics helpers.

Everything here is closed-form so audits stay fast and reproducible
on any machine with a Python interpreter.
"""

from math import erfc, sqrt

Z95 = 1.959964  # two-sided 95% normal quantile


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n.

    Preferred over the naive normal interval because it behaves well
    for small groups and rates near 0 or 1 -- exactly where bias
    audits tend to live.
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value for H0: p1 == p2 (pooled two-proportion z-test)."""
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    var = pooled * (1 - pooled) * (1 / n1 + 1 / n2)
    if var == 0:
        return 1.0
    z = abs(k1 / n1 - k2 / n2) / sqrt(var)
    return erfc(z / sqrt(2))  # == 2 * (1 - Phi(|z|))


def ratio(a: float, b: float) -> float | None:
    """a / b, or None when b is zero."""
    return a / b if b else None
