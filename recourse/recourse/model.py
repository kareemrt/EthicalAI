"""Linear scoring models, plus the rules for what a person can actually change.

A model file describes two things side by side:

* the *scorecard*  – weights, intercept and decision threshold, and
* the *action policy* – for every feature, whether a person can change it,
  in which direction, how far, and how much effort each unit costs.

Keeping both in one small JSON file means a reviewer can read, in one place,
what the model rewards and what it is reasonable to ask of people.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Mapping

DIRECTIONS = ("increase", "decrease", "both")


@dataclass(frozen=True)
class Feature:
    name: str
    weight: float
    label: str = ""
    unit: str = ""
    reference: float = 0.0        # "typical" value used to explain reasons
    mutable: bool = False         # can the person change this at all?
    direction: str = "both"       # increase | decrease | both
    min: float = -math.inf        # hard bounds on the value
    max: float = math.inf
    max_change: float = math.inf  # realistic change within the horizon
    step: float = 0.0             # smallest meaningful change (0 = continuous)
    cost: float = 1.0             # effort points per unit of change
    note: str = ""                # why it is (im)mutable, shown to readers

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            raise ValueError(f"{self.name}: direction must be one of {DIRECTIONS}")
        if self.mutable and self.cost <= 0:
            raise ValueError(f"{self.name}: cost must be positive for mutable features")
        if self.step < 0 or self.max_change < 0:
            raise ValueError(f"{self.name}: step and max_change must be non-negative")

    @property
    def title(self) -> str:
        return self.label or self.name

    def room(self, value: float, sign: int) -> float:
        """How far the feature may move from `value` in direction `sign` (+1 / -1)."""
        if not self.mutable:
            return 0.0
        if (sign > 0 and self.direction == "decrease") or (sign < 0 and self.direction == "increase"):
            return 0.0
        limit = self.max - value if sign > 0 else value - self.min
        return max(0.0, min(limit, self.max_change))


@dataclass
class Model:
    name: str
    features: dict[str, Feature]
    intercept: float = 0.0
    threshold: float = 0.0
    positive: str = "approved"
    negative: str = "declined"
    notes: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- loading
    @classmethod
    def from_dict(cls, data: Mapping) -> "Model":
        known = {f.name for f in fields(Feature)}
        feats = {}
        for name, spec in data["features"].items():
            unknown = set(spec) - known
            if unknown:
                raise ValueError(f"{name}: unknown keys {sorted(unknown)}")
            feats[name] = Feature(name=name, **spec)
        outcome = data.get("outcome", {})
        return cls(
            name=data.get("name", "model"),
            features=feats,
            intercept=float(data.get("intercept", 0.0)),
            threshold=float(data.get("threshold", 0.0)),
            positive=outcome.get("positive", "approved"),
            negative=outcome.get("negative", "declined"),
            notes=list(data.get("notes", [])),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Model":
        return cls.from_dict(json.loads(Path(path).read_text()))

    # -------------------------------------------------------------- inference
    def vector(self, record: Mapping) -> dict[str, float]:
        """Pull the model's features out of a record, as floats."""
        missing = [n for n in self.features if record.get(n) in (None, "")]
        if missing:
            raise KeyError(f"record is missing feature(s): {', '.join(missing)}")
        return {n: float(record[n]) for n in self.features}

    def score(self, x: Mapping[str, float]) -> float:
        return self.intercept + sum(f.weight * x[n] for n, f in self.features.items())

    def approves(self, x: Mapping[str, float]) -> bool:
        return self.score(x) >= self.threshold

    def contributions(self, x: Mapping[str, float]) -> dict[str, float]:
        """Each feature's push on the score relative to its reference value."""
        return {n: f.weight * (x[n] - f.reference) for n, f in self.features.items()}

    def reasons(self, x: Mapping[str, float], k: int = 4) -> list[tuple[Feature, float]]:
        """Top-k features pulling the score down (adverse-action style reasons)."""
        neg = [(self.features[n], c) for n, c in self.contributions(x).items() if c < 0]
        return sorted(neg, key=lambda fc: fc[1])[:k]

    # ---------------------------------------------------------------- policy
    @property
    def mutable(self) -> list[Feature]:
        return [f for f in self.features.values() if f.mutable and f.weight]

    @property
    def fixed(self) -> list[Feature]:
        return [f for f in self.features.values() if not f.mutable and f.weight]
