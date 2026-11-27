"""Core audit logic: selection rates, impact ratios and verdicts.

Method (mirrors NYC Local Law 144 bias-audit rules and the EEOC "four-fifths"
guideline):

1. For every group, ``selection rate = favourable / total``.
2. The *reference* group is the eligible group with the highest rate.
3. ``impact ratio = group rate / reference rate``.
4. A ratio below ``threshold`` (default 0.80) is adverse impact. We then ask
   whether the gap is statistically meaningful so that reviewers can tell a
   systemic pattern from noise:

   * ``FAIL``    ratio < threshold and significant (p < alpha, enough data)
   * ``REVIEW``  ratio < threshold but not (yet) statistically conclusive
   * ``PASS``    ratio >= threshold
   * ``EXCLUDED`` group is < ``min_share`` of the data (LL144 allows this,
     but its counts must still be disclosed)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

from .data import Record
from .stats import two_proportion_p, underpowered, wilson_interval

JOIN = " × "


@dataclass
class GroupResult:
    group: str
    total: int
    selected: int
    share: float
    rate: float
    ci: tuple[float, float]
    ratio: float | None = None
    p_value: float | None = None
    low_power: bool = False
    status: str = "PASS"


@dataclass
class DimensionResult:
    dimension: str
    groups: list[GroupResult]
    reference: str | None
    unknown: int
    verdict: str = field(init=False)

    def __post_init__(self) -> None:
        statuses = {g.status for g in self.groups}
        self.verdict = "FAIL" if "FAIL" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"


def audit_dimension(
    records: list[Record],
    attrs: list[str],
    threshold: float = 0.8,
    min_share: float = 0.02,
    alpha: float = 0.05,
) -> DimensionResult:
    """Audit one attribute (or an intersection of several)."""
    totals: Counter[str] = Counter()
    selected: Counter[str] = Counter()
    unknown = 0
    for values, outcome in records:
        parts = [values[a] for a in attrs]
        if any(p is None for p in parts):
            unknown += 1
            continue
        key = JOIN.join(parts)  # type: ignore[arg-type]
        totals[key] += 1
        selected[key] += outcome

    known = sum(totals.values())
    groups = [
        GroupResult(
            group=g,
            total=n,
            selected=selected[g],
            share=n / known,
            rate=selected[g] / n,
            ci=wilson_interval(selected[g], n),
        )
        for g, n in totals.items()
    ]

    eligible = [g for g in groups if g.share >= min_share]
    for g in groups:
        if g.share < min_share:
            g.status = "EXCLUDED"
    ref = max(eligible, key=lambda g: (g.rate, g.total), default=None)

    if ref and ref.rate > 0:
        for g in groups:
            g.ratio = g.rate / ref.rate
            if g is ref:
                continue
            g.p_value = two_proportion_p(g.selected, g.total, ref.selected, ref.total)
            g.low_power = underpowered(g.selected, g.total, ref.selected, ref.total)
            if g.status == "EXCLUDED" or g.ratio >= threshold:
                continue
            g.status = "FAIL" if g.p_value < alpha and not g.low_power else "REVIEW"

    groups.sort(key=lambda g: (g.status == "EXCLUDED", -(g.ratio or 0), g.group))
    return DimensionResult(JOIN.join(attrs), groups, ref.group if ref else None, unknown)


def run_audit(
    records: list[Record],
    attributes: list[str],
    intersectional: bool = True,
    **options,
) -> list[DimensionResult]:
    """Audit each attribute alone, then their full intersection."""
    dims = [[a] for a in attributes]
    if intersectional and len(attributes) > 1:
        dims.append(list(attributes))
    return [audit_dimension(records, d, **options) for d in dims]


def to_dict(results: list[DimensionResult]) -> list[dict]:
    return [asdict(r) for r in results]
