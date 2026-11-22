"""Core audit: selection rates, impact ratios, significance and error-rate gaps."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from itertools import combinations

from .data import UNKNOWN, Record
from .stats import two_proportion_p, wilson_interval

ADVERSE, REVIEW, OK, EXCLUDED, REFERENCE = "adverse", "review", "ok", "excluded", "reference"


@dataclass
class Group:
    category: str
    n: int
    selected: int
    share: float                       # fraction of all applicants in this group
    rate: float                        # selection rate
    ci: tuple[float, float]            # 95% Wilson interval on the rate
    impact_ratio: float | None = None  # rate / highest group rate
    p_value: float | None = None       # vs. the reference group
    status: str = OK
    tpr: float | None = None           # selected | qualified   (needs --label)
    fpr: float | None = None           # selected | unqualified (needs --label)


@dataclass
class Attribute:
    name: str
    groups: list[Group]
    reference: str | None
    tpr_gap: float | None = None  # equal-opportunity gap (max - min TPR)

    @property
    def worst(self) -> Group | None:
        scored = [g for g in self.groups if g.impact_ratio is not None]
        return min(scored, key=lambda g: g.impact_ratio) if scored else None


@dataclass
class Audit:
    n: int
    selected: int
    attributes: list[Attribute]
    settings: dict = field(default_factory=dict)

    @property
    def rate(self) -> float:
        return self.selected / self.n if self.n else 0.0

    def findings(self, status: str = ADVERSE) -> list[tuple[Attribute, Group]]:
        return [(a, g) for a in self.attributes for g in a.groups if g.status == status]

    def kind(self, attr: Attribute, group: Group) -> str | None:
        """Classify a flagged intersectional group relative to its single-attribute parents.

        * ``hidden``     – no parent group is flagged: invisible on any single axis
        * ``compounded`` – a parent is flagged, but this group fares far worse still
                           (its rate is below ``ratio`` x the flagged parent's rate)
        * ``inherited``  – the gap is already explained by a flagged parent
        Returns ``None`` for single-attribute groups.
        """
        if " × " not in attr.name:
            return None
        single = {a.name: {g.category: g for g in a.groups} for a in self.attributes}
        parents = [single.get(n, {}).get(c) for n, c in zip(attr.name.split(" × "), group.category.split(" · "))]
        flagged = [p for p in parents if p is not None and p.status == ADVERSE]
        if not flagged:
            return "hidden"
        floor = min(p.rate for p in flagged)
        return "compounded" if group.rate < self.settings.get("ratio", 0.8) * floor else "inherited"

    def headline(self, status: str = ADVERSE) -> list[tuple[Attribute, Group]]:
        """Findings worth reading first: single-axis gaps plus hidden intersectional ones."""
        return [(a, g) for a, g in self.findings(status) if self.kind(a, g) != "inherited"]

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "selected": self.selected,
            "selection_rate": self.rate,
            "settings": self.settings,
            "attributes": [{**asdict(a), "worst": a.worst.category if a.worst else None} for a in self.attributes],
            "summary": {s: len(self.findings(s)) for s in (ADVERSE, REVIEW)},
            "headline": [{"attribute": a.name, "group": g.category, "status": g.status,
                          "impact_ratio": g.impact_ratio, "p_value": g.p_value}
                         for s in (ADVERSE, REVIEW) for a, g in self.headline(s)],
        }


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _assess(name: str, buckets: dict[str, list[Record]], total: int,
            ratio: float, alpha: float, min_share: float) -> Attribute:
    groups = []
    for cat, recs in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        k, n = sum(r.selected for r in recs), len(recs)
        qualified = [r for r in recs if r.label is True]
        unqualified = [r for r in recs if r.label is False]
        groups.append(Group(
            category=cat, n=n, selected=k, share=n / total, rate=k / n, ci=wilson_interval(k, n),
            tpr=_rate(sum(r.selected for r in qualified), len(qualified)),
            fpr=_rate(sum(r.selected for r in unqualified), len(unqualified)),
        ))

    # Tiny and unknown groups are reported but not scored, as LL144 permits.
    eligible = [g for g in groups if g.category != UNKNOWN and UNKNOWN not in g.category and g.share >= min_share]
    for g in groups:
        if g not in eligible:
            g.status = EXCLUDED

    ref = max(eligible, key=lambda g: g.rate, default=None)
    for g in eligible:
        g.impact_ratio = g.rate / ref.rate if ref.rate else 1.0
        if g is ref:
            g.status, g.p_value = REFERENCE, 1.0
            continue
        g.p_value = two_proportion_p(g.selected, g.n, ref.selected, ref.n)
        low, significant = g.impact_ratio < ratio, g.p_value < alpha
        g.status = ADVERSE if low and significant else REVIEW if low or significant else OK

    tprs = [g.tpr for g in eligible if g.tpr is not None]
    gap = max(tprs) - min(tprs) if len(tprs) > 1 else None
    return Attribute(name, groups, ref.category if ref else None, gap)


def audit(records: list[Record], attrs: list[str], *, ratio: float = 0.8, alpha: float = 0.05,
          min_share: float = 0.02, intersect: bool = True) -> Audit:
    """Audit ``records`` across each attribute and (optionally) their pairwise intersections.

    A group is flagged **adverse** only when its impact ratio is below ``ratio``
    (the EEOC four-fifths rule) *and* the gap is statistically significant at
    ``alpha``. Either signal alone is flagged **review** — worth a human look,
    but not yet evidence.
    """
    if not records:
        raise ValueError("no records to audit")
    total = len(records)
    keys = [(a,) for a in attrs] + (list(combinations(attrs, 2)) if intersect else [])

    results = []
    for key in keys:
        buckets: dict[str, list[Record]] = defaultdict(list)
        for r in records:
            buckets[" · ".join(r.groups[a] for a in key)].append(r)
        results.append(_assess(" × ".join(key), buckets, total, ratio, alpha, min_share))

    return Audit(
        n=total,
        selected=sum(r.selected for r in records),
        attributes=results,
        settings={"ratio": ratio, "alpha": alpha, "min_share": min_share, "intersect": intersect,
                  "has_labels": any(r.label is not None for r in records)},
    )
