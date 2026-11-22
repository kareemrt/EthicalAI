"""Core fairness math. Pure functions, no I/O.

Definitions follow NYC Local Law 144 (6 RCNY §5-300) and the EEOC
"four-fifths rule" (29 CFR §1607.4(D)):

  selection rate = selected / total                       (per category)
  scoring rate   = share of a category scoring above the overall median
  impact ratio   = category rate / rate of the most-favoured category

An impact ratio below 0.8 is the conventional signal of adverse impact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

FOUR_FIFTHS = 0.8
MIN_SHARE = 0.02  # LL144 lets auditors set aside categories under 2% of the data


@dataclass(frozen=True)
class GroupResult:
    group: str
    total: int
    selected: int
    rate: float
    impact_ratio: float | None  # None when the group is too small to judge
    p_value: float | None  # vs. the most-favoured group
    share: float

    @property
    def status(self) -> str:
        if self.impact_ratio is None:
            return "too few"
        if round(self.impact_ratio, 9) < FOUR_FIFTHS:  # guard float noise at the boundary
            significant = self.p_value is not None and self.p_value < 0.05
            return "adverse impact" if significant else "adverse (n.s.)"
        return "ok"

    @property
    def flagged(self) -> bool:
        return self.status.startswith("adverse")


def two_proportion_p_value(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test."""
    if min(n1, n2) == 0:
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def median(values: Iterable[float]) -> float:
    s = sorted(values)
    if not s:
        raise ValueError("median of empty sequence")
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def audit(
    records: Iterable[tuple[str, bool]],
    min_share: float = MIN_SHARE,
) -> list[GroupResult]:
    """Audit (group, selected) pairs. Returns results sorted by rate, highest first."""
    counts: dict[str, list[int]] = {}
    for group, selected in records:
        c = counts.setdefault(group, [0, 0])
        c[0] += 1
        c[1] += bool(selected)

    grand_total = sum(n for n, _ in counts.values())
    if grand_total == 0:
        return []

    eligible = {g: c for g, c in counts.items() if c[0] / grand_total >= min_share}
    ref_group = max(eligible, key=lambda g: eligible[g][1] / eligible[g][0], default=None)
    ref_n, ref_x = eligible[ref_group] if ref_group else (0, 0)
    ref_rate = ref_x / ref_n if ref_n else 0.0

    results = []
    for group, (n, x) in counts.items():
        rate = x / n
        judged = group in eligible and ref_rate > 0
        results.append(
            GroupResult(
                group=group,
                total=n,
                selected=x,
                rate=rate,
                impact_ratio=rate / ref_rate if judged else None,
                p_value=two_proportion_p_value(x, n, ref_x, ref_n) if judged and group != ref_group else None,
                share=n / grand_total,
            )
        )
    return sorted(results, key=lambda r: (-r.rate, r.group))
