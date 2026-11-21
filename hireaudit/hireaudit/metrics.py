"""Fairness metrics: selection rates, impact ratios and significance tests.

Definitions follow NYC Local Law 144 (6 RCNY 5-300) and the EEOC
"four-fifths rule" (29 CFR 1607.4(D)):

  selection rate  = selected / applicants             (per category)
  impact ratio    = category rate / highest category rate
  adverse impact  = impact ratio below the threshold (default 0.8)

Because small groups produce noisy ratios, every comparison also carries a
two-sided Fisher exact p-value against the reference (highest-rate) group.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .data import Dataset

SEPARATOR = " × "
SEVERITY = {"FAIL": 3, "REVIEW": 2, "PASS": 1, "N/A": 0, "EXCLUDED": 0}


@dataclass
class Group:
    name: str
    n: int
    selected: int
    share: float                         # share of applicants with a known category
    impact_ratio: Optional[float] = None
    p_value: Optional[float] = None
    status: str = "N/A"

    @property
    def rate(self) -> float:
        return self.selected / self.n if self.n else 0.0


@dataclass
class Audit:
    attribute: str
    groups: list[Group]
    unknown: int
    reference: Optional[str]
    threshold: float
    alpha: float
    min_share: float

    @property
    def status(self) -> str:
        return max((g.status for g in self.groups), key=SEVERITY.get, default="N/A")

    @property
    def total(self) -> int:
        return self.unknown + sum(g.n for g in self.groups)


@dataclass(frozen=True)
class Config:
    threshold: float = 0.8    # four-fifths rule
    alpha: float = 0.05       # significance level
    min_share: float = 0.02   # LL144 allows excluding categories < 2% of data
    intersect: bool = True    # also audit every combination of the columns


def audit_all(ds: Dataset, cfg: Config = Config()) -> list[Audit]:
    """Audit each demographic column, plus their intersection when requested."""
    audits = [audit(ds, (a,), cfg) for a in ds.attributes]
    if cfg.intersect and len(ds.attributes) > 1:
        audits.append(audit(ds, ds.attributes, cfg))
    return audits


def audit(ds: Dataset, columns: tuple[str, ...], cfg: Config = Config()) -> Audit:
    """Compute rates, impact ratios and p-values for one (combined) attribute."""
    idx = [ds.attributes.index(c) for c in columns]
    tally: dict[str, list[int]] = {}
    unknown = 0
    for labels, hit in ds.rows:
        values = [labels[i] for i in idx]
        if None in values:
            unknown += 1
            continue
        counts = tally.setdefault(SEPARATOR.join(values), [0, 0])
        counts[0] += 1
        counts[1] += hit

    known = sum(n for n, _ in tally.values()) or 1
    groups = [Group(name, n, s, n / known) for name, (n, s) in tally.items()]
    included = [g for g in groups if g.share >= cfg.min_share]
    for g in groups:
        if g not in included:
            g.status = "EXCLUDED"

    ref = max(included, key=lambda g: g.rate, default=None)
    if ref and ref.rate > 0:
        for g in included:
            g.impact_ratio = g.rate / ref.rate
            if g is not ref:
                g.p_value = fisher_exact(g.selected, g.n - g.selected,
                                         ref.selected, ref.n - ref.selected)
            g.status = classify(g.impact_ratio, g.p_value, cfg.threshold, cfg.alpha)

    groups.sort(key=lambda g: (g.status == "EXCLUDED", -g.rate, g.name))
    return Audit(SEPARATOR.join(columns), groups, unknown,
                 ref.name if ref else None, cfg.threshold, cfg.alpha, cfg.min_share)


def classify(ratio: float, p: Optional[float], threshold: float, alpha: float) -> str:
    """FAIL = below threshold *and* significant; REVIEW = one of the two."""
    low = ratio < threshold
    significant = p is not None and p < alpha
    if low and significant:
        return "FAIL"
    return "REVIEW" if low or significant else "PASS"


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test p-value for the table [[a, b], [c, d]].

    Sums the probability of every table with the same margins that is no more
    likely than the observed one. Uses log-gamma, so it is exact and fast
    even for tens of thousands of applicants.
    """
    row1, row2, col1 = a + b, c + d, a + c
    n = row1 + row2
    lo, hi = max(0, col1 - row2), min(row1, col1)

    def log_p(k: int) -> float:
        return _log_comb(row1, k) + _log_comb(row2, col1 - k) - _log_comb(n, col1)

    observed = log_p(a) + 1e-7   # tolerance for floating-point ties
    p = sum(math.exp(lp) for lp in map(log_p, range(lo, hi + 1)) if lp <= observed)
    return min(1.0, p)


def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
