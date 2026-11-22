"""Pure fairness metrics. No I/O, no dependencies — easy to test and reuse."""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from statistics import median

FOUR_FIFTHS = 0.8   # EEOC Uniform Guidelines, 29 CFR 1607.4(D)
MIN_SHARE = 0.02    # NYC LL144 lets auditors exclude categories < 2% of the data


@dataclass
class GroupStat:
    group: str
    n: int
    selected: int
    rate: float
    impact_ratio: float = 1.0
    p_value: float = 1.0          # vs. the most-selected group
    tpr: float | None = None      # selection rate among the truly qualified
    flags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value of a pooled two-proportion z-test."""
    if min(n1, n2) == 0:
        return 1.0
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = abs(x1 / n1 - x2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def binarize(scores: list[float], threshold: float | None = None) -> tuple[list[bool], float]:
    """LL144 "scoring rate": share of a group scoring above the overall median."""
    cut = median(scores) if threshold is None else threshold
    return [s > cut for s in scores], cut


def audit(groups: list[str], selected: list[bool], qualified: list[bool] | None = None,
          alpha: float = 0.05) -> list[GroupStat]:
    """Return per-group stats, sorted from most- to least-selected.

    groups    – category label for each person
    selected  – did the tool select / advance / score them highly?
    qualified – optional ground truth, enables the equal-opportunity (TPR) gap
    """
    if not (len(groups) == len(selected) and (qualified is None or len(qualified) == len(groups))):
        raise ValueError("groups, selected and qualified must be the same length")

    tally: dict[str, list[int]] = {}              # group -> [n, sel, qual, qual&sel]
    for i, g in enumerate(groups):
        t = tally.setdefault(g, [0, 0, 0, 0])
        t[0] += 1
        t[1] += selected[i]
        if qualified is not None and qualified[i]:
            t[2] += 1
            t[3] += selected[i]

    stats = [
        GroupStat(g, n, s, s / n, tpr=(qs / q if qualified is not None and q else None))
        for g, (n, s, q, qs) in tally.items()
    ]
    stats.sort(key=lambda st: (-st.rate, st.group))

    total = len(groups)
    eligible = [st for st in stats if st.n / total >= MIN_SHARE] or stats
    ref = eligible[0]                              # most-selected eligible group
    best_tpr = max((st.tpr for st in eligible if st.tpr is not None), default=None)

    for st in stats:
        st.impact_ratio = st.rate / ref.rate if ref.rate else 1.0
        st.p_value = 1.0 if st is ref else two_proportion_p(st.selected, st.n, ref.selected, ref.n)
        flags = []
        if st.n / total < MIN_SHARE:
            flags.append("small-sample")
        elif st.impact_ratio < FOUR_FIFTHS:
            flags.append("adverse-impact")
            if st.p_value < alpha:
                flags.append("significant")
        if best_tpr and st.tpr is not None and st.tpr / best_tpr < FOUR_FIFTHS:
            flags.append("opportunity-gap")
        st.flags = tuple(flags)
    return stats
