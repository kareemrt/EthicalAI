"""Fairness metrics: selection rates, impact ratios, significance and error rates.

Every function here is pure and uses only the standard library, so the math
is easy to audit — which matters for a tool whose job is accountability.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from math import erfc, sqrt

from .data import UNKNOWN, Dataset

FOUR_FIFTHS = 0.80   # EEOC Uniform Guidelines, 29 CFR 1607.4(D)
MIN_SHARE = 0.02     # NYC LL144 lets auditors exclude categories < 2% of the data
ALPHA = 0.05         # significance level for the two-proportion z-test


# ── statistics helpers ────────────────────────────────────────────────────────

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n (well-behaved for small n)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided p-value that two groups share the same underlying rate."""
    if not n1 or not n2:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return erfc(abs(z) / sqrt(2))


def ratio(a: int, b: int) -> float | None:
    return a / b if b else None


# ── result types ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GroupStat:
    group: str
    n: int
    selected: int
    share: float
    rate: float
    ci: tuple[float, float]
    impact_ratio: float | None = None
    p_value: float | None = None
    tpr: float | None = None        # of truly-qualified people, share selected
    fpr: float | None = None        # of unqualified people, share selected

    @property
    def excluded(self) -> bool:
        return self.group == UNKNOWN or self.share < MIN_SHARE

    @property
    def status(self) -> str:
        """pass · warn (below 4/5ths but could be noise) · fail · n/a (excluded)."""
        if self.excluded or self.impact_ratio is None:
            return "n/a"
        if self.impact_ratio >= FOUR_FIFTHS:
            return "pass"
        return "fail" if (self.p_value or 1) < ALPHA else "warn"


@dataclass(frozen=True)
class AttributeAudit:
    attribute: str
    groups: list[GroupStat]
    reference: str | None                      # group with the highest rate
    tpr_gap: float | None = None               # equal-opportunity difference
    fpr_gap: float | None = None               # equalized-odds (FPR) difference

    @property
    def eligible(self) -> list[GroupStat]:
        return [g for g in self.groups if not g.excluded]

    @property
    def min_ratio(self) -> float | None:
        ratios = [g.impact_ratio for g in self.eligible if g.impact_ratio is not None]
        return min(ratios) if ratios else None

    @property
    def status(self) -> str:
        statuses = {g.status for g in self.groups}
        for s in ("fail", "warn", "pass"):
            if s in statuses:
                return s
        return "n/a"


@dataclass(frozen=True)
class Audit:
    rows: int
    mode: str
    threshold: float | None
    overall_rate: float
    has_labels: bool
    attributes: list[AttributeAudit] = field(default_factory=list)

    @property
    def status(self) -> str:
        statuses = {a.status for a in self.attributes}
        for s in ("fail", "warn", "pass"):
            if s in statuses:
                return s
        return "n/a"


# ── the audit itself ─────────────────────────────────────────────────────────

def audit_attribute(ds: Dataset, *attrs: str) -> AttributeAudit:
    """Compute per-group rates and compare every group to the most-selected one."""
    labels = ds.groups(*attrs)
    n, k = defaultdict(int), defaultdict(int)
    pos, tp, neg, fp = (defaultdict(int) for _ in range(4))

    for i, g in enumerate(labels):
        n[g] += 1
        k[g] += ds.selected[i]
        if ds.actual is not None:
            if ds.actual[i]:
                pos[g] += 1
                tp[g] += ds.selected[i]
            else:
                neg[g] += 1
                fp[g] += ds.selected[i]

    total = len(ds)
    eligible = [g for g in n if g != UNKNOWN and n[g] / total >= MIN_SHARE]
    ref = max(eligible, key=lambda g: k[g] / n[g], default=None)
    ref_rate = k[ref] / n[ref] if ref else 0

    stats = []
    for g in sorted(n, key=lambda g: (g == UNKNOWN, g not in eligible, -k[g] / n[g], g)):
        is_eligible = g in eligible
        stats.append(GroupStat(
            group=g, n=n[g], selected=k[g], share=n[g] / total,
            rate=k[g] / n[g], ci=wilson(k[g], n[g]),
            impact_ratio=(k[g] / n[g]) / ref_rate if is_eligible and ref_rate else None,
            p_value=two_proportion_p(k[g], n[g], k[ref], n[ref]) if is_eligible and g != ref else None,
            tpr=ratio(tp[g], pos[g]) if ds.actual is not None else None,
            fpr=ratio(fp[g], neg[g]) if ds.actual is not None else None,
        ))

    def gap(values):
        values = [v for v in values if v is not None]
        return max(values) - min(values) if len(values) > 1 else None

    elig_stats = [s for s in stats if not s.excluded]
    return AttributeAudit(
        attribute=" × ".join(attrs), groups=stats, reference=ref,
        tpr_gap=gap(s.tpr for s in elig_stats),
        fpr_gap=gap(s.fpr for s in elig_stats),
    )


def run_audit(ds: Dataset, attributes: list[str], intersect: bool = False) -> Audit:
    """Audit each attribute on its own and, optionally, all of them combined."""
    results = [audit_attribute(ds, a) for a in attributes]
    if intersect and len(attributes) > 1:
        results.append(audit_attribute(ds, *attributes))
    return Audit(
        rows=len(ds), mode=ds.mode, threshold=ds.threshold,
        overall_rate=sum(ds.selected) / len(ds),
        has_labels=ds.actual is not None, attributes=results,
    )
