"""Core audit logic: selection rates, impact ratios and flags.

Terminology follows the EEOC "four-fifths rule" (29 CFR 1607.4(D)) and the
NYC Local Law 144 bias-audit rules for automated employment decision tools:

- selection rate  = selected / total, per group
- scoring rate    = share of a group scoring above the overall median
                    (used when the outcome is a continuous score)
- impact ratio    = group rate / rate of the most-selected group
- adverse impact  = impact ratio below the threshold (default 0.8)
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from statistics import median
from typing import Iterable, Mapping, Sequence

from .stats import two_proportion_p

TRUE_WORDS = {"1", "true", "yes", "y", "selected", "hired", "pass", "approved", "accept", "accepted"}
FALSE_WORDS = {"0", "false", "no", "n", "rejected", "declined", "fail", "denied", "reject"}
JOIN = " × "


@dataclass(frozen=True)
class GroupResult:
    group: str
    n: int
    selected: int
    rate: float
    impact_ratio: float | None = None
    p_value: float | None = None
    excluded: bool = False  # too small to judge (below --min-share)

    @property
    def is_reference(self) -> bool:
        return self.impact_ratio == 1.0 and self.p_value is None and not self.excluded


@dataclass
class AttributeResult:
    attribute: str
    groups: list[GroupResult]
    unknown: int = 0  # rows with a blank value for this attribute
    threshold: float = 0.8

    def flagged(self) -> list[GroupResult]:
        return [g for g in self.groups if not g.excluded and g.impact_ratio is not None
                and g.impact_ratio < self.threshold]


@dataclass
class Audit:
    outcome: str
    mode: str  # "selection" or "scoring"
    total: int
    threshold: float
    min_share: float
    attributes: list[AttributeResult] = field(default_factory=list)
    median_score: float | None = None

    def flagged(self) -> list[tuple[str, GroupResult]]:
        return [(a.attribute, g) for a in self.attributes for g in a.flagged()]

    @property
    def passed(self) -> bool:
        return not self.flagged()


# ── input ────────────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f)]


def to_outcomes(values: Sequence[str], mode: str = "auto") -> tuple[list[bool], str, float | None]:
    """Turn raw outcome strings into booleans.

    Binary labels ("hired", "1", "yes", ...) are used as-is. Numeric scores are
    converted to "scored above the overall median", per NYC LL144.
    """
    lowered = [v.strip().lower() for v in values]
    is_binary = all(v in TRUE_WORDS | FALSE_WORDS for v in lowered)
    if mode == "selection" or (mode == "auto" and is_binary):
        if not is_binary:
            bad = next(v for v in values if v.strip().lower() not in TRUE_WORDS | FALSE_WORDS)
            raise ValueError(f"outcome value {bad!r} is not a recognised yes/no label")
        return [v in TRUE_WORDS for v in lowered], "selection", None
    try:
        scores = [float(v) for v in values]
    except ValueError as e:
        raise ValueError(f"outcome column is neither yes/no labels nor numeric scores ({e})") from None
    mid = median(scores)
    return [s > mid for s in scores], "scoring", mid


# ── computation ──────────────────────────────────────────────────────────────

def _rates(labels: Iterable[str], outcomes: Iterable[bool], total: int,
           min_share: float) -> tuple[list[GroupResult], int]:
    n, sel, unknown = Counter(), Counter(), 0
    for label, ok in zip(labels, outcomes):
        if not label:
            unknown += 1
            continue
        n[label] += 1
        sel[label] += ok

    raw = {g: (n[g], sel[g], sel[g] / n[g]) for g in n}
    eligible = {g for g, (cnt, _, _) in raw.items() if cnt / total >= min_share}
    if not eligible:
        return [GroupResult(g, c, s, r, excluded=True) for g, (c, s, r) in sorted(raw.items())], unknown

    ref = max(eligible, key=lambda g: (raw[g][2], raw[g][0]))
    ref_n, ref_sel, ref_rate = raw[ref]

    out = []
    for g, (cnt, s, r) in raw.items():
        if g not in eligible:
            out.append(GroupResult(g, cnt, s, r, excluded=True))
        elif g == ref:
            out.append(GroupResult(g, cnt, s, r, impact_ratio=1.0))
        else:
            ir = r / ref_rate if ref_rate else None
            out.append(GroupResult(g, cnt, s, r, ir, two_proportion_p(s, cnt, ref_sel, ref_n)))
    out.sort(key=lambda g: (g.excluded, -(g.impact_ratio or 0), g.group))
    return out, unknown


def audit(rows: Sequence[Mapping[str, str]], outcome: str, attributes: Sequence[str], *,
          threshold: float = 0.8, min_share: float = 0.0, intersect: bool = True,
          mode: str = "auto") -> Audit:
    """Audit `rows` for adverse impact on `outcome` across `attributes`."""
    if not rows:
        raise ValueError("no rows to audit")
    missing = [c for c in [outcome, *attributes] if c not in rows[0]]
    if missing:
        raise ValueError(f"column(s) not found: {', '.join(missing)}. Available: {', '.join(rows[0])}")

    outcomes, mode, mid = to_outcomes([r[outcome] for r in rows], mode)
    result = Audit(outcome, mode, len(rows), threshold, min_share, median_score=mid)

    def add(name: str, labels: list[str]) -> None:
        groups, unknown = _rates(labels, outcomes, len(rows), min_share)
        result.attributes.append(AttributeResult(name, groups, unknown, threshold))

    for attr in attributes:
        add(attr, [r[attr] for r in rows])

    if intersect and len(attributes) > 1:
        labels = [JOIN.join(r[a] for a in attributes) if all(r[a] for a in attributes) else ""
                  for r in rows]
        add(JOIN.join(attributes), labels)

    return result


__all__ = ["Audit", "AttributeResult", "GroupResult", "audit", "load_csv", "to_outcomes"]
