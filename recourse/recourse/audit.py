"""Audit a model for *recourse fairness* across a population.

Approval-rate audits ask "who gets declined?". A recourse audit asks the
next question: "once declined, how hard is it to get approved, and who has no
realistic path at all?" Two groups can have equal approval rates while one of
them faces twice the effort to recover from a 'no'.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Mapping

from .model import Model
from .solver import Plan, best_plan, locked_penalty

# Mirrors the "four-fifths rule": a burden 25 % higher than the
# least-burdened group (1 / 0.8) is worth a human look.
BURDEN_RATIO_FLAG = 1.25
# More than 1 in 20 declined people with no achievable path is worth a look.
NO_RECOURSE_FLAG = 0.05


@dataclass
class Case:
    id: str
    group: str
    approved: bool
    plan: Plan
    locked: float  # score lost to immutable features (≤ 0)


@dataclass
class GroupStats:
    group: str
    n: int
    declined: int
    no_recourse: int
    costs: list[float] = field(repr=False)
    locked: list[float] = field(repr=False)

    @property
    def decline_rate(self) -> float:
        return self.declined / self.n if self.n else 0.0

    @property
    def no_recourse_rate(self) -> float:
        """Share of *declined* people who cannot get approved under the policy."""
        return self.no_recourse / self.declined if self.declined else 0.0

    @property
    def median_cost(self) -> float:
        return median(self.costs) if self.costs else 0.0

    @property
    def mean_locked(self) -> float:
        return mean(self.locked) if self.locked else 0.0


@dataclass
class Finding:
    severity: str  # "flag" | "ok" | "info"
    text: str


@dataclass
class Report:
    model: Model
    group_by: str
    cases: list[Case]
    groups: list[GroupStats]
    findings: list[Finding]


def read_csv(path: str | Path) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _ratio(values: list[float]) -> float:
    lo, hi = min(values), max(values)
    return hi / lo if lo > 0 else (float("inf") if hi > 0 else 1.0)


def audit(model: Model, records: Iterable[Mapping], group_by: str = "group") -> Report:
    cases = []
    for i, rec in enumerate(records, 1):
        x = model.vector(rec)
        approved = model.approves(x)
        cases.append(Case(
            id=str(rec.get("id") or i),
            group=str(rec.get(group_by) or "all"),
            approved=approved,
            plan=best_plan(model, x),
            locked=0.0 if approved else sum(p for _, p in locked_penalty(model, x)),
        ))

    groups = []
    for g in sorted({c.group for c in cases}):
        members = [c for c in cases if c.group == g]
        declined = [c for c in members if not c.approved]
        groups.append(GroupStats(
            group=g,
            n=len(members),
            declined=len(declined),
            no_recourse=sum(not c.plan.feasible for c in declined),
            costs=[c.plan.cost for c in declined if c.plan.feasible],
            locked=[c.locked for c in declined],
        ))
    return Report(model, group_by, cases, groups, _findings(model, groups))


def _findings(model: Model, groups: list[GroupStats]) -> list[Finding]:
    out: list[Finding] = []
    total_declined = sum(g.declined for g in groups)
    total_stuck = sum(g.no_recourse for g in groups)
    if total_declined:
        share = total_stuck / total_declined
        sev = "flag" if share >= NO_RECOURSE_FLAG else "ok"
        out.append(Finding(sev, f"{total_stuck} of {total_declined} declined people "
                                f"({share:.0%}) have no achievable path to approval."))

    active = [g for g in groups if g.costs]
    if len(active) >= 2:
        r = _ratio([g.median_cost for g in active])
        worst = max(active, key=lambda g: g.median_cost)
        best = min(active, key=lambda g: g.median_cost)
        sev = "flag" if r >= BURDEN_RATIO_FLAG else "ok"
        out.append(Finding(sev, f"Recourse burden ratio {r:.2f}: '{worst.group}' needs a median "
                                f"{worst.median_cost:.2f} effort points vs {best.median_cost:.2f} "
                                f"for '{best.group}'."))

    with_declines = [g for g in groups if g.declined]
    if len(with_declines) >= 2:
        rates = [g.no_recourse_rate for g in with_declines]
        if max(rates) > 0:
            worst = max(with_declines, key=lambda g: g.no_recourse_rate)
            best = min(with_declines, key=lambda g: g.no_recourse_rate)
            r = _ratio(rates)
            sev = "flag" if r >= BURDEN_RATIO_FLAG and worst.no_recourse >= 3 else "ok"
            ratio = "∞" if r == float("inf") else f"{r:.2f}"
            out.append(Finding(sev, f"No-recourse ratio {ratio}: {worst.no_recourse_rate:.0%} of declined "
                                    f"'{worst.group}' are stuck vs {best.no_recourse_rate:.0%} of '{best.group}'."))

    for f in model.fixed:
        if f.note:
            out.append(Finding("info", f"Fixed feature '{f.title}' carries weight {f.weight:+g} — {f.note}."))
    return out
