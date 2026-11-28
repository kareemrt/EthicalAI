# Bias audit — November 28, 2026

**2,400 applicants** · overall selection rate **42.9%** · impact-ratio threshold **0.80** · result **FAIL**

## Findings

- Hispanic applicants (race) are selected at 60% the rate of White applicants (31.8% vs 52.8%); statistically significant.
- Black applicants (race) are selected at 45% the rate of White applicants (23.9% vs 52.8%); statistically significant.
- Male · Hispanic applicants (sex × race) are selected at 63% the rate of Male · White applicants (33.9% vs 53.6%); statistically significant.
- Female · Hispanic applicants (sex × race) are selected at 55% the rate of Male · White applicants (29.6% vs 53.6%); statistically significant.
- Male · Black applicants (sex × race) are selected at 50% the rate of Male · White applicants (26.7% vs 53.6%); statistically significant.
- Female · Black applicants (sex × race) are selected at 38% the rate of Male · White applicants (20.6% vs 53.6%); statistically significant.
- 8 group(s) were too small to assess and are NOT cleared: Female · Native American (sex × race), Male · Native American (sex × race), Native American (race), Non-binary · Asian (sex × race), Non-binary · Black (sex × race), Non-binary · Hispanic (sex × race), Non-binary · Native American (sex × race), Non-binary · White (sex × race).
- Qualified applicants are missed unevenly across race: true-positive rates differ by 32 percentage points (equal-opportunity gap).
- Qualified applicants are missed unevenly across sex × race: true-positive rates differ by 40 percentage points (equal-opportunity gap).

## sex

| Group | Applicants | Selected | Selection rate | Impact ratio | p-value | TPR | FPR | Status |
|---|---|---|---|---|---|---|---|---|
| Non-binary | 77 | 38 | 49.4% | 1.00 | — | 81.0% | 11.4% | reference |
| Male | 1,209 | 539 | 44.6% | 0.90 | 0.415 | 81.9% | 14.7% | ok |
| Female | 1,114 | 453 | 40.7% | 0.82 | 0.134 | 77.0% | 12.8% | ok |

## race

| Group | Applicants | Selected | Selection rate | Impact ratio | p-value | TPR | FPR | Status |
|---|---|---|---|---|---|---|---|---|
| White | 1,243 | 656 | 52.8% | 1.00 | — | 89.3% | 21.7% | reference |
| Asian | 279 | 127 | 45.5% | 0.86 | 0.028 | 81.9% | 15.1% | ok |
| Hispanic | 437 | 139 | 31.8% | 0.60 | <0.001 | 69.4% | 5.4% | ADVERSE IMPACT |
| Black | 397 | 95 | 23.9% | 0.45 | <0.001 | 56.9% | 0.0% | ADVERSE IMPACT |
| Native American | 44 | 13 | 29.5% | — | — | 70.6% | 3.7% | insufficient data |

## sex × race

| Group | Applicants | Selected | Selection rate | Impact ratio | p-value | TPR | FPR | Status |
|---|---|---|---|---|---|---|---|---|
| Male · White | 636 | 341 | 53.6% | 1.00 | — | 90.5% | 21.9% | reference |
| Female · White | 566 | 288 | 50.9% | 0.95 | 0.344 | 88.0% | 21.5% | ok |
| Male · Asian | 136 | 66 | 48.5% | 0.91 | 0.281 | 85.0% | 19.7% | ok |
| Female · Asian | 130 | 57 | 43.8% | 0.82 | 0.042 | 81.7% | 11.4% | ok |
| Male · Hispanic | 224 | 76 | 33.9% | 0.63 | <0.001 | 72.3% | 6.2% | ADVERSE IMPACT |
| Female · Hispanic | 199 | 59 | 29.6% | 0.55 | <0.001 | 66.7% | 4.2% | ADVERSE IMPACT |
| Male · Black | 195 | 52 | 26.7% | 0.50 | <0.001 | 61.9% | 0.0% | ADVERSE IMPACT |
| Female · Black | 194 | 40 | 20.6% | 0.38 | <0.001 | 50.0% | 0.0% | ADVERSE IMPACT |
| Female · Native American | 25 | 9 | 36.0% | — | — | 75.0% | 0.0% | insufficient data |
| Male · Native American | 18 | 4 | 22.2% | — | — | 60.0% | 7.7% | insufficient data |
| Non-binary · Asian | 13 | 4 | 30.8% | — | — | 57.1% | 0.0% | insufficient data |
| Non-binary · Black | 8 | 3 | 37.5% | — | — | 100.0% | 0.0% | insufficient data |
| Non-binary · Hispanic | 14 | 4 | 28.6% | — | — | 60.0% | 11.1% | insufficient data |
| Non-binary · Native American | 1 | 0 | 0.0% | — | — | — | 0.0% | insufficient data |
| Non-binary · White | 41 | 27 | 65.9% | — | — | 88.9% | 21.4% | insufficient data |

## Method

- **Selection rate** — share of a group's applicants the tool advanced.
- **Impact ratio** — a group's selection rate divided by the highest group's rate. Below 0.80 is the EEOC
  "four-fifths rule" signal of adverse impact; NYC Local Law 144 requires these ratios to be published.
- **p-value** — two-proportion z-test against the reference group; below 0.05 means the gap is unlikely to be chance.
- **TPR / FPR** — when ground-truth qualification is known: the share of qualified (TPR) and unqualified (FPR)
  applicants who were advanced. Unequal TPR means qualified people in some groups are being missed.
- Groups under the minimum share of the data are reported but not scored. *Not scored is not the same as fair.*

This report is a statistical screen, not a legal determination.