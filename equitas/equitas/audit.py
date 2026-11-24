"""Orchestrates a full audit: data in, structured result out."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import data
from .metrics import GroupStat, audit_groups, worst_status


@dataclass
class Dimension:
    name: str  # e.g. "sex", or "sex × race" for intersections
    unknown: int  # rows whose category was missing / undisclosed
    groups: list[GroupStat]

    @property
    def status(self) -> str:
        return worst_status(self.groups)


@dataclass
class Audit:
    source: str
    outcome: str
    mode: str  # "selection" or "scoring"
    population: int
    overall_rate: float
    threshold: float
    min_share: float
    alpha: float
    median_cut: float | None = None
    dimensions: list[Dimension] = field(default_factory=list)

    @property
    def status(self) -> str:
        return worst_status(g for d in self.dimensions for g in d.groups)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status
        for dim, src in zip(d["dimensions"], self.dimensions):
            dim["status"] = src.status
        return d


def run_audit(
    path: str | Path,
    outcome: str,
    groups: list[str],
    *,
    score: bool = False,
    intersect: bool = True,
    threshold: float = 0.8,
    min_share: float = 0.02,
    alpha: float = 0.05,
) -> Audit:
    rows = data.load_rows(path)
    data.require_columns(rows, [outcome, *groups])

    if score:
        outcomes, cut = data.score_outcomes(rows, outcome)
    else:
        outcomes, cut = data.binary_outcomes(rows, outcome), None

    audit = Audit(
        source=Path(path).name,
        outcome=outcome,
        mode="scoring" if score else "selection",
        population=len(rows),
        overall_rate=sum(outcomes) / len(outcomes),
        threshold=threshold,
        min_share=min_share,
        alpha=alpha,
        median_cut=cut,
    )

    specs = [(g, lambda r, g=g: data.group_value(r, g)) for g in groups]
    if intersect and len(groups) > 1:
        specs.append((" × ".join(groups), lambda r: data.intersect_value(r, groups)))

    for name, key in specs:
        keyed = [(key(r), o) for r, o in zip(rows, outcomes)]
        known = [(k, o) for k, o in keyed if k is not None]
        stats = audit_groups(known, threshold, min_share, alpha)
        audit.dimensions.append(Dimension(name, len(keyed) - len(known), stats))
    return audit
