"""Turn a list of predictions into one Audit: numbers, operating point, findings."""

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

from . import metrics as m
from .data import Prediction


@dataclass
class GroupStats:
    group: str
    n: int
    accuracy: float
    mean_conf: float
    ece: float
    deferred: float = 0.0          # share of this group's cases sent to a human
    auto_accuracy: float = float("nan")  # accuracy on the cases the AI kept
    auto_n: int = 0


@dataclass
class Audit:
    n: int
    target: float
    accuracy: float
    mean_conf: float
    ece: float
    mce: float
    brier: float
    bins: List[m.Bin]
    curve: List[m.CurvePoint]
    operating_point: Optional[m.CurvePoint]
    platt: Dict[str, float]          # a, b and held-out ECE before/after
    recal_bins: List[m.Bin]
    groups: List[GroupStats]
    findings: List[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["curve"] = d["curve"][:: max(1, len(self.curve) // 200)]  # keep JSON small
        return d


def _group_stats(preds: Sequence[Prediction], threshold: Optional[float]) -> List[GroupStats]:
    by: Dict[str, List[Prediction]] = {}
    for p in preds:
        by.setdefault(p.group, []).append(p)
    out = []
    for g, ps in sorted(by.items()):
        s = GroupStats(g, len(ps), m.accuracy(ps), m.mean_conf(ps), m.ece(m.reliability_bins(ps)))
        if threshold is not None:
            kept = [p for p in ps if p.confidence >= threshold]
            s.deferred = 1 - len(kept) / len(ps)
            s.auto_n = len(kept)
            s.auto_accuracy = m.accuracy(kept)
        out.append(s)
    return out


def _recalibrate(preds: Sequence[Prediction]) -> tuple:
    """Fit Platt scaling on even rows, score it on odd rows (honest hold-out)."""
    train, test = preds[0::2], preds[1::2]
    a, b = m.fit_platt(train)
    fixed = m.apply_platt(test, a, b)
    before = m.ece(m.reliability_bins(test))
    after_bins = m.reliability_bins(fixed)
    return {"a": a, "b": b, "ece_before": before, "ece_after": m.ece(after_bins)}, after_bins


def run_audit(preds: Sequence[Prediction], target: float = 0.95,
              max_ece: float = 0.05, max_gap: float = 0.03) -> Audit:
    """Run every check. ``target`` is the accuracy the AI must hit on the cases
    it decides alone; ``max_ece`` and ``max_gap`` set the pass/fail gates."""
    preds = list(preds)
    bins = m.reliability_bins(preds)
    curve = m.coverage_curve(preds)
    op = m.pick_threshold(curve, target)
    platt, recal_bins = _recalibrate(preds)
    groups = _group_stats(preds, op.threshold if op else None)

    a = Audit(
        n=len(preds), target=target, accuracy=m.accuracy(preds), mean_conf=m.mean_conf(preds),
        ece=m.ece(bins), mce=m.mce(bins), brier=m.brier(preds), bins=bins, curve=curve,
        operating_point=op, platt=platt, recal_bins=recal_bins, groups=groups,
    )
    _findings(a, max_ece, max_gap)
    return a


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _findings(a: Audit, max_ece: float, max_gap: float) -> None:
    f = a.findings
    gap = a.mean_conf - a.accuracy
    if a.ece > max_ece:
        a.passed = False
        mood = "overconfident" if gap > 0 else "underconfident"
        f.append(f"FAIL  Miscalibrated: ECE {_pct(a.ece)} > {_pct(max_ece)}. "
                 f"The model is {mood} (says {_pct(a.mean_conf)}, is right {_pct(a.accuracy)}).")
    else:
        f.append(f"PASS  Calibrated: ECE {_pct(a.ece)} <= {_pct(max_ece)}.")

    if a.platt["ece_after"] < a.platt["ece_before"] * 0.7:
        f.append(f"FIX   Platt scaling (a={a.platt['a']:.2f}, b={a.platt['b']:.2f}) cuts held-out "
                 f"ECE {_pct(a.platt['ece_before'])} -> {_pct(a.platt['ece_after'])}. "
                 "Apply it before trusting raw scores.")

    op = a.operating_point
    if op is None:
        a.passed = False
        f.append(f"FAIL  No confidence cut-off reliably reaches {_pct(a.target)} accuracy. "
                 "Every case needs human review, or the target must be revisited.")
    else:
        f.append(f"PLAN  Automate when confidence >= {op.threshold:.3f}: the AI decides "
                 f"{_pct(op.coverage)} of cases at {_pct(op.accuracy)} accuracy "
                 f"(>= {_pct(op.lower)} with 95% confidence); {_pct(1 - op.coverage)} go to a human.")

    if len(a.groups) < 2:
        return
    worst = max(a.groups, key=lambda g: g.ece)
    best = min(a.groups, key=lambda g: g.ece)
    if worst.ece - best.ece > max_gap:
        a.passed = False
        f.append(f"FAIL  Calibration gap between groups: '{worst.group}' ECE {_pct(worst.ece)} vs "
                 f"'{best.group}' {_pct(best.ece)}. Its confidence scores mean less.")
    if op is not None:
        for g in a.groups:
            if g.auto_n and g.auto_accuracy < a.target:
                a.passed = False
                f.append(f"FAIL  Group '{g.group}': automated accuracy {_pct(g.auto_accuracy)} "
                         f"(n={g.auto_n}) is below the {_pct(a.target)} target. One global "
                         "threshold does not protect this group.")
        hi = max(a.groups, key=lambda g: g.deferred)
        lo = min(a.groups, key=lambda g: g.deferred)
        if lo.deferred > 0 and hi.deferred / lo.deferred >= 1.25:
            f.append(f"NOTE  '{hi.group}' cases go to a human {hi.deferred / lo.deferred:.1f}x as often "
                     f"as '{lo.group}' ({_pct(hi.deferred)} vs {_pct(lo.deferred)}). "
                     "Staff review queues accordingly.")
