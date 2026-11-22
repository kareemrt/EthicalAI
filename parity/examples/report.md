# Parity bias audit ❌ FAIL

Source: `examples/hiring.csv` · 2026-11-22 · four-fifths threshold 0.80 · α = 0.05

## ❌ gender

| Group | N | Selected | Rate | 95% CI | Impact | p | TPR | FPR |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Man (ref) | 769 | 270 | 35.1% | 32%–39% | 1.00 | — | 64% | 11% |
| Non-binary | 71 | 21 | 29.6% | 20%–41% | 0.84 | 0.349 | 50% | 11% |
| Woman | 760 | 198 | 26.1% | 23%–29% | 0.74 | <0.001 | 43% | 13% |

- ⚠️ Equal-opportunity gap: qualified people in the Non-binary group are selected 50% of the time vs 64% in Man.
- ❌ Adverse impact: Woman is selected at 74% of Man's rate (26% vs 35%, p<0.001).
- ⚠️ Equal-opportunity gap: qualified people in the Woman group are selected 43% of the time vs 64% in Man.

## ❌ age_band

| Group | N | Selected | Rate | 95% CI | Impact | p | TPR | FPR |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Under 40 (ref) | 997 | 336 | 33.7% | 31%–37% | 1.00 | — | 60% | 11% |
| 40 and over | 603 | 153 | 25.4% | 22%–29% | 0.75 | <0.001 | 43% | 13% |

- ❌ Adverse impact: 40 and over is selected at 75% of Under 40's rate (25% vs 34%, p<0.001).
- ⚠️ Equal-opportunity gap: qualified people in the 40 and over group are selected 43% of the time vs 60% in Under 40.

## ❌ gender × age_band

| Group | N | Selected | Rate | 95% CI | Impact | p | TPR | FPR |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Man · Under 40 (ref) | 484 | 189 | 39.0% | 35%–43% | 1.00 | — | 69% | 10% |
| Non-binary · Under 40 | 48 | 18 | 37.5% | 25%–52% | 0.96 | 0.834 | 62% | 12% |
| Man · 40 and over | 285 | 81 | 28.4% | 23%–34% | 0.73 | 0.003 | 55% | 12% |
| Woman · Under 40 | 465 | 129 | 27.7% | 24%–32% | 0.71 | <0.001 | 48% | 12% |
| Woman · 40 and over | 295 | 69 | 23.4% | 19%–29% | 0.60 | <0.001 | 36% | 13% |
| Non-binary · 40 and over | 23 | 3 | 13.0% | 5%–32% | 0.33 | 0.012 | 20% | 8% |

- ❌ Adverse impact: Man · 40 and over is selected at 73% of Man · Under 40's rate (28% vs 39%, p=0.003).
- ⚠️ Equal-opportunity gap: qualified people in the Man · 40 and over group are selected 55% of the time vs 69% in Man · Under 40.
- ❌ Adverse impact: Woman · Under 40 is selected at 71% of Man · Under 40's rate (28% vs 39%, p<0.001).
- ⚠️ Equal-opportunity gap: qualified people in the Woman · Under 40 group are selected 48% of the time vs 69% in Man · Under 40.
- ❌ Adverse impact: Woman · 40 and over is selected at 60% of Man · Under 40's rate (23% vs 39%, p<0.001).
- ⚠️ Equal-opportunity gap: qualified people in the Woman · 40 and over group are selected 36% of the time vs 69% in Man · Under 40.
- ℹ️ Non-binary · 40 and over: only 23 records, too few for reliable conclusions.
- ⚠️ Below the four-fifths line but inconclusive: Non-binary · 40 and over is selected at 33% of Man · Under 40's rate (13% vs 39%, p=0.012). Collect more data before drawing conclusions.
- ⚠️ Equal-opportunity gap: qualified people in the Non-binary · 40 and over group are selected 20% of the time vs 69% in Man · Under 40.

