"""Core audit: turn rows of decisions into per-group fairness statistics."""

import csv
from dataclasses import dataclass, field

from . import metrics

TRUTHY = {"1", "true", "yes", "y", "selected", "pass", "hired"}
FALSY = {"0", "false", "no", "n", "rejected", "fail", ""}


@dataclass
class GroupStat:
    group: str
    n: int
    selected: int
    rate: float
    share: float                # fraction of all audited rows in this group
    impact_ratio: float = 0.0
    p_value: float = 1.0        # vs. the highest-rate (reference) group
    excluded: bool = False      # too small to judge (LL144 permits <2% exclusion)
    tpr: float | None = None    # true-positive rate, if ground truth given
    fpr: float | None = None    # false-positive rate, if ground truth given


@dataclass
class Dimension:
    name: str                   # e.g. "sex" or "sex × race"
    groups: list[GroupStat]
    reference: str              # group with the highest selection rate

    def tpr_gap(self) -> float | None:
        vals = [g.tpr for g in self.groups if g.tpr is not None and not g.excluded]
        return max(vals) - min(vals) if len(vals) > 1 else None


@dataclass
class Audit:
    outcome: str
    mode: str                   # "binary" or "score"
    cutoff: float | None
    total: int
    threshold: float
    alpha: float
    dimensions: list[Dimension]
    warnings: list[str] = field(default_factory=list)

    def status(self, g: GroupStat) -> str:
        if g.excluded:
            return "excluded"
        if g.impact_ratio >= self.threshold:
            return "ok"
        return "adverse*" if g.p_value < self.alpha else "adverse"

    def adverse(self, significant_only: bool = False) -> list[tuple[str, GroupStat]]:
        """All (dimension, group) pairs below the impact-ratio threshold."""
        return [
            (d.name, g)
            for d in self.dimensions
            for g in d.groups
            if not g.excluded
            and g.impact_ratio < self.threshold
            and (not significant_only or g.p_value < self.alpha)
        ]


def load_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def _to_bool(value: str, column: str) -> bool:
    v = value.lower()
    if v in TRUTHY:
        return True
    if v in FALSY:
        return False
    raise ValueError(f"Column '{column}': cannot read {value!r} as yes/no")


def _is_binary(values: list[str]) -> bool:
    return all(v.lower() in TRUTHY | FALSY for v in values)


def run_audit(
    rows: list[dict[str, str]],
    outcome: str,
    attributes: list[str],
    label: str | None = None,
    cutoff: float | None = None,
    threshold: float = 0.8,
    min_share: float = 0.02,
    alpha: float = 0.05,
    intersections: bool = True,
) -> Audit:
    """Audit `rows` for disparate impact on `outcome` across `attributes`.

    `outcome` may be a yes/no decision or a numeric score. Scores are turned
    into a "scoring rate" — the share scoring above `cutoff` (default: the
    sample median, as LL144 prescribes).
    """
    if not rows:
        raise ValueError("No rows to audit")
    for col in [outcome, *attributes, *([label] if label else [])]:
        if col not in rows[0]:
            raise ValueError(f"Column '{col}' not found. Available: {', '.join(rows[0])}")

    warnings: list[str] = []
    # Rows missing a demographic value can't be attributed; count and skip.
    usable = [r for r in rows if all(r[a] for a in attributes)]
    if len(usable) < len(rows):
        warnings.append(f"{len(rows) - len(usable)} rows missing demographic data were left out.")

    raw = [r[outcome] for r in usable]
    if _is_binary(raw):
        mode = "binary"
        selected = [_to_bool(v, outcome) for v in raw]
        cutoff = None
    else:
        mode = "score"
        try:
            scores = [float(v) for v in raw]
        except ValueError as e:
            raise ValueError(f"Column '{outcome}' is neither yes/no nor numeric: {e}") from None
        cutoff = metrics.median(scores) if cutoff is None else cutoff
        selected = [s > cutoff for s in scores]

    truth = [_to_bool(r[label], label) for r in usable] if label else None

    keys = [[a] for a in attributes]
    if intersections and len(attributes) > 1:
        keys.append(list(attributes))

    dims = [
        _dimension(usable, cols, selected, truth, min_share, warnings)
        for cols in keys
    ]

    return Audit(outcome, mode, cutoff, len(usable), threshold, alpha, dims, warnings)


def _dimension(rows, cols, selected, truth, min_share, warnings) -> Dimension:
    name = " × ".join(cols)
    buckets: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        buckets.setdefault(" / ".join(r[c] for c in cols), []).append(i)

    total = len(rows)
    stats = []
    for group, idx in sorted(buckets.items()):
        k = sum(selected[i] for i in idx)
        g = GroupStat(group, len(idx), k, metrics.rate(k, len(idx)), len(idx) / total)
        g.excluded = g.share < min_share
        if truth is not None:
            pos = [i for i in idx if truth[i]]
            neg = [i for i in idx if not truth[i]]
            g.tpr = metrics.rate(sum(selected[i] for i in pos), len(pos)) if pos else None
            g.fpr = metrics.rate(sum(selected[i] for i in neg), len(neg)) if neg else None
        stats.append(g)

    # The reference group is the highest-rate group large enough to judge.
    ref = max((g for g in stats if not g.excluded), key=lambda g: g.rate, default=None) \
        or max(stats, key=lambda g: g.rate)
    for g in stats:
        g.impact_ratio = g.rate / ref.rate if ref.rate else 0.0
        g.p_value = 1.0 if g is ref else metrics.two_proportion_p(g.selected, g.n, ref.selected, ref.n)

    small = [g.group for g in stats if g.excluded]
    if small:
        warnings.append(
            f"[{name}] {len(small)} group(s) under {min_share:.0%} of the sample were not "
            f"judged: {', '.join(small)}. Report them separately; they are too small for reliable ratios."
        )
    return Dimension(name, stats, ref.group)
