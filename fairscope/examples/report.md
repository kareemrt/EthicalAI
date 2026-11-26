# Bias audit — `screening.csv`

**Overall verdict: ❌ FAIL** · generated 2026-11-26 by fairscope

## gender — ⚠️ REVIEW

2,400 records · overall selection rate 32.2% · threshold 0.80

| Group | n | Share | Selected | Rate | Impact ratio | p-value | TPR | FPR | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Female | 1,159 | 48.3% | 348 | 30.0% | 0.860 | 0.0123 | 62.0% | 3.8% |  |
| Male | 1,140 | 47.5% | 398 | 34.9% | 1.000 | 1 | 71.3% | 7.0% |  |
| Non-binary | 101 | 4.2% | 27 | 26.7% | **0.766** | 0.0969 | 52.3% | 7.0% | low ratio, not significant |

- Non-binary: impact ratio 0.766 (< 0.80), selected 26.7% vs 34.9% for Male, p=0.0969
- true-positive rate (equal opportunity) differs by 19.0% across groups (limit 10%)

## race — ❌ FAIL

2,400 records · overall selection rate 32.2% · threshold 0.80

| Group | n | Share | Selected | Rate | Impact ratio | p-value | TPR | FPR | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| White | 1,250 | 52.1% | 464 | 37.1% | 0.932 | 0.408 | 73.7% | 7.5% |  |
| Hispanic | 426 | 17.8% | 108 | 25.4% | **0.636** | 6.55e-05 | 54.6% | 3.3% | adverse impact |
| Black | 413 | 17.2% | 84 | 20.3% | **0.510** | 3.78e-08 | 44.8% | 0.9% | adverse impact |
| Asian | 261 | 10.9% | 104 | 39.8% | 1.000 | 1 | 78.2% | 7.7% |  |
| Two or more | 35 | 1.5% | 9 | 25.7% | 0.645 | 0.106 | 64.3% | 0.0% | small sample |
| Native American | 15 | 0.6% | 4 | 26.7% | 0.669 | 0.309 | 100.0% | 0.0% | small sample |

- Hispanic: impact ratio 0.636 (< 0.80), selected 25.4% vs 39.8% for Asian, p=6.55e-05
- Black: impact ratio 0.510 (< 0.80), selected 20.3% vs 39.8% for Asian, p=3.78e-08
- true-positive rate (equal opportunity) differs by 33.3% across groups (limit 10%)
- excluded for small sample (< 2% of records): Two or more, Native American

## gender × race — ❌ FAIL

2,400 records · overall selection rate 32.2% · threshold 0.80

| Group | n | Share | Selected | Rate | Impact ratio | p-value | TPR | FPR | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Female × White | 606 | 25.2% | 219 | 36.1% | **0.795** | 0.0535 | 72.3% | 4.6% | low ratio, not significant |
| Male × White | 591 | 24.6% | 229 | 38.7% | 0.852 | 0.17 | 76.8% | 10.1% |  |
| Female × Hispanic | 204 | 8.5% | 48 | 23.5% | **0.518** | 4.01e-05 | 47.9% | 2.7% | adverse impact |
| Male × Black | 201 | 8.4% | 54 | 26.9% | **0.591** | 0.00064 | 57.0% | 0.9% | adverse impact |
| Male × Hispanic | 201 | 8.4% | 55 | 27.4% | **0.602** | 0.000915 | 61.7% | 4.2% | adverse impact |
| Female × Black | 194 | 8.1% | 27 | 13.9% | **0.306** | 5.5e-10 | 33.3% | 0.0% | adverse impact |
| Female × Asian | 131 | 5.5% | 46 | 35.1% | **0.773** | 0.0942 | 72.7% | 7.9% | low ratio, not significant |
| Male × Asian | 121 | 5.0% | 55 | 45.5% | 1.000 | 1 | 83.3% | 8.2% |  |
| Non-binary × White | 53 | 2.2% | 16 | 30.2% | **0.664** | 0.0593 | 56.5% | 10.0% | low ratio, not significant |
| Non-binary × Hispanic | 21 | 0.9% | 5 | 23.8% | 0.524 | 0.0638 | 62.5% | 0.0% | small sample |
| Female × Two or more | 19 | 0.8% | 6 | 31.6% | 0.695 | 0.257 | 66.7% | 0.0% | small sample |
| Non-binary × Black | 18 | 0.8% | 3 | 16.7% | 0.367 | 0.0208 | 22.2% | 11.1% | small sample |
| Male × Two or more | 16 | 0.7% | 3 | 18.8% | 0.413 | 0.0422 | 60.0% | 0.0% | small sample |
| Male × Native American | 10 | 0.4% | 2 | 20.0% | 0.440 | 0.119 | 100.0% | 0.0% | small sample |
| Non-binary × Asian | 9 | 0.4% | 3 | 33.3% | 0.733 | 0.48 | 75.0% | 0.0% | small sample |
| Female × Native American | 5 | 0.2% | 2 | 40.0% | 0.880 | 0.81 | 100.0% | 0.0% | small sample |

- Female × White: impact ratio 0.795 (< 0.80), selected 36.1% vs 45.5% for Male × Asian, p=0.0535
- Female × Hispanic: impact ratio 0.518 (< 0.80), selected 23.5% vs 45.5% for Male × Asian, p=4.01e-05
- Male × Black: impact ratio 0.591 (< 0.80), selected 26.9% vs 45.5% for Male × Asian, p=0.00064
- Male × Hispanic: impact ratio 0.602 (< 0.80), selected 27.4% vs 45.5% for Male × Asian, p=0.000915
- Female × Black: impact ratio 0.306 (< 0.80), selected 13.9% vs 45.5% for Male × Asian, p=5.5e-10
- Female × Asian: impact ratio 0.773 (< 0.80), selected 35.1% vs 45.5% for Male × Asian, p=0.0942
- Non-binary × White: impact ratio 0.664 (< 0.80), selected 30.2% vs 45.5% for Male × Asian, p=0.0593
- true-positive rate (equal opportunity) differs by 50.0% across groups (limit 10%)
- false-positive rate differs by 10.1% across groups (limit 10%)
- excluded for small sample (< 2% of records): Non-binary × Hispanic, Female × Two or more, Non-binary × Black, Male × Two or more, Male × Native American, Non-binary × Asian, Female × Native American

