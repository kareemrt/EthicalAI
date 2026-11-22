"""Fairness metrics for automated decisions.

Everything here is plain arithmetic on counts, so every number in a
report can be checked by hand:

* selection rate   = selected / total                (per group)
* impact ratio     = group rate / highest group rate (four-fifths rule)
* p-value          = is the gap vs. the top group bigger than chance?
                     Fisher's exact test for small cells, z-test otherwise
* equal opportunity = true-positive rate ratio (needs ground truth)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import comb, erfc, sqrt
from typing import Callable, Iterable

from .data import UNKNOWN, Record

FOUR_FIFTHS = 0.8
MIN_SHARE = 0.02   # LL144 lets auditors set aside categories under 2% of the sample
ALPHA = 0.05


@dataclass
class GroupStat:
    name: str
    n: int
    selected: int
    share: float                  # fraction of the whole sample
    rate: float                   # selection (or scoring) rate
    impact_ratio: float | None = None
    p_value: float | None = None
    test: str = ""
    tpr: float | None = None      # true-positive rate, if ground truth given
    tpr_ratio: float | None = None
    flags: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        """Whether this group is large and known enough to be a reference."""
        return self.name != UNKNOWN and self.share >= MIN_SHARE


@dataclass
class Audit:
    attribute: str
    groups: list[GroupStat]
    reference: str
    threshold: float

    @property
    def flagged(self) -> list[GroupStat]:
        return [g for g in self.groups if "adverse impact" in g.flags]


# --- statistics ----------------------------------------------------------

def z_test(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided two-proportion z-test p-value."""
    pooled = (x1 + x2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return erfc(abs(z) / sqrt(2))


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher's exact test p-value for the table [[a, b], [c, d]]."""
    row1, col1, n = a + b, a + c, a + b + c + d
    total = comb(n, col1)

    def prob(k: int) -> float:
        return comb(row1, k) * comb(n - row1, col1 - k) / total

    observed = prob(a)
    lo, hi = max(0, col1 - (n - row1)), min(row1, col1)
    p = sum(pk for k in range(lo, hi + 1) if (pk := prob(k)) <= observed * (1 + 1e-9))
    return min(1.0, p)


def compare(x1: int, n1: int, x2: int, n2: int) -> tuple[float, str]:
    """Pick the right test for the sample size and return (p, test name)."""
    cells = (x1, n1 - x1, x2, n2 - x2)
    if min(cells) < 5:
        return fisher_exact(*cells), "fisher"
    return z_test(x1, n1, x2, n2), "z"


# --- audit ---------------------------------------------------------------

def audit(
    records: list[Record],
    key: Callable[[Record], str],
    attribute: str,
    threshold: float = FOUR_FIFTHS,
) -> Audit:
    """Compute selection rates and impact ratios for each value of *key*."""
    buckets: dict[str, list[Record]] = {}
    for r in records:
        buckets.setdefault(key(r), []).append(r)

    total = len(records)
    groups = []
    for name, rs in buckets.items():
        sel = sum(r.selected for r in rs)
        g = GroupStat(name, len(rs), sel, len(rs) / total, sel / len(rs))
        positives = [r for r in rs if r.actual]
        if positives:
            g.tpr = sum(r.selected for r in positives) / len(positives)
        groups.append(g)

    pool = [g for g in groups if g.eligible] or groups
    ref = max(pool, key=lambda g: g.rate)
    best_tpr = max((g.tpr for g in pool if g.tpr is not None), default=None)

    for g in groups:
        if not g.eligible:
            g.flags.append("small sample" if g.name != UNKNOWN else "unknown category")
        if ref.rate > 0:
            g.impact_ratio = g.rate / ref.rate
        if g is not ref:
            g.p_value, g.test = compare(g.selected, g.n, ref.selected, ref.n)
        if best_tpr and g.tpr is not None:
            g.tpr_ratio = g.tpr / best_tpr
        if g.eligible and g.impact_ratio is not None and g.impact_ratio < threshold - 1e-9:
            g.flags.append("adverse impact")
            if g.p_value is not None and g.p_value < ALPHA:
                g.flags.append("statistically significant")
        if g.eligible and g.tpr_ratio is not None and g.tpr_ratio < threshold - 1e-9:
            g.flags.append("unequal opportunity")

    groups.sort(key=lambda g: (-g.rate, g.name))
    return Audit(attribute, groups, ref.name, threshold)


def run(
    records: list[Record],
    attributes: Iterable[str],
    intersectional: bool = False,
    threshold: float = FOUR_FIFTHS,
) -> list[Audit]:
    """Audit each attribute, plus every combination of them if requested."""
    attributes = list(attributes)
    audits = [audit(records, lambda r, a=a: r.groups[a], a, threshold) for a in attributes]
    if intersectional and len(attributes) > 1:
        label = " × ".join(attributes)
        audits.append(audit(
            records,
            lambda r: " · ".join(r.groups[a] for a in attributes),
            label,
            threshold,
        ))
    return audits
