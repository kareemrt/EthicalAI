"""Core audit engine.

Computes selection / scoring rates and impact ratios per demographic category,
following the methodology used for bias audits of Automated Employment Decision
Tools (AEDTs) under NYC Local Law 144 and the EEOC "four-fifths" rule of thumb,
and adds what those minimum standards leave out: confidence intervals,
significance tests, small-sample warnings, intersectional analysis and drift
over time.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import stats

TRUTHY = {"1", "true", "t", "yes", "y", "selected", "hired", "advanced", "pass", "passed", "accept", "accepted"}
FALSY = {"0", "false", "f", "no", "n", "rejected", "declined_offer", "fail", "failed", "reject"}
UNKNOWN_VALUES = {"", "unknown", "na", "n/a", "none", "null", "declined", "prefer not to say", "not disclosed", "?"}

# Status labels attached to every group.
STATUS_REFERENCE = "reference"
STATUS_OK = "ok"
STATUS_ADVERSE = "adverse impact"
STATUS_WATCH = "below threshold (not significant)"
STATUS_INSUFFICIENT = "insufficient data"
STATUS_EXCLUDED = "excluded (<{:.0%} of sample)"


@dataclass
class GroupResult:
    category: str
    n: int
    positives: int
    rate: float
    rate_ci: Tuple[float, float]
    share: float
    impact_ratio: Optional[float] = None
    impact_ratio_ci: Optional[Tuple[float, float]] = None
    p_value: Optional[float] = None
    excluded: bool = False
    status: str = STATUS_OK


@dataclass
class DimensionResult:
    name: str
    columns: Tuple[str, ...]
    groups: List[GroupResult]
    reference: Optional[str]
    unknown: int

    @property
    def flagged(self) -> List[GroupResult]:
        return [g for g in self.groups if g.status == STATUS_ADVERSE]

    @property
    def watch(self) -> List[GroupResult]:
        return [g for g in self.groups if g.status == STATUS_WATCH]

    @property
    def min_impact_ratio(self) -> Optional[float]:
        ratios = [g.impact_ratio for g in self.groups if g.impact_ratio is not None and not g.excluded]
        return min(ratios) if ratios else None


@dataclass
class PeriodPoint:
    period: str
    dimension: str
    min_impact_ratio: Optional[float]
    worst_category: Optional[str]
    n: int


@dataclass
class AuditResult:
    title: str
    mode: str
    outcome: str
    total: int
    positives: int
    threshold: float
    min_share: float
    alpha: float
    min_group_size: int
    median_score: Optional[float]
    dimensions: List[DimensionResult]
    timeline: List[PeriodPoint] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def overall_rate(self) -> float:
        return self.positives / self.total if self.total else 0.0

    @property
    def verdict(self) -> str:
        if any(d.flagged for d in self.dimensions):
            return "ADVERSE IMPACT DETECTED"
        if any(d.watch for d in self.dimensions):
            return "REVIEW RECOMMENDED"
        return "NO ADVERSE IMPACT DETECTED"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["overall_rate"] = self.overall_rate
        d["verdict"] = self.verdict
        return d


# --------------------------------------------------------------------------- #
# Loading & parsing
# --------------------------------------------------------------------------- #

def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def parse_outcome(value: str) -> bool:
    v = (value or "").strip().lower()
    if v in TRUTHY:
        return True
    if v in FALSY:
        return False
    try:
        return float(v) > 0
    except ValueError as exc:
        raise ValueError(f"Cannot interpret outcome value {value!r} as selected / not selected") from exc


def _is_unknown(value: Optional[str], unknown_values: Iterable[str]) -> bool:
    return value is None or value.strip().lower() in unknown_values


def _binarise(rows: Sequence[Dict[str, str]], outcome: str, mode: str) -> Tuple[List[bool], Optional[float]]:
    if mode == "selection":
        return [parse_outcome(r.get(outcome, "")) for r in rows], None
    if mode == "scoring":
        scores = []
        for r in rows:
            try:
                scores.append(float(r[outcome]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Non-numeric score {r.get(outcome)!r} in column {outcome!r}") from exc
        med = stats.median(scores)
        # LL144 "scoring rate": share of a category scoring ABOVE the sample median.
        return [s > med for s in scores], med
    raise ValueError(f"mode must be 'selection' or 'scoring', got {mode!r}")


# --------------------------------------------------------------------------- #
# Core computation
# --------------------------------------------------------------------------- #

def _dimension(
    name: str,
    columns: Tuple[str, ...],
    rows: Sequence[Dict[str, str]],
    positives: Sequence[bool],
    *,
    threshold: float,
    min_share: float,
    alpha: float,
    min_group_size: int,
    unknown_values: Iterable[str],
) -> DimensionResult:
    counts: Dict[str, List[int]] = {}
    unknown = 0
    for row, pos in zip(rows, positives):
        values = [row.get(c) for c in columns]
        if any(_is_unknown(v, unknown_values) for v in values):
            unknown += 1
            continue
        label = " × ".join(v.strip() for v in values)  # type: ignore[union-attr]
        c = counts.setdefault(label, [0, 0])
        c[0] += 1
        c[1] += int(pos)

    known_total = sum(n for n, _ in counts.values())
    groups: List[GroupResult] = []
    for label, (n, k) in counts.items():
        share = n / known_total if known_total else 0.0
        groups.append(
            GroupResult(
                category=label,
                n=n,
                positives=k,
                rate=k / n if n else 0.0,
                rate_ci=stats.wilson_interval(k, n),
                share=share,
                excluded=share < min_share,
            )
        )

    eligible = [g for g in groups if not g.excluded]
    reference = max(eligible, key=lambda g: (g.rate, g.n)) if eligible else None

    for g in groups:
        if reference is None or reference.rate == 0:
            g.status = STATUS_INSUFFICIENT
            continue
        g.impact_ratio = g.rate / reference.rate
        if g is reference:
            g.status = STATUS_REFERENCE
            continue
        g.impact_ratio_ci = stats.ratio_interval(g.positives, g.n, reference.positives, reference.n)
        g.p_value = stats.two_proportion_p_value(g.positives, g.n, reference.positives, reference.n)
        if g.excluded:
            g.status = STATUS_EXCLUDED.format(min_share)
        elif g.impact_ratio >= threshold:
            g.status = STATUS_OK
        elif g.n < min_group_size:
            g.status = STATUS_INSUFFICIENT
        elif g.p_value is not None and g.p_value < alpha:
            g.status = STATUS_ADVERSE
        elif g.p_value is None and g.positives == 0:
            # Nobody in this group was selected at all: always surface it.
            g.status = STATUS_ADVERSE
        else:
            g.status = STATUS_WATCH

    groups.sort(key=lambda g: (g.impact_ratio is None, -(g.impact_ratio or 0.0), g.category))
    return DimensionResult(
        name=name,
        columns=columns,
        groups=groups,
        reference=reference.category if reference else None,
        unknown=unknown,
    )


def audit(
    rows: Sequence[Dict[str, str]],
    outcome: str,
    attributes: Dict[str, str],
    *,
    mode: str = "selection",
    intersections: Sequence[Tuple[str, ...]] = (),
    period: Optional[str] = None,
    threshold: float = 0.8,
    min_share: float = 0.02,
    alpha: float = 0.05,
    min_group_size: int = 30,
    unknown_values: Iterable[str] = UNKNOWN_VALUES,
    title: str = "Bias Audit",
) -> AuditResult:
    """Run a full bias audit.

    Parameters
    ----------
    rows:
        Records as dictionaries (e.g. from :func:`load_csv`).
    outcome:
        Column holding the decision (``mode="selection"``) or numeric score
        (``mode="scoring"``).
    attributes:
        Mapping of human-readable dimension name -> column, e.g.
        ``{"Sex": "sex", "Race/Ethnicity": "race"}``.
    intersections:
        Tuples of dimension names to cross, e.g. ``[("Sex", "Race/Ethnicity")]``.
    period:
        Optional column (e.g. ``quarter``) used to track impact ratios over time.
    """
    if not rows:
        raise ValueError("No records to audit")
    missing = [c for c in [outcome, *attributes.values(), *([period] if period else [])] if c not in rows[0]]
    if missing:
        raise ValueError(f"Column(s) not found in data: {', '.join(missing)}")

    unknown_values = {u.lower() for u in unknown_values}
    positives, med = _binarise(rows, outcome, mode)
    kwargs = dict(threshold=threshold, min_share=min_share, alpha=alpha,
                  min_group_size=min_group_size, unknown_values=unknown_values)

    specs: List[Tuple[str, Tuple[str, ...]]] = [(name, (col,)) for name, col in attributes.items()]
    for combo in intersections:
        try:
            cols = tuple(attributes[name] for name in combo)
        except KeyError as exc:
            raise ValueError(f"Intersection refers to unknown dimension {exc.args[0]!r}") from exc
        specs.append((" × ".join(combo), cols))

    dimensions = [_dimension(name, cols, rows, positives, **kwargs) for name, cols in specs]

    warnings: List[str] = []
    for d in dimensions:
        if d.unknown:
            pct = d.unknown / len(rows)
            msg = f"{d.name}: {d.unknown} record(s) ({pct:.1%}) have an unknown category and are excluded from this dimension."
            if pct > 0.1:
                msg += " High missingness can hide bias -- investigate why demographic data is missing."
            warnings.append(msg)
        for g in d.groups:
            if g.status == STATUS_INSUFFICIENT and g.impact_ratio is not None and g.impact_ratio < threshold:
                warnings.append(
                    f"{d.name} / {g.category}: impact ratio {g.impact_ratio:.2f} is below {threshold} "
                    f"but only {g.n} records (< {min_group_size}); collect more data before drawing conclusions."
                )

    timeline: List[PeriodPoint] = []
    if period:
        periods = sorted({r[period] for r in rows})
        for p in periods:
            idx = [i for i, r in enumerate(rows) if r[period] == p]
            sub_rows = [rows[i] for i in idx]
            sub_pos = [positives[i] for i in idx]
            for name, cols in specs:
                d = _dimension(name, cols, sub_rows, sub_pos, **kwargs)
                worst = min(
                    (g for g in d.groups if g.impact_ratio is not None and not g.excluded),
                    key=lambda g: g.impact_ratio,  # type: ignore[arg-type,return-value]
                    default=None,
                )
                timeline.append(
                    PeriodPoint(
                        period=p,
                        dimension=name,
                        min_impact_ratio=worst.impact_ratio if worst else None,
                        worst_category=worst.category if worst else None,
                        n=len(sub_rows),
                    )
                )

    return AuditResult(
        title=title,
        mode=mode,
        outcome=outcome,
        total=len(rows),
        positives=sum(positives),
        threshold=threshold,
        min_share=min_share,
        alpha=alpha,
        min_group_size=min_group_size,
        median_score=med,
        dimensions=dimensions,
        timeline=timeline,
        warnings=warnings,
    )
