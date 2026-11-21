"""Small, dependency-free statistics helpers used by the audit engine.

Everything here is standard-library only so AuditLens can run inside locked-down
HR / compliance environments where installing scientific Python is not an option.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

Z_95 = 1.959963984540054


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def wilson_interval(k: int, n: int, z: float = Z_95) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the naive Wald interval because it behaves sensibly for small
    groups and for rates close to 0 or 1 -- exactly the situations where
    under-represented groups end up in an audit.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_p_value(k1: int, n1: int, k2: int, n2: int) -> Optional[float]:
    """Two-sided p-value of a pooled two-proportion z-test.

    Returns ``None`` when the test is undefined (empty groups or a pooled rate
    of exactly 0 or 1).
    """
    if n1 <= 0 or n2 <= 0:
        return None
    pooled = (k1 + k2) / (n1 + n2)
    if pooled <= 0.0 or pooled >= 1.0:
        return None
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n1 + 1.0 / n2))
    if se == 0:
        return None
    z = (k1 / n1 - k2 / n2) / se
    return 2.0 * (1.0 - normal_cdf(abs(z)))


def ratio_interval(
    k1: int, n1: int, k2: int, n2: int, z: float = Z_95
) -> Optional[Tuple[float, float]]:
    """Confidence interval for the ratio of two proportions (Katz log method).

    ``(k1/n1) / (k2/n2)`` is the impact ratio of a group against the reference
    group. Returns ``None`` if either group has zero positive outcomes (the log
    transform is undefined).
    """
    if min(k1, k2) <= 0 or min(n1, n2) <= 0:
        return None
    ratio = (k1 / n1) / (k2 / n2)
    se = math.sqrt(max(0.0, 1.0 / k1 - 1.0 / n1 + 1.0 / k2 - 1.0 / n2))
    lo = math.exp(math.log(ratio) - z * se)
    hi = math.exp(math.log(ratio) + z * se)
    return (lo, hi)


def median(values) -> float:
    """Median of a non-empty sequence of numbers."""
    data = sorted(values)
    if not data:
        raise ValueError("median() of empty data")
    mid = len(data) // 2
    if len(data) % 2:
        return float(data[mid])
    return (data[mid - 1] + data[mid]) / 2.0
