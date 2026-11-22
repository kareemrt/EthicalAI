"""Selection rates, impact ratios and two-proportion significance tests."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from .data import UNKNOWN, _require, category, outcomes

FOUR_FIFTHS = 0.8


class Status(str, Enum):
    OK = "ok"              # impact ratio >= threshold and no significant gap
    WATCH = "watch"        # ratio passes, but the gap is statistically real
    REVIEW = "review"      # ratio fails, but sample too small to be sure
    ADVERSE = "adverse"    # ratio fails AND the gap is statistically significant
    EXCLUDED = "excluded"  # category below min_share; reported, not rated

    @property
    def icon(self) -> str:
        return {"ok": "✓", "watch": "◐", "review": "!", "adverse": "✕", "excluded": "–"}[self.value]


@dataclass(frozen=True)
class GroupResult:
    name: str
    n: int
    selected: int
    rate: float
    share: float
    impact_ratio: float | None
    p_value: float | None
    status: Status


@dataclass
class Audit:
    dimension: str                     # e.g. "sex" or "sex × race"
    groups: list[GroupResult]
    reference: str | None              # category with the highest rate
    unknown: int                       # rows with a missing category
    total: int
    threshold: float = FOUR_FIFTHS
    alpha: float = 0.05
    meta: dict = field(default_factory=dict)

    @property
    def worst(self) -> Status:
        order = [Status.ADVERSE, Status.REVIEW, Status.WATCH, Status.OK]
        found = {g.status for g in self.groups}
        return next((s for s in order if s in found), Status.OK)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test."""
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm–Bonferroni adjusted p-values (controls family-wise error rate)."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(ordered), 0.0, {}
    for i, (k, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def audit(
    rows: list[dict[str, str]],
    attrs: list[str],
    *,
    outcome: str | None = None,
    score: str | None = None,
    threshold: float = FOUR_FIFTHS,
    alpha: float = 0.05,
    min_share: float = 0.02,
    correct: bool = True,
) -> Audit:
    """Audit one dimension (a single attribute, or an intersection of several)."""
    _require(rows, attrs)
    picks = outcomes(rows, outcome=outcome, score=score)

    tally: dict[str, list[int]] = {}
    for row, hit in zip(rows, picks):
        n_sel = tally.setdefault(category(row, attrs), [0, 0])
        n_sel[0] += 1
        n_sel[1] += hit

    unknown = tally.pop(UNKNOWN, [0, 0])[0]
    known = sum(n for n, _ in tally.values())
    stats = {k: (n, s, s / n, n / known) for k, (n, s) in tally.items()}
    rated = {k: v for k, v in stats.items() if v[3] >= min_share}

    ref = max(rated, key=lambda k: (rated[k][2], rated[k][0])) if rated else None
    ref_n, ref_s, ref_rate, _ = rated[ref] if ref else (0, 0, 0.0, 0)

    raw = {k: two_proportion_p(s, n, ref_s, ref_n) for k, (n, s, _, _) in rated.items() if k != ref}
    pvals = holm(raw) if correct else raw

    groups = []
    for name, (n, s, rate, share) in stats.items():
        if name not in rated or ref is None:
            ir = p = None
            status = Status.EXCLUDED
        else:
            ir = rate / ref_rate if ref_rate else 1.0
            p = pvals.get(name, 1.0)
            low, sig = ir < threshold, p < alpha
            status = (Status.ADVERSE if sig else Status.REVIEW) if low else (Status.WATCH if sig else Status.OK)
        groups.append(GroupResult(name, n, s, rate, share, ir, p, status))

    groups.sort(key=lambda g: (g.impact_ratio is None, -(g.impact_ratio or 0), -g.n))
    return Audit(
        dimension=" × ".join(attrs),
        groups=groups,
        reference=ref,
        unknown=unknown,
        total=len(rows),
        threshold=threshold,
        alpha=alpha,
        meta={"mode": "scoring rate" if score else "selection rate", "column": score or outcome,
              "correction": "holm" if correct else "none"},
    )
