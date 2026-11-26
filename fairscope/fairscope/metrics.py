"""Fairness metrics: selection rates, impact ratios, significance and error-rate parity.

Definitions
-----------
selection rate   share of a group that received the favourable outcome
impact ratio     group selection rate / highest group selection rate
                 (NYC Local Law 144; < 0.80 breaches the EEOC four-fifths rule)
p-value          two-proportion z-test, group vs. the highest-rate (benchmark) group
TPR / FPR        true- and false-positive rates when ground-truth labels exist
                 (equal opportunity / equalized odds)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from math import erfc, sqrt

PASS, REVIEW, FAIL = "PASS", "REVIEW", "FAIL"


@dataclass
class GroupStats:
    name: str
    n: int
    selected: int
    share: float                      # share of all records
    rate: float                       # selection rate
    impact_ratio: float = 1.0
    p_value: float = 1.0
    tpr: float | None = None
    fpr: float | None = None
    excluded: bool = False            # too small to judge reliably
    flags: list[str] = field(default_factory=list)


@dataclass
class Audit:
    attribute: str
    total: int
    overall_rate: float
    groups: list[GroupStats]
    threshold: float
    verdict: str
    findings: list[str]
    tpr_gap: float | None = None
    fpr_gap: float | None = None


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value that two proportions differ (normal approximation)."""
    if not n1 or not n2:
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return erfc(abs(z) / sqrt(2))


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def audit(
    attribute: str,
    groups: list[str],
    selected: list[bool],
    labels: list[bool] | None = None,
    threshold: float = 0.8,
    min_share: float = 0.02,
    alpha: float = 0.05,
    gap_limit: float = 0.10,
) -> Audit:
    """Audit one attribute (or intersection). Returns per-group stats and a verdict."""
    if len(groups) != len(selected) or (labels and len(labels) != len(groups)):
        raise ValueError("groups, selected and labels must be the same length")
    total, total_sel = len(groups), sum(selected)
    n, sel = Counter(groups), Counter(g for g, s in zip(groups, selected) if s)

    stats = []
    for g in sorted(n, key=lambda k: (-n[k], k)):
        gs = GroupStats(g, n[g], sel[g], n[g] / total, sel[g] / n[g])
        gs.excluded = gs.share < min_share
        if labels:
            rows = [(s, y) for gg, s, y in zip(groups, selected, labels) if gg == g]
            pos = [s for s, y in rows if y]
            neg = [s for s, y in rows if not y]
            gs.tpr, gs.fpr = _rate(sum(pos), len(pos)), _rate(sum(neg), len(neg))
        stats.append(gs)

    eligible = [g for g in stats if not g.excluded] or stats
    top = max(eligible, key=lambda g: g.rate)
    best = top.rate
    findings: list[str] = []
    verdict = PASS

    for g in stats:
        g.impact_ratio = g.rate / best if best else 1.0
        if g is not top:
            g.p_value = two_proportion_p(g.selected, g.n, top.selected, top.n)
        if g.excluded:
            g.flags.append("small sample")
            continue
        if g.impact_ratio < threshold:
            significant = g.p_value < alpha
            g.flags.append("adverse impact" if significant else "low ratio, not significant")
            findings.append(
                f"{g.name}: impact ratio {g.impact_ratio:.3f} (< {threshold:.2f}), "
                f"selected {g.rate:.1%} vs {best:.1%} for {top.name}, p={g.p_value:.3g}"
            )
            verdict = FAIL if significant else max(verdict, REVIEW, key=_severity)

    tpr_gap = fpr_gap = None
    if labels:
        tprs = [g.tpr for g in eligible if g.tpr is not None]
        fprs = [g.fpr for g in eligible if g.fpr is not None]
        tpr_gap = max(tprs) - min(tprs) if len(tprs) > 1 else 0.0
        fpr_gap = max(fprs) - min(fprs) if len(fprs) > 1 else 0.0
        for name, gap in (("true-positive rate (equal opportunity)", tpr_gap),
                          ("false-positive rate", fpr_gap)):
            if gap > gap_limit:
                findings.append(f"{name} differs by {gap:.1%} across groups (limit {gap_limit:.0%})")
                verdict = max(verdict, REVIEW, key=_severity)

    small = [g.name for g in stats if g.excluded]
    if small:
        findings.append(f"excluded for small sample (< {min_share:.0%} of records): {', '.join(small)}")

    return Audit(attribute, total, total_sel / total, stats, threshold, verdict, findings, tpr_gap, fpr_gap)


def _severity(v: str) -> int:
    return {PASS: 0, REVIEW: 1, FAIL: 2}[v]


def worst(verdicts) -> str:
    return max(verdicts, key=_severity, default=PASS)
