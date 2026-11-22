"""Re-identification risk metrics.

Rows sharing the same quasi-identifier values form an *equivalence class*:
an attacker who knows someone's ZIP, birth date and sex can narrow them down
to that class and no further. Small classes mean high risk.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field


def equivalence_classes(rows, qis):
    """Group row indexes by their quasi-identifier values."""
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[tuple(row[q] for q in qis)].append(i)
    return groups


@dataclass
class Diversity:
    """How well a sensitive attribute is hidden inside each class (l-diversity)."""
    column: str
    l_min: int                 # fewest distinct sensitive values in any class
    homogeneous_classes: int   # classes where everyone shares the same value
    homogeneous_records: int   # records whose sensitive value is thereby revealed


@dataclass
class Risk:
    records: int
    qis: list
    k_target: int
    k_min: int            # k-anonymity: size of the smallest class
    classes: int
    unique: int           # records that are alone in their class
    at_risk: int          # records in classes smaller than k_target
    avg_risk: float       # mean probability of a correct re-identification
    max_risk: float       # worst-case probability (1 / k_min)
    size_histogram: dict  # class size bucket -> number of records
    diversity: list = field(default_factory=list)

    @property
    def passes(self):
        return self.records == 0 or self.k_min >= self.k_target

    @property
    def unique_pct(self):
        return 100 * self.unique / self.records if self.records else 0.0

    @property
    def at_risk_pct(self):
        return 100 * self.at_risk / self.records if self.records else 0.0


BUCKETS = [(1, 1, "1 (unique)"), (2, 4, "2-4"), (5, 9, "5-9"),
           (10, 49, "10-49"), (50, float("inf"), "50+")]


def assess(rows, qis, sensitive=(), k=5):
    """Measure how exposed each record is through its quasi-identifiers."""
    n = len(rows)
    groups = equivalence_classes(rows, qis) if n else {}
    sizes = [len(g) for g in groups.values()]
    histogram = {label: 0 for _, _, label in BUCKETS}
    for s in sizes:
        label = next(lbl for lo, hi, lbl in BUCKETS if lo <= s <= hi)
        histogram[label] += s

    diversity = []
    for col in sensitive:
        l_min, homo_c, homo_r = None, 0, 0
        for members in groups.values():
            distinct = len({rows[i][col] for i in members})
            l_min = distinct if l_min is None else min(l_min, distinct)
            if distinct == 1:
                homo_c += 1
                homo_r += len(members)
        diversity.append(Diversity(col, l_min or 0, homo_c, homo_r))

    return Risk(
        records=n, qis=list(qis), k_target=k,
        k_min=min(sizes) if sizes else 0,
        classes=len(groups),
        unique=sum(1 for s in sizes if s == 1),
        at_risk=sum(s for s in sizes if s < k),
        # Each record's risk is 1/|class|; summed over a class that is 1,
        # so the average over all records is simply classes / records.
        avg_risk=len(groups) / n if n else 0.0,
        max_risk=1 / min(sizes) if sizes else 0.0,
        size_histogram=histogram,
        diversity=diversity,
    )


def drivers(rows, qis):
    """Rank quasi-identifiers by how much uniqueness each one causes.

    For every column we measure how many records would stop being unique if
    that column were removed. The biggest drop is the column to generalize first.
    """
    def unique_count(cols):
        counts = Counter(tuple(r[c] for c in cols) for r in rows)
        return sum(1 for c in counts.values() if c == 1)

    base = unique_count(qis)
    result = []
    for q in qis:
        rest = [c for c in qis if c != q]
        after = unique_count(rest) if rest else 0
        result.append((q, base - after, len({r[q] for r in rows})))
    return sorted(result, key=lambda t: -t[1])
