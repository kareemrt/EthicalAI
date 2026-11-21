# Bias audit — examples/hiring.csv

**Result: FAIL** — 2 group(s) show statistically significant adverse impact.

Mode: `selection` · impact-ratio threshold: `0.8` · significance level: `0.05` · generated 2026-11-21 by Parity

## sex

| Group | n | Selected | Selection rate | Impact ratio | p-value | Status |
|---|--:|--:|--:|--:|--:|---|
| Male | 1,943 | 805 | 41.4% | 1.00 | — | ◆ reference |
| Female | 1,937 | 725 | 37.4% | 0.90 | 0.011 | ✓ ok |

- 4,000 records · 120 with unknown category (excluded from rates, reported per LL144)

## race

| Group | n | Selected | Selection rate | Impact ratio | p-value | Status |
|---|--:|--:|--:|--:|--:|---|
| Native American or Alaska Native\* | 39 | 17 | 43.6% | 1.04 | 0.871 | ✓ ok |
| White | 2,074 | 869 | 41.9% | 1.00 | — | ◆ reference |
| Two or More Races | 110 | 45 | 40.9% | 0.98 | 0.921 | ✓ ok |
| Asian | 426 | 160 | 37.6% | 0.90 | 0.105 | ✓ ok |
| Hispanic or Latino | 688 | 256 | 37.2% | 0.89 | 0.032 | ✓ ok |
| Black or African American | 556 | 184 | 33.1% | 0.79 | <0.001 | ✗ FLAG |
| Native Hawaiian or Pacific Islander\* | 19 | 3 | 15.8% | 0.38 | 0.032 | ? review |

- 4,000 records · 88 with unknown category (excluded from rates, reported per LL144)
- group is under 2% of records — not used as reference, never auto-flagged

## sex × race

| Group | n | Selected | Selection rate | Impact ratio | p-value | Status |
|---|--:|--:|--:|--:|--:|---|
| Female × Native American or Alaska Native\* | 12 | 6 | 50.0% | 1.12 | 0.775 | ✓ ok |
| Male × Two or More Races\* | 49 | 22 | 44.9% | 1.01 | 1.000 | ✓ ok |
| Male × White | 1,026 | 457 | 44.5% | 1.00 | — | ◆ reference |
| Male × Native American or Alaska Native\* | 25 | 11 | 44.0% | 0.99 | 1.000 | ✓ ok |
| Female × White | 987 | 389 | 39.4% | 0.88 | 0.021 | ✓ ok |
| Female × Asian | 211 | 83 | 39.3% | 0.88 | 0.171 | ✓ ok |
| Female × Two or More Races\* | 56 | 22 | 39.3% | 0.88 | 0.491 | ✓ ok |
| Male × Hispanic or Latino | 328 | 125 | 38.1% | 0.86 | 0.041 | ✓ ok |
| Male × Black or African American | 257 | 95 | 37.0% | 0.83 | 0.029 | ✓ ok |
| Male × Asian | 204 | 74 | 36.3% | 0.81 | 0.030 | ✓ ok |
| Female × Hispanic or Latino | 343 | 124 | 36.2% | 0.81 | 0.007 | ✓ ok |
| Female × Black or African American | 279 | 83 | 29.7% | 0.67 | <0.001 | ✗ FLAG |
| Female × Native Hawaiian or Pacific Islander\* | 10 | 2 | 20.0% | 0.45 | 0.199 | ? review |
| Male × Native Hawaiian or Pacific Islander\* | 8 | 1 | 12.5% | 0.28 | 0.084 | ? review |

- 4,000 records · 205 with unknown category (excluded from rates, reported per LL144)
- group is under 2% of records — not used as reference, never auto-flagged

