# Résumé screener — Q3 audit

**Verdict:** ✗ Adverse impact detected  
**Decisions analysed:** 2,400 · **Overall rate:** 31.5% · **Date:** 2026-11-22

## sex

| Group | n | Share | Rate | Impact ratio | p-value | TPR | FPR | Status |
|---|---|---|---|---|---|---|---|---|
| Male | 1,231 | 51.3% | 33.8% | 1.00 | — | 76.5% | 6.0% | ✓ pass |
| Female | 1,131 | 47.1% | 29.4% | 0.87 | 0.023 | 65.4% | 4.1% | ✓ pass |
| Non-binary | 38 | 1.6% | 21.1% | — | — | 72.7% | 0.0% | – n/a |

## race_ethnicity

| Group | n | Share | Rate | Impact ratio | p-value | TPR | FPR | Status |
|---|---|---|---|---|---|---|---|---|
| White | 1,223 | 51.0% | 35.2% | 1.00 | — | 77.5% | 6.4% | ✓ pass |
| Asian | 294 | 12.2% | 33.3% | 0.95 | 0.555 | 69.1% | 7.6% | ✓ pass |
| Hispanic or Latino | 384 | 16.0% | 28.6% | 0.81 | 0.018 | 65.2% | 1.4% | ✓ pass |
| Two or More Races | 82 | 3.4% | 24.4% | 0.69 | 0.047 | 72.0% | 3.5% | ✗ fail |
| Black or African American | 322 | 13.4% | 20.8% | 0.59 | <0.001 | 51.6% | 2.0% | ✗ fail |
| American Indian | 44 | 1.8% | 43.2% | — | — | 85.0% | 8.3% | – n/a |
| Unknown | 51 | 2.1% | 25.5% | — | — | 75.0% | 2.9% | – n/a |

## Findings

- [sex] Among genuinely qualified people, selection rates differ by 11.1% between groups (equal-opportunity gap).
- [sex] Excluded for small size (<2% of data): Non-binary. Their outcomes are still shown but not judged.
- [race_ethnicity] Two or More Races candidates are selected at 0.69× the rate of White (24.4% vs 35.2%); statistically significant (p 0.047).
- [race_ethnicity] Black or African American candidates are selected at 0.59× the rate of White (20.8% vs 35.2%); statistically significant (p <0.001).
- [race_ethnicity] Among genuinely qualified people, selection rates differ by 25.9% between groups (equal-opportunity gap).
- [race_ethnicity] Excluded for small size (<2% of data): American Indian. Their outcomes are still shown but not judged.

## Method

- **Impact ratio** = group rate ÷ highest group rate. Below **0.8** fails the EEOC four-fifths rule and is how NYC Local Law 144 audits report results.
- **p-value**: two-proportion z-test against the highest group; **fail** requires p < 0.05.
- Groups under 2% of the data and unknown values are shown but not judged.
- A passing audit is evidence, not proof, of fairness. Review job-relatedness and data quality too.
