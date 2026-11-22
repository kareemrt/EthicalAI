"""Selection rates, impact ratios and significance testing.

The core test is the *four-fifths rule* (EEOC Uniform Guidelines, 29 CFR 1607.4D),
also used by NYC Local Law 144 bias audits: a group whose selection rate is below
80% of the most-selected group's rate shows evidence of adverse impact.
"""

import math
from dataclasses import dataclass, asdict

FOUR_FIFTHS = 0.8
MIN_SHARE = 0.02   # LL144 permits excluding categories under 2% of the data
ALPHA = 0.05


@dataclass
class GroupResult:
    group: str
    n: int
    selected: int
    rate: float
    impact_ratio: float | None  # None when the group is too small to rate
    p_value: float | None       # z-test vs. all other rated groups (only below threshold)
    status: str                 # "reference" | "pass" | "watch" | "fail" | "excluded"

    def as_dict(self) -> dict:
        return asdict(self)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value for H0: p1 == p2 (pooled two-proportion z-test)."""
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def intersect(rows: list[dict], columns: list[str]) -> list[str]:
    """Combine several attribute columns into one intersectional label per row."""
    return [" × ".join(r[c] or "Unknown" for c in columns) for r in rows]


def audit_attribute(groups: list[str], selected: list[bool],
                    threshold: float = FOUR_FIFTHS, min_share: float = MIN_SHARE,
                    alpha: float = ALPHA) -> list[GroupResult]:
    """Audit one (possibly intersectional) attribute.

    Status meanings:
      reference — the group with the highest selection rate
      pass      — impact ratio >= threshold
      watch     — below threshold, but not statistically significant
      fail      — below threshold *and* significantly lower than all other
                  rated groups combined (two-proportion z-test at ``alpha``)
      excluded  — fewer than ``min_share`` of all records; reported, not rated
    """
    counts: dict[str, list[int]] = {}
    for g, s in zip(groups, selected):
        c = counts.setdefault(g or "Unknown", [0, 0])
        c[0] += 1
        c[1] += s

    total = len(groups)
    rated = {g: c for g, c in counts.items() if c[0] / total >= min_share}
    if not rated:
        raise ValueError("no group meets the minimum share; lower min_share")
    ref = max(rated, key=lambda g: rated[g][1] / rated[g][0])
    ref_rate = rated[ref][1] / rated[ref][0]
    # Significance is tested against everyone else, not just the reference group, so
    # a small-but-eligible reference group cannot mask a large, real disparity.
    all_n = sum(c[0] for c in rated.values())
    all_x = sum(c[1] for c in rated.values())

    results = []
    for g, (n, x) in counts.items():
        rate = x / n
        if g not in rated:
            results.append(GroupResult(g, n, x, rate, None, None, "excluded"))
            continue
        ratio = rate / ref_rate if ref_rate else 1.0
        if g == ref:
            results.append(GroupResult(g, n, x, rate, 1.0, None, "reference"))
            continue
        if ratio >= threshold:
            results.append(GroupResult(g, n, x, rate, ratio, None, "pass"))
            continue
        p = two_proportion_p(x, n, all_x - x, all_n - n)
        lower = rate < (all_x - x) / (all_n - n)
        results.append(GroupResult(g, n, x, rate, ratio, p, "fail" if p < alpha and lower else "watch"))

    order = {"reference": 0, "pass": 1, "watch": 2, "fail": 3, "excluded": 4}
    return sorted(results, key=lambda r: (order[r.status], -(r.impact_ratio or 0)))
