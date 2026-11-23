"""Small, dependency-free statistics helpers."""

from math import erfc, sqrt


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test.

    Answers: "could a gap this large between two selection rates plausibly be
    chance?" Small p (e.g. < 0.05) means the gap is unlikely to be noise.
    """
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return erfc(abs(z) / sqrt(2))
