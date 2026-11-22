# Bias audit: `hiring.csv`

**✗ ADVERSE IMPACT** — Statistically significant adverse impact detected. This system disadvantages at least one group.

- Decisions: **2,000**, favourable when `advanced = yes`
- Overall selection rate: **29.8%**
- Thresholds: impact ratio < 0.8, p < 0.05, groups under 2.0% excluded

## sex

Reference group: **Male** · parity gap 14.0% · equal-opportunity gap 24.8% · false-positive gap 11.3%

| Group | n | Share | Selected | Rate | 95% CI | Impact ratio | p | TPR | FPR | Status |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Male | 973 | 48.6% | 359 | 36.9% | 33.9%–40.0% | 1.00 | 1.000 | 76.7% | 16.8% | ✓ OK |
| Nonbinary | 63 | 3.1% | 16 | 25.4% | 16.3%–37.3% | 0.69 | 0.066 | 51.9% | 5.6% | ! REVIEW |
| Female | 964 | 48.2% | 221 | 22.9% | 20.4%–25.7% | 0.62 | <0.001 | 55.5% | 6.8% | ✗ ADVERSE IMPACT |

## race

Reference group: **White** · parity gap 21.3% · equal-opportunity gap 31.9% · false-positive gap 15.1%

| Group | n | Share | Selected | Rate | 95% CI | Impact ratio | p | TPR | FPR | Status |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| White | 1042 | 52.1% | 371 | 35.6% | 32.8%–38.6% | 1.00 | 1.000 | 72.4% | 15.7% | ✓ OK |
| Asian | 219 | 10.9% | 77 | 35.2% | 29.1%–41.7% | 0.99 | 0.901 | 71.8% | 17.6% | ✓ OK |
| Hispanic | 344 | 17.2% | 84 | 24.4% | 20.2%–29.2% | 0.69 | <0.001 | 63.1% | 6.0% | ✗ ADVERSE IMPACT |
| Black | 356 | 17.8% | 51 | 14.3% | 11.1%–18.3% | 0.40 | <0.001 | 40.5% | 2.4% | ✗ ADVERSE IMPACT |
| Unknown | 39 | 1.9% | 13 | 33.3% | 20.6%–49.0% | — | — | 76.9% | 11.5% | · EXCLUDED |

## sex × race

Reference group: **Male × White** · parity gap 30.5% · equal-opportunity gap 42.2% · false-positive gap 22.8%

| Group | n | Share | Selected | Rate | 95% CI | Impact ratio | p | TPR | FPR | Status |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Male × White | 524 | 26.2% | 234 | 44.7% | 40.5%–48.9% | 1.00 | 1.000 | 83.2% | 22.8% | ✓ OK |
| Male × Asian | 104 | 5.2% | 42 | 40.4% | 31.5%–50.0% | 0.90 | 0.423 | 78.8% | 22.5% | ✓ OK |
| Male × Hispanic | 157 | 7.8% | 50 | 31.8% | 25.1%–39.5% | 0.71 | 0.004 | 78.8% | 8.6% | ✗ ADVERSE IMPACT |
| Female × Asian | 107 | 5.3% | 31 | 29.0% | 21.2%–38.2% | 0.65 | 0.003 | 63.6% | 13.5% | ✗ ADVERSE IMPACT |
| Female × White | 488 | 24.4% | 127 | 26.0% | 22.3%–30.1% | 0.58 | <0.001 | 60.4% | 8.6% | ✗ ADVERSE IMPACT |
| Female × Hispanic | 177 | 8.8% | 33 | 18.6% | 13.6%–25.0% | 0.42 | <0.001 | 50.9% | 4.1% | ✗ ADVERSE IMPACT |
| Male × Black | 167 | 8.3% | 25 | 15.0% | 10.4%–21.2% | 0.34 | <0.001 | 42.2% | 4.9% | ✗ ADVERSE IMPACT |
| Female × Black | 176 | 8.8% | 25 | 14.2% | 9.8%–20.1% | 0.32 | <0.001 | 41.0% | 0.0% | ✗ ADVERSE IMPACT |
| Nonbinary × Asian | 8 | 0.4% | 4 | 50.0% | 21.5%–78.5% | — | — | 80.0% | 0.0% | · EXCLUDED |
| Nonbinary × White | 30 | 1.5% | 10 | 33.3% | 19.2%–51.2% | — | — | 66.7% | 11.1% | · EXCLUDED |
| Unknown | 39 | 1.9% | 13 | 33.3% | 20.6%–49.0% | — | — | 76.9% | 11.5% | · EXCLUDED |
| Nonbinary × Hispanic | 10 | 0.5% | 1 | 10.0% | 1.8%–40.4% | — | — | 25.0% | 0.0% | · EXCLUDED |
| Nonbinary × Black | 13 | 0.7% | 1 | 7.7% | 1.4%–33.3% | — | — | 20.0% | 0.0% | · EXCLUDED |

