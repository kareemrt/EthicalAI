"""Pure functions: calibration error, selective prediction, recalibration."""

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .data import Prediction

EPS = 1e-6


# ---------------------------------------------------------------- calibration
@dataclass
class Bin:
    lo: float
    hi: float
    count: int
    mean_conf: float
    accuracy: float


def reliability_bins(preds: Sequence[Prediction], n_bins: int = 10) -> List[Bin]:
    """Equal-width confidence bins with the observed accuracy in each."""
    sums = [[0, 0.0, 0] for _ in range(n_bins)]  # count, sum_conf, hits
    for p in preds:
        i = min(int(p.confidence * n_bins), n_bins - 1)
        sums[i][0] += 1
        sums[i][1] += p.confidence
        sums[i][2] += p.correct
    bins = []
    for i, (n, c, h) in enumerate(sums):
        if n:
            bins.append(Bin(i / n_bins, (i + 1) / n_bins, n, c / n, h / n))
    return bins


def ece(bins: Sequence[Bin]) -> float:
    """Expected Calibration Error: count-weighted |confidence - accuracy|."""
    total = sum(b.count for b in bins)
    return sum(b.count * abs(b.mean_conf - b.accuracy) for b in bins) / total if total else 0.0


def mce(bins: Sequence[Bin]) -> float:
    """Maximum Calibration Error: the worst bin."""
    return max((abs(b.mean_conf - b.accuracy) for b in bins), default=0.0)


def brier(preds: Sequence[Prediction]) -> float:
    return sum((p.confidence - p.correct) ** 2 for p in preds) / len(preds)


def accuracy(preds: Sequence[Prediction]) -> float:
    return sum(p.correct for p in preds) / len(preds) if preds else float("nan")


def mean_conf(preds: Sequence[Prediction]) -> float:
    return sum(p.confidence for p in preds) / len(preds) if preds else float("nan")


# ------------------------------------------------------- selective prediction
def wilson_lower(hits: int, n: int, z: float = 1.96) -> float:
    """Lower end of the Wilson score interval: a cautious accuracy estimate."""
    if n == 0:
        return 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


@dataclass
class CurvePoint:
    threshold: float  # automate when confidence >= threshold
    coverage: float   # share of cases the AI decides alone
    accuracy: float   # accuracy on those cases
    lower: float      # Wilson lower bound on that accuracy


def coverage_curve(preds: Sequence[Prediction]) -> List[CurvePoint]:
    """Accuracy of the automated cases at every possible confidence cut-off."""
    ranked = sorted(preds, key=lambda p: -p.confidence)
    n, hits, points = len(ranked), 0, []
    for k, p in enumerate(ranked, start=1):
        hits += p.correct
        # only emit a point once all ties at this confidence are included
        if k == n or ranked[k].confidence != p.confidence:
            points.append(CurvePoint(p.confidence, k / n, hits / k, wilson_lower(hits, k)))
    return points


def pick_threshold(curve: Sequence[CurvePoint], target: float) -> Optional[CurvePoint]:
    """Widest coverage whose *lower-bound* accuracy still meets the target.

    Using the Wilson lower bound (not the raw accuracy) means a small, lucky
    slice of confident cases can't talk us into automating too much.
    Returns None when no slice of cases is reliably good enough.
    """
    passing = [pt for pt in curve if pt.lower >= target]
    return max(passing, key=lambda pt: pt.coverage) if passing else None


# -------------------------------------------------------------- recalibration
def _logit(c: float) -> float:
    c = min(max(c, EPS), 1 - EPS)
    return math.log(c / (1 - c))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    e = math.exp(z)
    return e / (1 + e)


def _log_loss(xs, ys, a: float, b: float) -> float:
    loss = 0.0
    for x, y in zip(xs, ys):
        q = min(max(_sigmoid(a * x + b), EPS), 1 - EPS)
        loss -= y * math.log(q) + (1 - y) * math.log(1 - q)
    return loss


def fit_platt(preds: Sequence[Prediction], iters: int = 50) -> Tuple[float, float]:
    """Fit c' = sigmoid(a * logit(c) + b) by damped Newton's method on log-loss.

    Two parameters, convex objective, converges in a handful of steps.
    a < 1 means the model was overconfident; a > 1 underconfident.
    """
    xs = [_logit(p.confidence) for p in preds]
    ys = [float(p.correct) for p in preds]
    a, b = 1.0, 0.0
    loss = _log_loss(xs, ys, a, b)
    for _ in range(iters):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in zip(xs, ys):
            q = _sigmoid(a * x + b)
            r, w = q - y, q * (1 - q)
            ga, gb = ga + r * x, gb + r
            haa, hab, hbb = haa + w * x * x, hab + w * x, hbb + w
        haa, hbb = haa + 1e-3, hbb + 1e-3  # small ridge keeps the Hessian invertible
        det = haa * hbb - hab * hab
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        step = 1.0
        while step > 1e-4:  # backtrack until the loss actually goes down
            new = _log_loss(xs, ys, a - step * da, b - step * db)
            if new <= loss:
                break
            step /= 2
        else:
            break
        a, b = a - step * da, b - step * db
        if loss - new < 1e-10:
            break
        loss = new
    return a, b


def apply_platt(preds: Sequence[Prediction], a: float, b: float) -> List[Prediction]:
    return [Prediction(_sigmoid(a * _logit(p.confidence) + b), p.correct, p.group) for p in preds]
