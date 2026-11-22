# Bias Audit Report

- **Source:** applicants.csv
- **Date:** 2026-11-22
- **Rows:** 2,000
- **Metric:** Selection rate

> **⚠️ 2 categories below the 0.8 threshold: Female · Asian (0.78), Female · Black (0.73).**

## sex

| Category | Applicants | Selected | Rate | Impact ratio | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Male | 984 | 486 | 49.4% | 1.000 | ref | ok |
| Female | 949 | 404 | 42.6% | 0.862 | 0.003 | ok |

_67 applicant(s) with unknown category were excluded from this view._

## race_ethnicity

| Category | Applicants | Selected | Rate | Impact ratio | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Native Hawaiian or Pacific Islander | 20 | 12 | 60.0% | — | — | too few |
| Hispanic or Latino | 386 | 188 | 48.7% | 1.000 | ref | ok |
| White | 832 | 396 | 47.6% | 0.977 | 0.719 | ok |
| Two or more races | 87 | 40 | 46.0% | 0.944 | 0.646 | ok |
| Asian | 271 | 119 | 43.9% | 0.902 | 0.225 | ok |
| Black | 379 | 164 | 43.3% | 0.888 | 0.132 | ok |

_25 applicant(s) with unknown category were excluded from this view._

## sex × race_ethnicity

| Category | Applicants | Selected | Rate | Impact ratio | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Female · Native Hawaiian or Pacific Islander | 10 | 6 | 60.0% | — | — | too few |
| Male · Native Hawaiian or Pacific Islander | 9 | 5 | 55.6% | — | — | too few |
| Male · Hispanic or Latino | 194 | 101 | 52.1% | 1.000 | ref | ok |
| Male · White | 409 | 209 | 51.1% | 0.982 | 0.825 | ok |
| Male · Black | 183 | 87 | 47.5% | 0.913 | 0.380 | ok |
| Male · Two or more races | 41 | 19 | 46.3% | 0.890 | 0.506 | ok |
| Male · Asian | 136 | 62 | 45.6% | 0.876 | 0.247 | ok |
| Female · White | 399 | 177 | 44.4% | 0.852 | 0.078 | ok |
| Female · Hispanic or Latino | 176 | 78 | 44.3% | 0.851 | 0.137 | ok |
| Female · Two or more races | 42 | 18 | 42.9% | 0.823 | 0.279 | ok |
| Female · Asian | 126 | 51 | 40.5% | 0.777 | 0.043 | **adverse impact** |
| Female · Black | 184 | 70 | 38.0% | 0.731 | 0.006 | **adverse impact** |

_91 applicant(s) with unknown category were excluded from this view._

---
_Impact ratios are a screening signal, not a verdict. A low ratio warrants investigation; a passing ratio does not prove a process is fair. This report is not legal advice._
