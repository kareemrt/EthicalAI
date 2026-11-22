"""Core audit: selection rates, impact ratios, significance and error-rate parity.

Terminology (aligned with the EEOC four-fifths rule and NYC Local Law 144):

* selection rate  — share of a group that received the favourable outcome
* impact ratio    — a group's selection rate ÷ the highest group's selection rate
* adverse impact  — impact ratio below 0.80 *and* statistically significant
* review          — a gap worth a human look: ratio below 0.80 but not significant,
                    a significant gap with ratio below 0.90, or (with labels) qualified
                    members of the group selected at < 0.80× the reference group's rate
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import product

from .io import UNKNOWN, group_value, require_columns, to_binary
from .stats import compare_rates, wilson_interval

FOUR_FIFTHS = 0.80
ALPHA = 0.05

# Verdicts, from best to worst.
OK, REVIEW, ADVERSE, LOW_DATA, NOT_ASSESSED = "ok", "review", "adverse", "low data", "not assessed"


@dataclass
class GroupStat:
    name: str
    n: int
    selected: int
    share: float                      # share of all audited rows
    rate: float                       # selection rate
    ci: tuple[float, float]           # 95% Wilson interval for the rate
    impact_ratio: float | None = None
    p_value: float | None = None      # gap vs. everyone else in the dimension
    tpr: float | None = None          # true-positive rate, needs ground-truth labels
    fpr: float | None = None          # false-positive rate, needs ground-truth labels
    verdict: str = OK


@dataclass
class Dimension:
    name: str                         # e.g. "sex", or "sex × race" for intersections
    groups: list[GroupStat]
    reference: str | None             # group with the highest reliable selection rate

    @property
    def worst(self) -> GroupStat | None:
        rated = [g for g in self.groups if g.impact_ratio is not None]
        return min(rated, key=lambda g: g.impact_ratio) if rated else None


@dataclass
class Audit:
    total: int
    selected: int
    mode: str                         # "selection" or "score"
    cutoff: float | None
    has_labels: bool
    dimensions: list[Dimension] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.selected / self.total if self.total else 0.0

    @property
    def verdict(self) -> str:
        found = {g.verdict for d in self.dimensions for g in d.groups}
        return ADVERSE if ADVERSE in found else REVIEW if REVIEW in found else OK

    def to_dict(self) -> dict:
        return {**asdict(self), "rate": self.rate, "verdict": self.verdict}


def run_audit(
    rows: list[dict[str, str]],
    outcome: str,
    groups: list[str],
    label: str | None = None,
    threshold: float | None = None,
    intersect: bool = True,
    min_share: float = 0.02,
    min_n: int = 30,
) -> Audit:
    """Audit a decision log.

    rows      — records, e.g. from :func:`parity.load_csv`
    outcome   — column holding the decision (yes/no) or a score
    groups    — demographic columns to audit, e.g. ["sex", "race"]
    label     — optional ground-truth column ("was this person actually qualified?")
    threshold — score cut-off; defaults to the median when outcome is numeric
    intersect — also audit every combination of the group columns
    min_share / min_n — groups below either limit are reported but not judged
    """
    require_columns(rows, [outcome, *groups, *([label] if label else [])])
    selected, mode, cutoff = to_binary([r[outcome] for r in rows], threshold)
    truth = to_binary([r[label] for r in rows])[0] if label else None

    columns = [[c] for c in groups]
    if intersect and len(groups) > 1:
        columns.append(list(groups))

    audit = Audit(len(rows), sum(selected), mode, cutoff, truth is not None)
    for cols in columns:
        keys = [" · ".join(group_value(r, c) for c in cols) for r in rows]
        audit.dimensions.append(_dimension(" × ".join(cols), keys, selected, truth, min_share, min_n))
    return audit


def _dimension(name, keys, selected, truth, min_share, min_n) -> Dimension:
    total = len(keys)
    tally: dict[str, list[int]] = {}  # key -> [n, selected, tp, positives, fp, negatives]
    for i, key in enumerate(keys):
        t = tally.setdefault(key, [0, 0, 0, 0, 0, 0])
        t[0] += 1
        t[1] += selected[i]
        if truth is not None:
            pos = truth[i]
            t[2] += selected[i] and pos
            t[3] += pos
            t[4] += selected[i] and not pos
            t[5] += not pos

    stats = []
    for key, (n, k, tp, pos, fp, neg) in sorted(tally.items(), key=lambda kv: -kv[1][0]):
        g = GroupStat(key, n, k, n / total, k / n, wilson_interval(k, n))
        if truth is not None:
            g.tpr = tp / pos if pos else None
            g.fpr = fp / neg if neg else None
        if UNKNOWN in key.split(" · "):
            g.verdict = NOT_ASSESSED
        elif g.share < min_share or n < min_n:
            g.verdict = LOW_DATA
        stats.append(g)

    all_selected = sum(selected)
    judged = [g for g in stats if g.verdict == OK]
    ref = max(judged, key=lambda g: g.rate, default=None)
    if ref and ref.rate > 0:
        for g in stats:
            if g.verdict == NOT_ASSESSED:
                continue
            g.impact_ratio = g.rate / ref.rate
            # One-vs-rest test: robust even when the top group is small.
            g.p_value = compare_rates(g.selected, g.n, all_selected - g.selected, total - g.n)
            if g.verdict == OK:
                g.verdict = _judge(g.impact_ratio, g.p_value)
            # Equal opportunity: qualified people in this group are passed over more often.
            if g.verdict == OK and g.tpr is not None and ref.tpr and g.tpr / ref.tpr < FOUR_FIFTHS:
                g.verdict = REVIEW
    return Dimension(name, stats, ref.name if ref else None)


def _judge(ratio: float, p: float) -> str:
    low, significant = ratio < FOUR_FIFTHS, p < ALPHA
    if low and significant:
        return ADVERSE
    return REVIEW if low or (significant and ratio < 0.9) else OK
