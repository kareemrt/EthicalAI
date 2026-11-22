"""Fairness statistics. Pure functions, standard library only.

Definitions follow common regulatory practice:
  * selection rate  = selected / total                (per group)
  * impact ratio    = group rate / highest group rate (NYC Local Law 144)
  * four-fifths rule: impact ratio < 0.8 signals adverse impact (EEOC, 29 CFR 1607.4D)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Z95 = 1.959964  # two-sided 95% normal quantile


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Stable for small n and k=0/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test (1.0 when undefined)."""
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def safe_div(a: float, b: float) -> float | None:
    return a / b if b else None


@dataclass
class GroupStats:
    name: str
    n: int = 0
    selected: int = 0
    # Confusion counts; only populated when ground-truth labels are supplied.
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    # Derived (filled by `analyse`).
    impact_ratio: float | None = None
    p_value: float | None = None
    flags: list[str] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.selected / self.n if self.n else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson_interval(self.selected, self.n)

    @property
    def tpr(self) -> float | None:  # equal opportunity: qualified people who get selected
        return safe_div(self.tp, self.tp + self.fn)

    @property
    def fpr(self) -> float | None:  # unqualified people who get selected
        return safe_div(self.fp, self.fp + self.tn)


@dataclass
class Audit:
    attribute: str
    groups: list[GroupStats]
    reference: str            # group with the highest selection rate
    threshold: float
    has_labels: bool

    @property
    def flagged(self) -> list[GroupStats]:
        return [g for g in self.groups if "adverse-impact" in g.flags]

    @property
    def min_ratio(self) -> float | None:
        ratios = [g.impact_ratio for g in self.groups if g.impact_ratio is not None]
        return min(ratios) if ratios else None

    def gap(self, metric: str) -> float | None:
        """Max - min of a per-group metric ('tpr' or 'fpr') across groups."""
        vals = [v for g in self.groups if (v := getattr(g, metric)) is not None]
        return max(vals) - min(vals) if len(vals) > 1 else None


def analyse(attribute: str, groups: list[GroupStats], threshold: float = 0.8,
            min_n: int = 30, has_labels: bool = False, alpha: float = 0.05) -> Audit:
    """Compute impact ratios, significance and flags for one protected attribute."""
    groups = sorted(groups, key=lambda g: (-g.rate, g.name))
    ref = groups[0]
    total = sum(g.n for g in groups)
    for g in groups:
        g.impact_ratio = safe_div(g.rate, ref.rate)
        g.p_value = None if g is ref else two_proportion_p(g.selected, g.n, ref.selected, ref.n)
        g.flags = []
        if g.impact_ratio is not None and g.impact_ratio < threshold:
            g.flags.append("adverse-impact")
            if g.p_value is not None and g.p_value < alpha:
                g.flags.append("significant")
        if g.n < min_n:
            g.flags.append("small-sample")
        if total and g.n / total < 0.02:  # LL144 permits excluding categories <2% of data
            g.flags.append("under-2%")
    return Audit(attribute, groups, ref.name, threshold, has_labels)
