"""Core fairness math. Pure functions, no I/O.

Implements the impact-ratio methodology used by NYC Local Law 144 bias audits
and the EEOC "four-fifths rule", plus a two-proportion z-test so that small,
noisy gaps are not mistaken for systemic ones (and vice versa).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

# Status labels, ordered from best to worst.
OK, REVIEW, ADVERSE, EXCLUDED = "ok", "review", "adverse", "excluded"


@dataclass(frozen=True)
class GroupStat:
    """Outcome statistics for one category (e.g. "Female") within a dimension."""

    group: str
    total: int
    selected: int
    rate: float
    share: float  # fraction of the audited population in this group
    impact_ratio: float | None  # None when excluded for small size
    p_value: float | None  # vs. the highest-rate group; None for that group
    shortfall: int  # extra selections needed to reach the threshold
    status: str


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value for H0: rate1 == rate2 (pooled z-test)."""
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def shortfall(selected: int, total: int, target_rate: float) -> int:
    """How many more people in this group would need a positive outcome
    for its rate to reach `target_rate`. A concrete, explainable remedy size."""
    return max(0, math.ceil(target_rate * total - selected - 1e-9))


def audit_groups(
    pairs: Iterable[tuple[str, bool]],
    threshold: float = 0.8,
    min_share: float = 0.02,
    alpha: float = 0.05,
) -> list[GroupStat]:
    """Compute per-group selection rates and impact ratios.

    pairs      -- (group, selected) for every person with a known group
    threshold  -- impact ratio below which a group is flagged (0.8 = 4/5ths rule)
    min_share  -- groups smaller than this fraction are reported but excluded
                  from impact-ratio calculations (LL144 permits 2%)
    alpha      -- significance level separating "adverse" from "review"
    """
    totals: Counter[str] = Counter()
    hits: Counter[str] = Counter()
    for group, selected in pairs:
        totals[group] += 1
        hits[group] += bool(selected)

    n = sum(totals.values())
    if n == 0:
        return []

    eligible = [g for g in totals if totals[g] / n >= min_share] or list(totals)
    ref = max(eligible, key=lambda g: hits[g] / totals[g])
    ref_rate = hits[ref] / totals[ref]

    stats = []
    for g in sorted(totals, key=lambda g: (-totals[g], g)):
        t, s = totals[g], hits[g]
        rate = s / t
        if g not in eligible:
            stats.append(GroupStat(g, t, s, rate, t / n, None, None, 0, EXCLUDED))
            continue

        ir = rate / ref_rate if ref_rate else 1.0
        p = None if g == ref else two_proportion_p(s, t, hits[ref], totals[ref])
        if ir >= threshold:
            status = OK
        elif p is not None and p < alpha:
            status = ADVERSE
        else:
            status = REVIEW  # below threshold, but sample too small to be sure
        gap = shortfall(s, t, threshold * ref_rate) if status != OK else 0
        stats.append(GroupStat(g, t, s, rate, t / n, ir, p, gap, status))
    return stats


def worst_status(stats: Iterable[GroupStat]) -> str:
    order = {OK: 0, EXCLUDED: 0, REVIEW: 1, ADVERSE: 2}
    return max((s.status for s in stats), key=order.__getitem__, default=OK)
