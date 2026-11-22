# Bias audit — hiring_sample.csv

_Generated 2026-11-22 · 2,400 records · threshold 0.80_

**Summary:** 9 group(s) fall below the impact-ratio threshold, 8 of them statistically significant: Nonbinary (0.799); Female (0.521); Hispanic/Latino (0.451); Male · Black (0.792); Female · Asian (0.637); Female · Black (0.590); Male · Hispanic/Latino (0.493); Female · White (0.443); Female · Hispanic/Latino (0.218).

## sex

Reference group (highest rate): **Male**

| Group | N | Share | Selected | Rate | Impact ratio | p-value | TPR | TPR ratio | Flags |
|---|---|---|---|---|---|---|---|---|---|
| Male | 1,288 | 53.7% | 451 | 35.0% | 1.000 | ref | 69.0% | 1.000 | ✓ |
| Nonbinary | 50 | 2.1% | 14 | 28.0% | 0.799 | 0.307 | 54.2% | 0.785 | adverse impact, unequal opportunity |
| Female | 1,062 | 44.2% | 194 | 18.3% | 0.521 | <0.001 | 41.3% | 0.599 | adverse impact, statistically significant, unequal opportunity |

## race_ethnicity

Reference group (highest rate): **Asian**

| Group | N | Share | Selected | Rate | Impact ratio | p-value | TPR | TPR ratio | Flags |
|---|---|---|---|---|---|---|---|---|---|
| Native American | 24 | 1.0% | 9 | 37.5% | 1.142 | 0.639 | 66.7% | 1.034 | small sample |
| Asian | 335 | 14.0% | 110 | 32.8% | 1.000 | ref | 64.5% | 1.000 | ✓ |
| White | 1,069 | 44.5% | 329 | 30.8% | 0.937 | 0.478 | 64.3% | 0.996 | ✓ |
| Black | 430 | 17.9% | 126 | 29.3% | 0.892 | 0.294 | 57.1% | 0.885 | ✓ |
| Unknown | 50 | 2.1% | 12 | 24.0% | 0.730 | 0.210 | 61.1% | 0.947 | unknown category |
| Hispanic/Latino | 492 | 20.5% | 73 | 14.8% | 0.451 | <0.001 | 33.5% | 0.519 | adverse impact, statistically significant, unequal opportunity |

## sex × race_ethnicity

Reference group (highest rate): **Male · White**

| Group | N | Share | Selected | Rate | Impact ratio | p-value | TPR | TPR ratio | Flags |
|---|---|---|---|---|---|---|---|---|---|
| Nonbinary · Asian | 2 | 0.1% | 1 | 50.0% | 1.213 | 1.000 | 100.0% | 1.259 | small sample |
| Male · Native American | 13 | 0.5% | 6 | 46.2% | 1.120 | 0.719 | 83.3% | 1.049 | small sample |
| Male · White | 573 | 23.9% | 236 | 41.2% | 1.000 | ref | 79.4% | 1.000 | ✓ |
| Nonbinary · Black | 10 | 0.4% | 4 | 40.0% | 0.971 | 1.000 | 80.0% | 1.007 | small sample |
| Male · Asian | 192 | 8.0% | 72 | 37.5% | 0.910 | 0.367 | 73.8% | 0.929 | ✓ |
| Male · Unknown | 25 | 1.0% | 9 | 36.0% | 0.874 | 0.606 | 72.7% | 0.915 | small sample |
| Male · Black | 239 | 10.0% | 78 | 32.6% | 0.792 | 0.023 | 66.3% | 0.835 | adverse impact, statistically significant |
| Nonbinary · White | 25 | 1.0% | 7 | 28.0% | 0.679 | 0.189 | 50.0% | 0.629 | small sample |
| Female · Native American | 11 | 0.5% | 3 | 27.3% | 0.662 | 0.538 | 50.0% | 0.629 | small sample |
| Female · Asian | 141 | 5.9% | 37 | 26.2% | 0.637 | 0.001 | 52.2% | 0.657 | adverse impact, statistically significant, unequal opportunity |
| Female · Black | 181 | 7.5% | 44 | 24.3% | 0.590 | <0.001 | 45.7% | 0.574 | adverse impact, statistically significant, unequal opportunity |
| Male · Hispanic/Latino | 246 | 10.2% | 50 | 20.3% | 0.493 | <0.001 | 42.1% | 0.530 | adverse impact, statistically significant, unequal opportunity |
| Female · White | 471 | 19.6% | 86 | 18.3% | 0.443 | <0.001 | 44.0% | 0.553 | adverse impact, statistically significant, unequal opportunity |
| Nonbinary · Hispanic/Latino | 13 | 0.5% | 2 | 15.4% | 0.373 | 0.085 | 33.3% | 0.419 | small sample |
| Female · Unknown | 25 | 1.0% | 3 | 12.0% | 0.291 | 0.003 | 42.9% | 0.539 | small sample |
| Female · Hispanic/Latino | 233 | 9.7% | 21 | 9.0% | 0.218 | <0.001 | 22.8% | 0.287 | adverse impact, statistically significant, unequal opportunity |

---
Impact ratio = group rate ÷ reference rate. Below the threshold suggests adverse impact (EEOC four-fifths rule). Groups under 2% of the sample are reported but not flagged.
