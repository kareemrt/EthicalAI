"""A glass-box classifier: logistic regression over binary red-flag signals.

Why this model?  Every weight maps to one named signal, so a verdict is just
"bias + the weights of the flags that fired" - something a person can audit
by hand. No black box, no network calls, no data leaves the device.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from .signals import BY_ID, SIGNALS, Hit, scan

WEIGHTS_PATH = Path(__file__).with_name("weights.json")
FEATURES = [s.id for s in SIGNALS]


def featurize(text: str) -> tuple[list[float], dict[str, list[Hit]]]:
    hits = scan(text)
    return [1.0 if f in hits else 0.0 for f in FEATURES], hits


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


@dataclass
class Model:
    weights: dict[str, float] = field(default_factory=lambda: dict.fromkeys(FEATURES, 0.0))
    bias: float = 0.0

    # ── training ────────────────────────────────────────────────────────────
    @classmethod
    def train(cls, texts: list[str], labels: list[int], epochs: int = 1500, lr: float = 0.5,
              l2: float = 0.005, seed: int = 7) -> "Model":
        """Full-batch gradient descent with L2 regularisation. Deterministic."""
        X = [featurize(t)[0] for t in texts]
        w, b, n = [0.0] * len(FEATURES), 0.0, len(X)
        rng = random.Random(seed)
        w = [rng.uniform(-0.01, 0.01) for _ in w]
        for _ in range(epochs):
            gw, gb = [l2 * wi for wi in w], 0.0
            for x, y in zip(X, labels):
                err = _sigmoid(b + sum(wi * xi for wi, xi in zip(w, x))) - y
                gb += err / n
                for i, xi in enumerate(x):
                    if xi:
                        gw[i] += err * xi / n
            w = [wi - lr * g for wi, g in zip(w, gw)]
            b -= lr * gb
        return cls(dict(zip(FEATURES, w)), b)

    # ── persistence ─────────────────────────────────────────────────────────
    def save(self, path: Path = WEIGHTS_PATH) -> None:
        data = {"bias": round(self.bias, 4), "weights": {k: round(v, 4) for k, v in self.weights.items()}}
        path.write_text(json.dumps(data, indent=2) + "\n")

    @classmethod
    def load(cls, path: Path = WEIGHTS_PATH) -> "Model":
        data = json.loads(Path(path).read_text())
        return cls({f: data["weights"].get(f, 0.0) for f in FEATURES}, data["bias"])

    # ── inference ───────────────────────────────────────────────────────────
    def score(self, text: str) -> "Report":
        x, hits = featurize(text)
        z = self.bias + sum(self.weights[f] * xi for f, xi in zip(FEATURES, x))
        flags = sorted(
            (Flag(BY_ID[f], self.weights[f], hits[f]) for f in hits),
            key=lambda fl: fl.weight, reverse=True,
        )
        return Report(text, _sigmoid(z), flags)


@dataclass
class Flag:
    signal: object
    weight: float
    hits: list[Hit]

    def to_dict(self) -> dict:
        s = self.signal
        return {"id": s.id, "label": s.label, "why": s.why, "advice": s.advice, "weight": round(self.weight, 3),
                "evidence": [{"start": h.start, "end": h.end, "text": h.text} for h in self.hits]}


VERDICTS = ((0.80, "danger", "Very likely a scam"), (0.45, "warn", "Be careful"), (0.0, "ok", "No strong red flags"))


@dataclass
class Report:
    text: str
    risk: float
    flags: list[Flag]

    @property
    def level(self) -> str:
        return next(lvl for cut, lvl, _ in VERDICTS if self.risk >= cut)

    @property
    def verdict(self) -> str:
        return next(v for cut, _, v in VERDICTS if self.risk >= cut)

    def to_dict(self) -> dict:
        return {"risk": round(self.risk, 3), "level": self.level, "verdict": self.verdict,
                "flags": [f.to_dict() for f in self.flags]}
