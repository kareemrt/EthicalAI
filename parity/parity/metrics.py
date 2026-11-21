"""Fairness metrics: selection rates, impact ratios and significance tests.

Two audit modes, mirroring NYC Local Law 144 (Automated Employment Decision Tools):

* selection — the tool makes a yes/no decision.
      selection rate = selected / total            (per group)
* scoring   — the tool outputs a score.
      scoring rate   = share of group scoring above the median of the full sample

In both modes
      impact ratio   = group rate / rate of the most favoured group

An impact ratio under 0.8 is the classic "four-fifths rule" signal of adverse
impact (EEOC Uniform Guidelines, 29 CFR 1607.4D). A ratio alone can be noise in
small groups, so each group is also tested against the reference group with
Fisher's exact test.
"""

from dataclasses import dataclass, field
from math import exp, lgamma
from statistics import median

from .data import is_missing, is_positive, require_columns, to_float

SEP = " × "


@dataclass
class GroupStat:
    group: str
    n: int
    hits: int                 # selected (selection mode) or above-median (scoring mode)
    share: float              # fraction of known-category records in this group
    rate: float
    ratio: float | None = None
    p_value: float | None = None
    small: bool = False       # below min_share: may be excluded per LL144
    status: str = "ok"        # reference | ok | review | flag


@dataclass
class Audit:
    attribute: str
    mode: str                 # "selection" | "scoring"
    total: int                # records considered
    unknown: int              # records with a missing category
    reference: str | None
    threshold: float
    alpha: float
    groups: list = field(default_factory=list)
    median_score: float | None = None
    skipped: int = 0          # rows with an unusable score

    @property
    def flagged(self):
        return [g for g in self.groups if g.status == "flag"]

    @property
    def review(self):
        return [g for g in self.groups if g.status == "review"]


def _lcomb(n, k):
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def fisher_exact(a, b, c, d):
    """Two-sided Fisher's exact test p-value for the 2x2 table [[a, b], [c, d]].

    Exact at any sample size, so it stays honest for the small groups where
    normal-approximation tests (z-test, chi-square) break down.
    """
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    if n == 0 or r1 == 0 or r2 == 0 or c1 == 0 or c1 == n:
        return 1.0
    base = _lcomb(n, c1)

    def logp(x):
        return _lcomb(r1, x) + _lcomb(r2, c1 - x) - base

    observed = logp(a)
    p = sum(exp(lp) for x in range(max(0, c1 - r2), min(r1, c1) + 1)
            if (lp := logp(x)) <= observed + 1e-9)
    return min(1.0, p)


def _label(row, columns):
    values = [row[c] for c in columns]
    return None if any(is_missing(v) for v in values) else SEP.join(values)


def audit(rows, columns, outcome=None, score=None,
          threshold=0.8, alpha=0.05, min_share=0.02):
    """Audit one protected attribute (or an intersection of several).

    rows      list of dicts (see data.load_rows)
    columns   one column name, or several to audit their intersection
    outcome   column holding the yes/no decision        -> selection mode
    score     column holding a numeric score            -> scoring mode
    """
    if (outcome is None) == (score is None):
        raise ValueError("give exactly one of outcome= or score=")
    columns = [columns] if isinstance(columns, str) else list(columns)
    require_columns(rows, columns + [outcome or score])

    skipped = 0
    cutoff = None
    if score is not None:
        values = [to_float(r[score]) for r in rows]
        skipped = sum(v is None for v in values)
        pairs = [(r, v) for r, v in zip(rows, values) if v is not None]
        if not pairs:
            raise ValueError(f"no numeric values in column '{score}'")
        cutoff = median(v for _, v in pairs)
        decided = [(r, v > cutoff) for r, v in pairs]
    else:
        decided = [(r, is_positive(r[outcome])) for r in rows]

    counts, unknown = {}, 0
    for row, hit in decided:
        label = _label(row, columns)
        if label is None:
            unknown += 1
            continue
        n, h = counts.get(label, (0, 0))
        counts[label] = (n + 1, h + hit)

    known = sum(n for n, _ in counts.values()) or 1
    groups = [GroupStat(group=g, n=n, hits=h, share=n / known, rate=h / n,
                        small=n / known < min_share)
              for g, (n, h) in counts.items()]
    groups.sort(key=lambda g: (-g.rate, -g.n, g.group))

    # LL144 lets auditors leave tiny categories out of the reference choice;
    # otherwise one lucky 3-person group would define "most favoured".
    eligible = [g for g in groups if not g.small] or groups
    ref = eligible[0] if eligible else None

    for g in groups:
        if ref is None or ref.rate == 0:
            g.status = "ok"
            continue
        g.ratio = g.rate / ref.rate
        if g is ref:
            g.status = "reference"
            continue
        g.p_value = fisher_exact(g.hits, g.n - g.hits, ref.hits, ref.n - ref.hits)
        if g.ratio >= threshold:
            g.status = "ok"
        elif g.p_value < alpha and not g.small:
            g.status = "flag"
        else:
            g.status = "review"

    return Audit(attribute=SEP.join(columns), mode="scoring" if score else "selection",
                 total=len(decided), unknown=unknown, reference=ref.group if ref else None,
                 threshold=threshold, alpha=alpha, groups=groups,
                 median_score=cutoff, skipped=skipped)
