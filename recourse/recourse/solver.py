"""Find the least-effort changes that flip a decision.

For a linear score  s = b + Σ wᵢ·xᵢ  and a threshold t, flipping a decision
means closing the gap  g = t − s  using only actionable features, at minimum
total effort  Σ costᵢ·|Δᵢ|.  That is a fractional knapsack: spend effort on
the feature with the best score-per-effort ratio  |wᵢ| / costᵢ  until it hits
its limit, then the next one.  Greedy is exactly optimal for continuous
features; with `step` rounding it is optimal up to one step per feature.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

from .model import Feature, Model

EPS = 1e-9


@dataclass(frozen=True)
class Change:
    feature: Feature
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before

    @property
    def cost(self) -> float:
        return self.feature.cost * abs(self.delta)


@dataclass
class Plan:
    changes: list[Change] = field(default_factory=list)
    shortfall: float = 0.0  # score still missing after the plan (0 = it works)

    @property
    def feasible(self) -> bool:
        return self.shortfall <= EPS

    @property
    def cost(self) -> float:
        return sum(c.cost for c in self.changes)


def gap(model: Model, x: Mapping[str, float]) -> float:
    """Score still needed to reach the threshold (≤ 0 means already approved)."""
    return model.threshold - model.score(x)


def _snap(amount: float, step: float, room: float) -> float:
    """Round a change up to the feature's step, without exceeding its room."""
    if step <= 0:
        return amount
    up = math.ceil(amount / step - EPS) * step
    return up if up <= room + EPS else math.floor(room / step + EPS) * step


def _levers(model: Model, x: Mapping[str, float]):
    """Every way to raise the score: (efficiency, feature, sign, room)."""
    for f in model.mutable:
        sign = 1 if f.weight > 0 else -1
        room = f.room(x[f.name], sign)
        if room > EPS:
            yield abs(f.weight) / f.cost, f, sign, room


def _move(f: Feature, x: Mapping[str, float], sign: int, amount: float) -> Change:
    return Change(f, x[f.name], round(x[f.name] + sign * amount, 6))


def best_plan(model: Model, x: Mapping[str, float]) -> Plan:
    """Cheapest combination of changes that flips the decision.

    If no combination is enough, returns the furthest-reaching plan with a
    positive `shortfall` – the person has no recourse under this policy.
    """
    need = gap(model, x)
    if need <= 0:
        return Plan()
    plan = Plan()
    for _, f, sign, room in sorted(_levers(model, x), key=lambda t: -t[0]):
        if need <= EPS:
            break
        amount = _snap(min(room, need / abs(f.weight)), f.step, room)
        if amount > EPS:
            plan.changes.append(_move(f, x, sign, amount))
            need -= abs(f.weight) * amount
    plan.shortfall = max(0.0, need)
    return plan


def single_changes(model: Model, x: Mapping[str, float]) -> list[Plan]:
    """Every *one-feature* change that would be enough on its own, cheapest first."""
    need = gap(model, x)
    if need <= 0:
        return []
    plans = []
    for _, f, sign, room in _levers(model, x):
        amount = _snap(need / abs(f.weight), f.step, room)
        if abs(f.weight) * amount >= need - EPS:
            plans.append(Plan([_move(f, x, sign, amount)]))
    return sorted(plans, key=lambda p: p.cost)


def locked_penalty(model: Model, x: Mapping[str, float]) -> list[tuple[Feature, float]]:
    """Score lost to features the person cannot change, worst first."""
    out = [(f, f.weight * (x[f.name] - f.reference)) for f in model.fixed]
    return sorted([fc for fc in out if fc[1] < 0], key=lambda fc: fc[1])
