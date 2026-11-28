"""Fairness metrics: selection rates, impact ratios, significance, error-rate parity.

Every number here is defined so it can be explained to a non-technical reader:

  selection rate  = selected / applicants                      (per group)
  impact ratio    = group's selection rate / highest group rate (1.0 = parity)
  p-value         = two-proportion z-test vs. the highest group (is the gap noise?)
  TPR (recall)    = selected / qualified       — are qualified people missed?
  FPR             = selected / not qualified   — who gets the benefit of the doubt?
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .data import Record

FOUR_FIFTHS = 0.8   # EEOC Uniform Guidelines (1978) rule of thumb for adverse impact
MIN_SHARE = 0.02    # NYC LL144 lets auditors set aside categories under 2% of the data
ALPHA = 0.05


@dataclass
class GroupStat:
    name: str
    n: int
    selected: int
    share: float                       # fraction of all applicants
    rate: float                        # selection (or scoring) rate
    impact_ratio: Optional[float] = None
    p_value: Optional[float] = None
    tpr: Optional[float] = None
    fpr: Optional[float] = None
    excluded: bool = False             # too small to judge reliably
    adverse: bool = False              # impact ratio below the audit threshold

    @property
    def significant(self) -> bool:
        return self.p_value is not None and self.p_value < ALPHA


@dataclass
class DimensionResult:
    name: str                          # e.g. "sex", "race", "sex × race"
    groups: list[GroupStat]
    reference: str                     # the group with the highest rate

    @property
    def flagged(self) -> list[GroupStat]:
        return [g for g in self.groups if g.adverse]

    @property
    def tpr_gap(self) -> Optional[float]:
        """Equal-opportunity gap: largest difference in TPR between groups."""
        vals = [g.tpr for g in self.groups if g.tpr is not None and not g.excluded]
        return max(vals) - min(vals) if len(vals) > 1 else None


@dataclass
class Audit:
    n: int
    overall_rate: float
    threshold: float
    dimensions: list[DimensionResult]
    has_labels: bool

    @property
    def passed(self) -> bool:
        return not any(d.flagged for d in self.dimensions)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> Optional[float]:
    """Two-sided p-value for H0: both groups share the same selection rate."""
    if not n1 or not n2:
        return None
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def _ratio(num: int, den: int) -> Optional[float]:
    return num / den if den else None


def audit_dimension(
    records: Sequence[Record],
    name: str,
    key: Callable[[Record], str],
    threshold: float = FOUR_FIFTHS,
    min_share: float = MIN_SHARE,
) -> DimensionResult:
    buckets: dict[str, list[Record]] = {}
    for r in records:
        buckets.setdefault(key(r), []).append(r)

    total = len(records)
    stats = []
    for g, rs in buckets.items():
        sel = sum(r.selected for r in rs)
        qualified = [r for r in rs if r.qualified]
        unqualified = [r for r in rs if r.qualified is False]
        stats.append(
            GroupStat(
                name=g,
                n=len(rs),
                selected=sel,
                share=len(rs) / total,
                rate=sel / len(rs),
                tpr=_ratio(sum(r.selected for r in qualified), len(qualified)),
                fpr=_ratio(sum(r.selected for r in unqualified), len(unqualified)),
                excluded=len(rs) / total < min_share,
            )
        )

    included = [s for s in stats if not s.excluded] or stats
    ref = max(included, key=lambda s: s.rate)
    for s in stats:
        if s.excluded:
            continue
        s.impact_ratio = s.rate / ref.rate if ref.rate else 1.0
        s.adverse = s.impact_ratio < threshold
        if s is not ref:
            s.p_value = two_proportion_p(s.selected, s.n, ref.selected, ref.n)

    stats.sort(key=lambda s: (s.excluded, -(s.impact_ratio or 0), s.name))
    return DimensionResult(name=name, groups=stats, reference=ref.name)


def run_audit(
    records: Sequence[Record],
    group_cols: Sequence[str],
    threshold: float = FOUR_FIFTHS,
    min_share: float = MIN_SHARE,
    intersectional: bool = True,
) -> Audit:
    """Audit every protected attribute on its own, then their intersection."""
    if not records:
        raise ValueError("no records to audit")

    dims = [
        audit_dimension(records, col, lambda r, c=col: r.groups[c], threshold, min_share)
        for col in group_cols
    ]
    if intersectional and len(group_cols) > 1:
        dims.append(
            audit_dimension(
                records,
                " × ".join(group_cols),
                lambda r: " · ".join(r.groups[c] for c in group_cols),
                threshold,
                min_share,
            )
        )

    return Audit(
        n=len(records),
        overall_rate=sum(r.selected for r in records) / len(records),
        threshold=threshold,
        dimensions=dims,
        has_labels=any(r.qualified is not None for r in records),
    )
