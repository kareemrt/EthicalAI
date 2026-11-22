"""Core audit: per-group rates, impact ratios, significance and error-rate gaps."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, asdict

from .data import UNKNOWN, Record
from .stats import ratio, two_proportion_p, wilson

OK, WARN, FAIL, EXCLUDED = "ok", "warn", "fail", "excluded"
SEVERITY = {EXCLUDED: 0, OK: 1, WARN: 2, FAIL: 3}


@dataclass
class Config:
    ratio: float = 0.8        # four-fifths rule
    alpha: float = 0.05       # significance level
    min_share: float = 0.02   # groups below this share of the data are excluded (LL144 allows < 2%)
    intersections: bool = True


@dataclass
class Group:
    name: str
    n: int
    selected: int
    share: float
    rate: float
    ci: tuple[float, float]
    impact_ratio: float | None = None
    p_value: float | None = None
    tpr: float | None = None   # P(selected | qualified)  — equal opportunity
    fpr: float | None = None   # P(selected | unqualified)
    status: str = OK


@dataclass
class AttributeAudit:
    attribute: str
    reference: str | None
    groups: list[Group]
    parity_gap: float | None = None   # max - min selection rate (demographic parity difference)
    tpr_gap: float | None = None      # equal opportunity difference
    fpr_gap: float | None = None      # with tpr_gap: equalized odds

    @property
    def status(self) -> str:
        return max((g.status for g in self.groups), key=SEVERITY.get, default=OK)


@dataclass
class Report:
    source: str
    outcome: str
    n: int
    selected: int
    has_labels: bool
    config: Config
    audits: list[AttributeAudit] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.selected / self.n if self.n else 0.0

    @property
    def status(self) -> str:
        return max((a.status for a in self.audits), key=SEVERITY.get, default=OK)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rate"] = self.rate
        d["status"] = self.status
        for a, src in zip(d["audits"], self.audits):
            a["status"] = src.status
        return d


def _gap(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return max(vals) - min(vals) if len(vals) > 1 else None


def audit_attribute(records: list[Record], attribute: str, keys: list[str], cfg: Config) -> AttributeAudit:
    """Audit one attribute (or an intersection of several, given by `keys`)."""
    buckets: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        values = [r.groups[k] for k in keys]
        name = UNKNOWN if UNKNOWN in values else " × ".join(values)
        buckets[name].append(r)

    total = len(records)
    groups: list[Group] = []
    for name, rs in buckets.items():
        n, k = len(rs), sum(r.pred for r in rs)
        g = Group(name=name, n=n, selected=k, share=n / total, rate=k / n, ci=wilson(k, n))
        qualified = [r.pred for r in rs if r.label == 1]
        unqualified = [r.pred for r in rs if r.label == 0]
        g.tpr = sum(qualified) / len(qualified) if qualified else None
        g.fpr = sum(unqualified) / len(unqualified) if unqualified else None
        if name == UNKNOWN or g.share < cfg.min_share:
            g.status = EXCLUDED
        groups.append(g)

    included = [g for g in groups if g.status != EXCLUDED]
    ref = max(included, key=lambda g: g.rate, default=None)
    for g in included:
        g.impact_ratio = ratio(g.rate, ref.rate)
        g.p_value = two_proportion_p(g.selected, g.n, ref.selected, ref.n)
        if g.impact_ratio is not None and g.impact_ratio < cfg.ratio:
            # Below four-fifths: a hard fail only when the gap is also statistically
            # significant; otherwise it needs human review (small samples are noisy).
            g.status = FAIL if g.p_value < cfg.alpha else WARN

    groups.sort(key=lambda g: (g.status == EXCLUDED, -g.rate))
    return AttributeAudit(
        attribute=attribute,
        reference=ref.name if ref else None,
        groups=groups,
        parity_gap=_gap([g.rate for g in included]),
        tpr_gap=_gap([g.tpr for g in included]),
        fpr_gap=_gap([g.fpr for g in included]),
    )


def run(records: list[Record], attributes: list[str], outcome: str, source: str, cfg: Config | None = None) -> Report:
    """Audit every attribute, plus their full intersection when there are several."""
    cfg = cfg or Config()
    report = Report(
        source=source,
        outcome=outcome,
        n=len(records),
        selected=sum(r.pred for r in records),
        has_labels=any(r.label is not None for r in records),
        config=cfg,
    )
    for a in attributes:
        report.audits.append(audit_attribute(records, a, [a], cfg))
    if cfg.intersections and len(attributes) > 1:
        report.audits.append(audit_attribute(records, " × ".join(attributes), attributes, cfg))
    return report
