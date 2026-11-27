# Bias Audit Report

**Source:** `examples/hiring_sample.csv` · **Rows:** 2400 · **Date:** 2026-11-27 · **Overall:** ❌ FAIL

## sex — ❌ FAIL

Reference group: **Male** · Unknown/missing: 0

| Group | Applicants | Selected | Rate (95% CI) | Impact ratio | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Male | 1273 | 485 | 38.1% (35.5%–40.8%) | 1.00 | — | ✅ PASS |
| Female | 1083 | 227 | 21.0% (18.6%–23.5%) | 0.55 | <0.001 | ❌ FAIL |
| Non-binary | 44 | 13 | 29.5% (18.2%–44.2%) | 0.78 | 0.250 | ➖ EXCLUDED |

## race_ethnicity — ❌ FAIL

Reference group: **White** · Unknown/missing: 56

| Group | Applicants | Selected | Rate (95% CI) | Impact ratio | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| White | 1093 | 407 | 37.2% (34.4%–40.1%) | 1.00 | — | ✅ PASS |
| Asian | 337 | 125 | 37.1% (32.1%–42.4%) | 1.00 | 0.962 | ✅ PASS |
| Hispanic or Latino | 484 | 109 | 22.5% (19.0%–26.5%) | 0.60 | <0.001 | ❌ FAIL |
| Black | 412 | 67 | 16.3% (13.0%–20.1%) | 0.44 | <0.001 | ❌ FAIL |
| Native American | 18 | 5 | 27.8% (12.5%–50.9%) | 0.75 | 0.410 | ➖ EXCLUDED |

## sex × race_ethnicity — ❌ FAIL

Reference group: **Male × White** · Unknown/missing: 56

| Group | Applicants | Selected | Rate (95% CI) | Impact ratio | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Male × White | 567 | 267 | 47.1% (43.0%–51.2%) | 1.00 | — | ✅ PASS |
| Male × Asian | 174 | 75 | 43.1% (36.0%–50.5%) | 0.92 | 0.356 | ✅ PASS |
| Male × Hispanic or Latino | 265 | 81 | 30.6% (25.3%–36.4%) | 0.65 | <0.001 | ❌ FAIL |
| Female × Asian | 156 | 46 | 29.5% (22.9%–37.1%) | 0.63 | <0.001 | ❌ FAIL |
| Female × White | 508 | 134 | 26.4% (22.7%–30.4%) | 0.56 | <0.001 | ❌ FAIL |
| Male × Black | 230 | 50 | 21.7% (16.9%–27.5%) | 0.46 | <0.001 | ❌ FAIL |
| Female × Hispanic or Latino | 214 | 27 | 12.6% (8.8%–17.7%) | 0.27 | <0.001 | ❌ FAIL |
| Female × Black | 172 | 17 | 9.9% (6.3%–15.3%) | 0.21 | <0.001 | ❌ FAIL |
| Non-binary × Asian | 7 | 4 | 57.1% (25.0%–84.2%) | 1.21 | 0.596 | ➖ EXCLUDED |
| Male × Native American | 7 | 3 | 42.9% (15.8%–75.0%) | 0.91 | 0.824 | ➖ EXCLUDED |
| Non-binary × Native American | 3 | 1 | 33.3% (6.1%–79.2%) | 0.71 | 0.634 | ➖ EXCLUDED |
| Non-binary × White | 18 | 6 | 33.3% (16.3%–56.3%) | 0.71 | 0.249 | ➖ EXCLUDED |
| Non-binary × Hispanic or Latino | 5 | 1 | 20.0% (3.6%–62.4%) | 0.42 | 0.227 | ➖ EXCLUDED |
| Female × Native American | 8 | 1 | 12.5% (2.2%–47.1%) | 0.27 | 0.051 | ➖ EXCLUDED |
| Non-binary × Black | 10 | 0 | 0.0% (0.0%–27.8%) | 0.00 | 0.003 | ➖ EXCLUDED |

_Impact ratios below 0.80 indicate potential adverse impact (four-fifths rule)._
