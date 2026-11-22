# Bias audit report

**3,000** decisions · **32.9%** selected · flag rule: impact ratio < 0.80 and p < 0.05

## Findings

- ✖ **Adverse** — 40 and over (age_band) selected at 22.0% vs 38.1% for Under 40 — impact ratio 0.58, p <0.001: below the four-fifths threshold and unlikely to be chance.
- ✖ **Adverse** — Black or African American (race_ethnicity) selected at 25.0% vs 38.4% for Two or More Races — impact ratio 0.65, p 0.008: below the four-fifths threshold and unlikely to be chance.
- ✖ **Adverse** — Female · Black or African American (sex × race_ethnicity) selected at 14.0% vs 37.6% for Male · Asian — impact ratio 0.37, p <0.001: below the four-fifths threshold and unlikely to be chance. Compounded: far worse than any single attribute shows.
- ✖ **Adverse** — 40 and over · Black or African American (age_band × race_ethnicity) selected at 17.6% vs 46.8% for Under 40 · Two or More Races — impact ratio 0.38, p <0.001: below the four-fifths threshold and unlikely to be chance. Compounded: far worse than any single attribute shows.
- 6 more intersectional groups inherit the gaps above.

## sex

| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status | TPR | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Female | 1,452 | 48.4% | 466 | 32.1% (29.7%–34.5%) | 0.94 | 0.263 | ✔ ok | 60.3% | 9.9% |
| Male | 1,436 | 47.9% | 489 | 34.1% (31.6%–36.5%) | 1.00 | 1.000 | ● reference | 64.1% | 9.0% |
| (unknown) | 112 | 3.7% | 33 | 29.5% (21.8%–38.5%) | — | — | · excluded | 59.2% | 6.3% |

Equal-opportunity gap (max − min TPR): **3.8%**

## age_band

| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status | TPR | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Under 40 | 2,038 | 67.9% | 776 | 38.1% (36.0%–40.2%) | 1.00 | 1.000 | ● reference | 70.8% | 12.2% |
| 40 and over | 962 | 32.1% | 212 | 22.0% (19.5%–24.8%) | 0.58 | <0.001 | ✖ adverse | 44.5% | 2.9% |

Equal-opportunity gap (max − min TPR): **26.3%**

## race_ethnicity

| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status | TPR | FPR |
|---|---|---|---|---|---|---|---|---|---|
| White | 1,534 | 51.1% | 512 | 33.4% (31.1%–35.8%) | 0.87 | 0.307 | ✔ ok | 64.1% | 9.8% |
| Hispanic or Latino | 632 | 21.1% | 217 | 34.3% (30.7%–38.1%) | 0.89 | 0.432 | ✔ ok | 67.7% | 7.9% |
| Black or African American | 392 | 13.1% | 98 | 25.0% (21.0%–29.5%) | 0.65 | 0.008 | ✖ adverse | 44.6% | 6.0% |
| Asian | 318 | 10.6% | 113 | 35.5% (30.5%–40.9%) | 0.93 | 0.606 | ✔ ok | 64.8% | 11.0% |
| Two or More Races | 99 | 3.3% | 38 | 38.4% (29.4%–48.2%) | 1.00 | 1.000 | ● reference | 60.0% | 16.3% |
| Native Hawaiian or Pacific Islander | 25 | 0.8% | 10 | 40.0% (23.4%–59.3%) | — | — | · excluded | 80.0% | 13.3% |

Equal-opportunity gap (max − min TPR): **23.2%**

## sex × age_band

| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status | TPR | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Female · Under 40 | 988 | 32.9% | 369 | 37.3% (34.4%–40.4%) | 0.96 | 0.474 | ✔ ok | 70.1% | 12.6% |
| Male · Under 40 | 979 | 32.6% | 381 | 38.9% (35.9%–42.0%) | 1.00 | 1.000 | ● reference | 71.1% | 12.3% |
| Female · 40 and over | 464 | 15.5% | 97 | 20.9% (17.5%–24.8%) | 0.54 | <0.001 | ✖ adverse | 40.9% | 3.6% |
| Male · 40 and over | 457 | 15.2% | 108 | 23.6% (20.0%–27.7%) | 0.61 | <0.001 | ✖ adverse | 49.3% | 1.6% |
| (unknown) · Under 40 | 71 | 2.4% | 26 | 36.6% (26.4%–48.2%) | — | — | · excluded | 75.0% | 5.1% |
| (unknown) · 40 and over | 41 | 1.4% | 7 | 17.1% (8.5%–31.3%) | — | — | · excluded | 29.4% | 8.3% |

Equal-opportunity gap (max − min TPR): **30.2%**

## sex × race_ethnicity

| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status | TPR | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Male · White | 761 | 25.4% | 255 | 33.5% (30.2%–36.9%) | 0.89 | 0.348 | ✔ ok | 63.9% | 9.2% |
| Female · White | 717 | 23.9% | 244 | 34.0% (30.7%–37.6%) | 0.91 | 0.417 | ✔ ok | 65.8% | 10.7% |
| Female · Hispanic or Latino | 311 | 10.4% | 109 | 35.0% (30.0%–40.5%) | 0.93 | 0.602 | ✔ ok | 66.9% | 9.3% |
| Male · Hispanic or Latino | 290 | 9.7% | 96 | 33.1% (27.9%–38.7%) | 0.88 | 0.358 | ✔ ok | 67.5% | 6.7% |
| Female · Black or African American | 193 | 6.4% | 27 | 14.0% (9.8%–19.6%) | 0.37 | <0.001 | ✖ adverse | 26.9% | 2.0% |
| Male · Black or African American | 184 | 6.1% | 67 | 36.4% (29.8%–43.6%) | 0.97 | 0.828 | ✔ ok | 60.4% | 10.2% |
| Female · Asian | 171 | 5.7% | 56 | 32.7% (26.2%–40.1%) | 0.87 | 0.372 | ✔ ok | 62.2% | 10.3% |
| Male · Asian | 141 | 4.7% | 53 | 37.6% (30.0%–45.8%) | 1.00 | 1.000 | ● reference | 66.7% | 12.0% |
| (unknown) · White | 56 | 1.9% | 13 | 23.2% (14.1%–35.8%) | — | — | · excluded | 45.8% | 6.2% |
| Male · Two or More Races | 52 | 1.7% | 16 | 30.8% (19.9%–44.3%) | — | — | · excluded | 57.7% | 3.8% |
| Female · Two or More Races | 44 | 1.5% | 22 | 50.0% (35.8%–64.2%) | — | — | · excluded | 68.2% | 31.8% |
| (unknown) · Hispanic or Latino | 31 | 1.0% | 12 | 38.7% (23.7%–56.2%) | — | — | · excluded | 78.6% | 5.9% |
| Female · Native Hawaiian or Pacific Islander | 16 | 0.5% | 8 | 50.0% (28.0%–72.0%) | — | — | · excluded | 87.5% | 12.5% |
| (unknown) · Black or African American | 15 | 0.5% | 4 | 26.7% (10.9%–52.0%) | — | — | · excluded | 75.0% | 9.1% |
| Male · Native Hawaiian or Pacific Islander | 8 | 0.3% | 2 | 25.0% (7.1%–59.1%) | — | — | · excluded | 50.0% | 16.7% |
| (unknown) · Asian | 6 | 0.2% | 4 | 66.7% (30.0%–90.3%) | — | — | · excluded | 80.0% | 0.0% |
| (unknown) · Two or More Races | 3 | 0.1% | 0 | 0.0% (0.0%–56.1%) | — | — | · excluded | 0.0% | 0.0% |
| (unknown) · Native Hawaiian or Pacific Islander | 1 | 0.0% | 0 | 0.0% (0.0%–79.3%) | — | — | · excluded | — | 0.0% |

Equal-opportunity gap (max − min TPR): **40.6%**

## age_band × race_ethnicity

| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status | TPR | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Under 40 · White | 1,042 | 34.7% | 401 | 38.5% (35.6%–41.5%) | 0.82 | 0.193 | ✔ ok | 72.6% | 13.1% |
| 40 and over · White | 492 | 16.4% | 111 | 22.6% (19.1%–26.5%) | 0.48 | <0.001 | ✖ adverse | 47.1% | 2.6% |
| Under 40 · Hispanic or Latino | 451 | 15.0% | 173 | 38.4% (34.0%–42.9%) | 0.82 | 0.204 | ✔ ok | 74.7% | 10.9% |
| Under 40 · Black or African American | 250 | 8.3% | 73 | 29.2% (23.9%–35.1%) | 0.62 | 0.008 | ✖ adverse | 53.8% | 7.5% |
| Under 40 · Asian | 211 | 7.0% | 90 | 42.7% (36.2%–49.4%) | 0.91 | 0.565 | ✔ ok | 72.4% | 13.2% |
| 40 and over · Hispanic or Latino | 181 | 6.0% | 44 | 24.3% (18.6%–31.1%) | 0.52 | <0.001 | ✖ adverse | 51.8% | 0.0% |
| 40 and over · Black or African American | 142 | 4.7% | 25 | 17.6% (12.2%–24.7%) | 0.38 | <0.001 | ✖ adverse | 30.3% | 3.0% |
| 40 and over · Asian | 107 | 3.6% | 23 | 21.5% (14.8%–30.2%) | 0.46 | <0.001 | ✖ adverse | 45.0% | 7.5% |
| Under 40 · Two or More Races | 62 | 2.1% | 29 | 46.8% (34.9%–59.0%) | 1.00 | 1.000 | ● reference | 75.9% | 21.2% |
| 40 and over · Two or More Races | 37 | 1.2% | 9 | 24.3% (13.4%–40.1%) | — | — | · excluded | 38.1% | 6.2% |
| Under 40 · Native Hawaiian or Pacific Islander | 22 | 0.7% | 10 | 45.5% (26.9%–65.3%) | — | — | · excluded | 80.0% | 16.7% |
| 40 and over · Native Hawaiian or Pacific Islander | 3 | 0.1% | 0 | 0.0% (0.0%–56.1%) | — | — | · excluded | — | 0.0% |

Equal-opportunity gap (max − min TPR): **45.6%**

> Equitas is a statistical screen, not a legal determination. A flag means the gap is large and unlikely to be chance — investigate the job-relatedness of the criteria before drawing conclusions.
