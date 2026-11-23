"""Core fairness math: selection rates, impact ratios, and how much to trust them.

Everything here is plain Python. An *audit* answers one question per
demographic dimension: "does any group receive the favourable outcome at less
than four-fifths (80%) of the rate of the most-favoured group?"
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Mapping, Sequence

# Values treated as "demographic data not available". Reported, never guessed.
UNKNOWN = {"", "unknown", "na", "n/a", "nan", "none", "null", "?",
           "prefer not to say", "declined", "not disclosed"}

# Values treated as a favourable outcome in selection mode.
TRUTHY = {"1", "1.0", "true", "t", "yes", "y", "selected", "hired",
          "advanced", "pass", "passed", "approved", "accepted"}

LOW_N = 30  # below this, rates swing wildly with each individual


def _norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def is_unknown(value: object) -> bool:
    return _norm(value).lower() in UNKNOWN


def to_outcomes(values: Sequence[object], scored: bool = False) -> list[bool]:
    """Turn raw outcome values into favourable (True) / not favourable (False).

    selection mode: a value is favourable if it looks like "yes" / "1" / "hired".
    scoring mode:   a value is favourable if it is above the sample median
                    (the "scoring rate" definition used by NYC Local Law 144).
    """
    if not scored:
        return [_norm(v).lower() in TRUTHY for v in values]
    try:
        scores = [float(_norm(v)) for v in values]
    except ValueError as err:
        raise ValueError(f"scoring mode needs numeric outcomes: {err}") from None
    cut = median(scores)
    return [s > cut for s in scores]


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value for 'these two groups have the same underlying rate'."""
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def is_fragile(pos: int, n: int, ref_rate: float, threshold: float) -> bool:
    """True if changing a single person's outcome would flip the verdict.

    A result that hinges on one individual is not evidence of anything
    on its own; it is a prompt to collect more data.
    """
    if ref_rate == 0:
        return False
    failing = pos / n / ref_rate < threshold
    if failing:
        return pos < n and (pos + 1) / n / ref_rate >= threshold
    return pos > 0 and (pos - 1) / n / ref_rate < threshold


@dataclass(frozen=True)
class Group:
    name: str
    n: int
    positives: int
    share: float                 # fraction of records with known values
    rate: float                  # selection / scoring rate
    impact_ratio: float | None   # rate ÷ reference rate
    p_value: float | None        # vs reference group
    fragile: bool                # verdict flips if one outcome changes
    status: str                  # reference | ok | adverse | excluded

    @property
    def low_n(self) -> bool:
        return self.n < LOW_N


@dataclass(frozen=True)
class Dimension:
    name: str
    groups: tuple[Group, ...]
    unknown: int

    @property
    def reference(self) -> Group | None:
        return next((g for g in self.groups if g.status == "reference"), None)

    @property
    def adverse(self) -> list[Group]:
        return [g for g in self.groups if g.status == "adverse"]


@dataclass(frozen=True)
class Audit:
    outcome: str
    mode: str          # selection | scoring
    total: int
    positives: int
    threshold: float
    min_share: float
    dimensions: tuple[Dimension, ...]

    @property
    def has_adverse_impact(self) -> bool:
        return any(d.adverse for d in self.dimensions)


def _dimension(name: str, labels: Sequence[str | None], hits: Sequence[bool],
               threshold: float, min_share: float) -> Dimension:
    n: Counter[str] = Counter()
    pos: Counter[str] = Counter()
    for label, hit in zip(labels, hits):
        if label is not None:
            n[label] += 1
            pos[label] += hit

    known = sum(n.values())
    if not known:
        raise ValueError(f"column {name!r} has no known values")

    rate = {g: pos[g] / n[g] for g in n}
    included = [g for g in n if n[g] / known >= min_share] or list(n)
    ref = max(included, key=lambda g: (rate[g], n[g]))
    ref_rate = rate[ref]

    groups = []
    for g in sorted(n, key=lambda g: (-rate[g], g)):
        ir = rate[g] / ref_rate if ref_rate else None
        if g == ref:
            status, p, fragile = "reference", None, False
        else:
            p = two_proportion_p(pos[g], n[g], pos[ref], n[ref])
            fragile = is_fragile(pos[g], n[g], ref_rate, threshold)
            if g not in included:
                status = "excluded"
            elif ir is not None and ir < threshold:
                status = "adverse"
            else:
                status = "ok"
        groups.append(Group(g, n[g], pos[g], n[g] / known, rate[g],
                            ir, p, fragile, status))

    return Dimension(name, tuple(groups), len(labels) - known)


def audit(rows: Iterable[Mapping[str, object]], outcome: str, by: Sequence[str], *,
          scored: bool = False, intersect: bool = True,
          threshold: float = 0.8, min_share: float = 0.02) -> Audit:
    """Run a disparate-impact audit.

    rows       records (e.g. from csv.DictReader or DataFrame.to_dict("records"))
    outcome    column holding the decision (selection) or score (scoring)
    by         demographic columns to audit, e.g. ["sex", "race"]
    intersect  also audit the combination of all `by` columns
    threshold  impact-ratio benchmark (0.8 = the four-fifths rule)
    min_share  groups below this share are reported but not flagged
    """
    rows = list(rows)
    if not rows:
        raise ValueError("no records to audit")
    missing = [c for c in (outcome, *by) if c not in rows[0]]
    if missing:
        raise ValueError(f"missing column(s): {', '.join(missing)}")

    hits = to_outcomes([r[outcome] for r in rows], scored)
    labels: dict[str, list[str | None]] = {
        col: [None if is_unknown(r[col]) else _norm(r[col]) for r in rows] for col in by
    }
    if intersect and len(by) > 1:
        cols = [labels[c] for c in by]
        labels[" × ".join(by)] = [
            None if None in combo else " · ".join(combo)  # type: ignore[arg-type]
            for combo in zip(*cols)
        ]

    dims = tuple(_dimension(name, vals, hits, threshold, min_share)
                 for name, vals in labels.items())
    return Audit(outcome, "scoring" if scored else "selection", len(rows),
                 sum(hits), threshold, min_share, dims)
