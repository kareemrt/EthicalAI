"""Fairness metrics. Pure functions over plain records, no I/O.

A *record* is a tuple ``(group, selected, label)``:
    group     str           the demographic group (or intersection) of one person
    selected  bool          what the automated system decided (hired, approved, ...)
    label     bool | None   the ground-truth outcome, if known (qualified, repaid, ...)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional

FOUR_FIFTHS = 0.8  # EEOC Uniform Guidelines, 29 CFR 1607.4(D)

OK, WARN, FAIL, EXCLUDED = "OK", "WARN", "FAIL", "EXCLUDED"


@dataclass
class Group:
    name: str
    n: int = 0
    selected: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    share: float = 0.0          # fraction of all records in this group
    impact_ratio: float = 1.0   # selection rate / reference group's rate
    p_value: float = 1.0        # two-proportion z-test vs. reference group
    status: str = OK

    @property
    def rate(self) -> float:
        return self.selected / self.n if self.n else 0.0

    @property
    def tpr(self) -> Optional[float]:
        """True positive rate: of the truly qualified, how many were selected."""
        pos = self.tp + self.fn
        return self.tp / pos if pos else None

    @property
    def fpr(self) -> Optional[float]:
        """False positive rate: of the truly unqualified, how many were selected."""
        neg = self.fp + self.tn
        return self.fp / neg if neg else None


@dataclass
class Audit:
    attribute: str
    groups: list[Group]
    reference: str
    threshold: float
    alpha: float
    has_labels: bool

    @property
    def evaluated(self) -> list[Group]:
        return [g for g in self.groups if g.status != EXCLUDED]

    @property
    def failed(self) -> list[Group]:
        return [g for g in self.groups if g.status == FAIL]

    @property
    def warned(self) -> list[Group]:
        return [g for g in self.groups if g.status == WARN]

    @property
    def status(self) -> str:
        return FAIL if self.failed else WARN if self.warned else OK

    def gap(self, metric: str) -> Optional[float]:
        """Largest between-group difference in a rate (e.g. 'tpr' -> equal opportunity gap)."""
        values = [v for g in self.evaluated if (v := getattr(g, metric)) is not None]
        return max(values) - min(values) if len(values) > 1 else None


def two_proportion_p(s1: int, n1: int, s2: int, n2: int) -> float:
    """Two-sided p-value that two selection rates differ only by chance."""
    if not n1 or not n2:
        return 1.0
    pooled = (s1 + s2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (s1 / n1 - s2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def audit(
    records: Iterable[tuple[str, bool, Optional[bool]]],
    attribute: str = "group",
    threshold: float = FOUR_FIFTHS,
    alpha: float = 0.05,
    min_share: float = 0.0,
) -> Audit:
    """Compute per-group selection rates, impact ratios and error rates.

    Status per group:
        FAIL      impact ratio < threshold AND the gap is statistically significant
        WARN      impact ratio < threshold but the sample is too small to be sure
        OK        impact ratio >= threshold
        EXCLUDED  group is below ``min_share`` of the data (as NYC LL144 permits <2%)
    """
    by_name: dict[str, Group] = {}
    has_labels = False
    for name, selected, label in records:
        g = by_name.setdefault(name, Group(name))
        g.n += 1
        g.selected += bool(selected)
        if label is not None:
            has_labels = True
            if label:
                g.tp += selected
                g.fn += not selected
            else:
                g.fp += selected
                g.tn += not selected

    groups = sorted(by_name.values(), key=lambda g: g.name)
    total = sum(g.n for g in groups)
    if not total:
        raise ValueError("no records to audit")

    for g in groups:
        g.share = g.n / total
        if g.share < min_share:
            g.status = EXCLUDED

    evaluated = [g for g in groups if g.status != EXCLUDED] or groups
    ref = max(evaluated, key=lambda g: g.rate)

    for g in evaluated:
        g.status = OK
        g.impact_ratio = g.rate / ref.rate if ref.rate else 1.0
        if g is not ref:
            g.p_value = two_proportion_p(g.selected, g.n, ref.selected, ref.n)
        if g.impact_ratio < threshold:
            g.status = FAIL if g.p_value < alpha else WARN

    return Audit(attribute, groups, ref.name, threshold, alpha, has_labels)
