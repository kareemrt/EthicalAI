"""Core audit math. Pure functions, no I/O.

Implements the impact-ratio method used by NYC Local Law 144 bias audits
and the EEOC "four-fifths rule", plus a significance test so that small,
noisy gaps are separated from gaps that are very unlikely to be chance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median

TRUTHY = {"1", "true", "t", "yes", "y", "selected", "hired", "advanced", "pass"}
UNKNOWN = "Unknown"

# Status ladder, from most to least serious.
ADVERSE, WATCH, OK, REFERENCE, EXCLUDED = "adverse", "watch", "ok", "reference", "excluded"
SEVERITY = {ADVERSE: 3, WATCH: 2, OK: 1, REFERENCE: 0, EXCLUDED: 0}


@dataclass
class GroupStat:
    name: str
    n: int
    selected: int
    share: float                      # fraction of the audited population
    rate: float                       # selection (or scoring) rate
    impact_ratio: float | None = None  # rate / reference rate
    p_value: float | None = None      # two-proportion z-test vs reference
    shortfall: int = 0                # extra selections needed to reach the threshold
    status: str = OK


@dataclass
class Dimension:
    name: str
    groups: list[GroupStat]
    reference: str | None

    @property
    def status(self) -> str:
        return max((g.status for g in self.groups), key=SEVERITY.get, default=OK)


@dataclass
class Audit:
    outcome: str
    mode: str                 # "selection" (binary outcome) or "scoring" (above median)
    n: int
    threshold: float
    alpha: float
    min_share: float
    cutoff: float | None      # median score used in scoring mode
    dimensions: list[Dimension]

    @property
    def status(self) -> str:
        return max((d.status for d in self.dimensions), key=SEVERITY.get, default=OK)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value for H0: both groups share the same underlying rate."""
    if not (n1 and n2):
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def binarize(rows: list[dict], outcome: str | None = None, score: str | None = None):
    """Turn each row into True/False. Returns (outcomes, mode, cutoff).

    * selection mode: truthy values in `outcome` count as selected.
    * scoring mode:   a score strictly above the sample median counts as
                      "selected" — LL144's definition of a scoring rate.
    """
    if (outcome is None) == (score is None):
        raise ValueError("Provide exactly one of `outcome` or `score`.")
    if outcome:
        return [str(r.get(outcome, "")).strip().lower() in TRUTHY for r in rows], "selection", None
    try:
        values = [float(r[score]) for r in rows]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Column '{score}' must exist and be numeric: {exc}") from None
    cutoff = median(values)
    return [v > cutoff for v in values], "scoring", cutoff


def audit_dimension(name: str, labels: list[str], outcomes: list[bool],
                    threshold: float = 0.8, alpha: float = 0.05,
                    min_share: float = 0.02) -> Dimension:
    """Compute per-group rates and impact ratios for a single attribute."""
    total = len(labels)
    counts: dict[str, list[int]] = {}
    for label, hit in zip(labels, outcomes):
        c = counts.setdefault(label, [0, 0])
        c[0] += 1
        c[1] += hit

    groups = [GroupStat(g, n, s, n / total, s / n) for g, (n, s) in counts.items()]
    eligible = [g for g in groups if g.name != UNKNOWN and g.share >= min_share]
    for g in groups:
        if g not in eligible:
            g.status = EXCLUDED

    ref = max(eligible, key=lambda g: g.rate, default=None)
    if ref and ref.rate > 0:
        for g in groups:
            g.impact_ratio = g.rate / ref.rate
            if g is ref:
                g.status = REFERENCE
                continue
            g.p_value = two_proportion_p(g.selected, g.n, ref.selected, ref.n)
            g.shortfall = max(0, math.ceil(threshold * ref.rate * g.n - g.selected - 1e-9))
            if g.status != EXCLUDED and g.impact_ratio < threshold:
                g.status = ADVERSE if g.p_value < alpha else WATCH

    groups.sort(key=lambda g: (g.status == EXCLUDED, -g.rate, g.name))
    return Dimension(name, groups, ref.name if ref else None)


def run_audit(rows: list[dict], attrs: list[str], outcome: str | None = None,
              score: str | None = None, intersect: bool = True,
              threshold: float = 0.8, alpha: float = 0.05,
              min_share: float = 0.02) -> Audit:
    """Audit every attribute in `attrs` (and their intersection, if 2+)."""
    if not rows:
        raise ValueError("No rows to audit.")
    missing = [a for a in attrs if a not in rows[0]]
    if missing:
        raise ValueError(f"Missing column(s): {', '.join(missing)}")

    outcomes, mode, cutoff = binarize(rows, outcome, score)
    label = lambda r, a: (str(r.get(a) or "").strip() or UNKNOWN)

    columns = {a: [label(r, a) for r in rows] for a in attrs}
    if intersect and len(attrs) > 1:
        combo = []
        for parts in zip(*columns.values()):
            combo.append(UNKNOWN if UNKNOWN in parts else " · ".join(parts))
        columns[" × ".join(attrs)] = combo

    dims = [audit_dimension(name, labels, outcomes, threshold, alpha, min_share)
            for name, labels in columns.items()]
    return Audit(outcome or score, mode, len(rows), threshold, alpha, min_share, cutoff, dims)
