"""Core fairness metrics and plain-language findings.

The audit follows the method regulators already use:

* **Selection rate** per group, with a 95% Wilson interval.
* **Impact ratio** = group rate / highest group rate. The US EEOC
  "four-fifths rule" and NYC Local Law 144 treat a ratio below 0.80 as
  evidence of adverse impact.
* A **two-proportion z-test** against the reference group, so a low ratio
  on a handful of people is reported as "uncertain", not "biased".
* When ground truth is available, **true/false positive rates** -- did
  equally qualified people get equal treatment? ("equal opportunity").
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .data import Record
from .stats import ratio, two_proportion_p, wilson

FAIL, WARN, INFO = "fail", "warn", "info"


@dataclass
class GroupStats:
    name: str
    n: int
    selected: int
    rate: float
    ci: tuple[float, float]
    impact_ratio: float | None = None
    p_value: float | None = None
    tpr: float | None = None   # P(selected | qualified)
    fpr: float | None = None   # P(selected | not qualified)
    ppv: float | None = None   # P(qualified | selected)


@dataclass
class Finding:
    level: str
    group: str
    message: str


@dataclass
class Audit:
    attribute: str
    groups: list[GroupStats]
    reference: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def status(self) -> str:
        levels = {f.level for f in self.findings}
        return FAIL if FAIL in levels else WARN if WARN in levels else "pass"


@dataclass(frozen=True)
class Policy:
    threshold: float = 0.80   # four-fifths rule
    alpha: float = 0.05       # significance level
    min_n: int = 30           # below this a group is "small sample"
    max_gap: float = 0.10     # tolerated TPR/FPR gap (absolute)


def _rates(rs: list[Record]) -> tuple[float | None, float | None, float | None]:
    pos = [r for r in rs if r.label]
    neg = [r for r in rs if r.label is False]
    sel = [r for r in rs if r.decision]
    tpr = ratio(sum(r.decision for r in pos), len(pos))
    fpr = ratio(sum(r.decision for r in neg), len(neg))
    ppv = ratio(sum(bool(r.label) for r in sel), len(sel))
    return tpr, fpr, ppv


def audit(
    records: Iterable[Record],
    attribute: str,
    key: Callable[[Record], str],
    policy: Policy = Policy(),
) -> Audit:
    """Audit one (possibly intersectional) attribute."""
    buckets: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        buckets[key(r)].append(r)

    has_label = any(r.label is not None for rs in buckets.values() for r in rs)
    stats = []
    for name, rs in buckets.items():
        k, n = sum(r.decision for r in rs), len(rs)
        g = GroupStats(name, n, k, k / n, wilson(k, n))
        if has_label:
            g.tpr, g.fpr, g.ppv = _rates(rs)
        stats.append(g)

    # Reference = most-favoured group among those large enough to trust,
    # so one lucky three-person group can't set the bar for everyone.
    trusted = [g for g in stats if g.n >= policy.min_n] or stats
    ref = max(trusted, key=lambda g: g.rate)
    for g in stats:
        g.impact_ratio = ratio(g.rate, ref.rate)
        if g is not ref:
            g.p_value = two_proportion_p(g.selected, g.n, ref.selected, ref.n)

    stats.sort(key=lambda g: (-g.rate, g.name))
    result = Audit(attribute, stats, ref.name)
    result.findings = list(_findings(stats, ref, policy))
    return result


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _p(x: float | None) -> str:
    return "p=n/a" if x is None else "p<0.001" if x < 0.001 else f"p={x:.3f}"


def _findings(stats: list[GroupStats], ref: GroupStats, p: Policy):
    for g in stats:
        small = g.n < p.min_n
        if small:
            yield Finding(INFO, g.name,
                          f"{g.name}: only {g.n} records, too few for reliable conclusions.")
        if g is ref:
            continue

        ir = g.impact_ratio
        if ir is not None and ir < p.threshold:
            significant = g.p_value is not None and g.p_value < p.alpha
            gist = (f"{g.name} is selected at {_pct(ir)} of {ref.name}'s rate "
                    f"({_pct(g.rate)} vs {_pct(ref.rate)}, {_p(g.p_value)})")
            if significant and not small:
                yield Finding(FAIL, g.name, f"Adverse impact: {gist}.")
            else:
                yield Finding(WARN, g.name,
                              f"Below the four-fifths line but inconclusive: {gist}. "
                              f"Collect more data before drawing conclusions.")

        if g.tpr is not None and ref.tpr is not None and ref.tpr - g.tpr > p.max_gap:
            yield Finding(WARN, g.name,
                          f"Equal-opportunity gap: qualified people in the {g.name} group are "
                          f"selected {_pct(g.tpr)} of the time vs {_pct(ref.tpr)} in "
                          f"{ref.name}.")
        if g.fpr is not None and ref.fpr is not None and abs(g.fpr - ref.fpr) > p.max_gap:
            yield Finding(WARN, g.name,
                          f"False-positive gap: unqualified people in the {g.name} group are "
                          f"selected {_pct(g.fpr)} of the time vs {_pct(ref.fpr)} in "
                          f"{ref.name}.")


def run(records: list[Record], attributes: list[str], policy: Policy = Policy()) -> list[Audit]:
    """Audit each attribute on its own, plus their intersection if >1."""
    audits = [
        audit(records, a, (lambda r, i=i: r.groups[i]), policy)
        for i, a in enumerate(attributes)
    ]
    if len(attributes) > 1:
        audits.append(audit(records, " × ".join(attributes),
                            lambda r: " · ".join(r.groups), policy))
    return audits
