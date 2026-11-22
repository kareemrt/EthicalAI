"""Make a dataset k-anonymous by coarsening quasi-identifiers.

Each quasi-identifier gets a *generalization hierarchy*: level 0 is the raw
value and every level above it is coarser, ending in "*" (fully hidden).

    zip         02139 -> 0213* -> 021** -> 02*** -> 0**** -> *
    birth_date  1984-07-12 -> 1984-07 -> 1984 -> 1980s -> *
    age         37 -> 35-39 -> 30-39 -> 20-39 -> ... -> *
    occupation  rare values -> Other -> *

A greedy search raises one column one level at a time, always choosing the
step that protects the most records per unit of information lost, until the
remaining at-risk records fit inside the suppression budget. Those last few
records are dropped rather than distorting every other row.
"""

import math
from collections import Counter
from dataclasses import dataclass


def _nice(x):
    """Round up to 1, 2 or 5 times a power of ten."""
    if x <= 0:
        return 1
    exp = 10 ** math.floor(math.log10(x))
    return next(m * exp for m in (1, 2, 5, 10) if m * exp >= x)


def _fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


class Hierarchy:
    """Precomputed value -> generalized value maps, one per level."""

    def __init__(self, values, steps):
        distinct = set(values)
        self.maps = [{v: v for v in distinct}]
        for step in steps:
            self.maps.append({v: ("*" if not v else step(v)) for v in distinct})
        self.maps.append({v: "*" for v in distinct})

    @property
    def depth(self):
        return len(self.maps) - 1


def build_hierarchy(kind, values, k):
    if kind == "zip":
        steps = [lambda v, n=n: v[:-n] + "*" * n for n in range(1, 5)]
    elif kind == "date":
        steps = [lambda v: v[:7], lambda v: v[:4], lambda v: v[:3] + "0s"]
    elif kind == "numeric":
        nums = [float(v) for v in values if v]
        span = (max(nums) - min(nums)) if nums else 0
        integral = all(n.is_integer() for n in nums)
        steps, width = [], _nice(span / 20) if span else 1
        while nums and width < span:
            def step(v, w=width):
                lo = math.floor(float(v) / w) * w
                hi = lo + w - 1 if integral else lo + w
                return f"{_fmt(lo)}-{_fmt(hi)}"
            steps.append(step)
            width *= 2
    else:
        counts = Counter(values)
        steps = [lambda v: v if counts[v] >= k else "Other"]
    return Hierarchy(values, steps)


@dataclass
class Result:
    rows: list
    levels: dict
    depths: dict
    suppressed: int
    info_loss: float  # 0 = untouched, 1 = every quasi-identifier hidden


def _violators(keys, k):
    counts = Counter(keys)
    return sum(c for c in counts.values() if c < k)


def anonymize(rows, qis, kinds, k=5, max_suppress=0.05, drop=()):
    """Return a k-anonymous copy of rows plus a summary of what changed."""
    hier = {q: build_hierarchy(kinds[q], [r[q] for r in rows], k) for q in qis}
    levels = {q: 0 for q in qis}
    budget = math.floor(max_suppress * len(rows))

    def keys(lv):
        maps = [hier[q].maps[lv[q]] for q in qis]
        return [tuple(m[r[q]] for m, q in zip(maps, qis)) for r in rows]

    def loss(lv):
        return sum(lv[q] / hier[q].depth for q in qis) / len(qis) if qis else 0.0

    current = _violators(keys(levels), k)
    while current > budget:
        best = None
        for q in qis:
            if levels[q] == hier[q].depth:
                continue
            trial = {**levels, q: levels[q] + 1}
            after = _violators(keys(trial), k)
            gain = (current - after) / (loss(trial) - loss(levels))
            score = (gain, -after)
            if best is None or score > best[0]:
                best = (score, trial, after)
        if best is None:
            break
        _, levels, current = best

    final = keys(levels)
    counts = Counter(final)
    out, suppressed = [], 0
    for row, key in zip(rows, final):
        if counts[key] < k:
            suppressed += 1
            continue
        new = {c: v for c, v in row.items() if c not in drop}
        new.update(zip(qis, key))
        out.append(new)
    return Result(out, levels, {q: hier[q].depth for q in qis}, suppressed, loss(levels))
