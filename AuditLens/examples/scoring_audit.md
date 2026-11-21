# Resume Screener — Scoring Audit

**Verdict: ADVERSE IMPACT DETECTED**  
Generated 2026-11-21 by AuditLens · mode: `scoring` · outcome column: `score`

| Records | Overall rate | Threshold | Significance (α) | Min. group share | Min. group size |
|---:|---:|---:|---:|---:|---:|
| 6,000 | 49.8% | 0.8 | 0.05 | 2% | 30 |

Scoring rate = share of a category scoring above the sample median score (**66.9**).

## Sex

| Category | Applicants | Selected | Scoring rate (95% CI) | Impact ratio (95% CI) | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Non-binary | 77 | 41 | 53.2% (42.2%–64.0%) | 1.007 (0.81–1.25) | 0.948 | ⚪ excluded (<2% of sample) |
| Male | 2,909 | 1,538 | 52.9% (51.1%–54.7%) | 1.000 | — | 🔵 reference |
| Female | 2,894 | 1,336 | 46.2% (44.4%–48.0%) | 0.873 (0.83–0.92) | <0.001 | 🟢 ok |

Unknown / not disclosed: **120**

## Race/Ethnicity

| Category | Applicants | Selected | Scoring rate (95% CI) | Impact ratio (95% CI) | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Two or More Races | 257 | 151 | 58.8% (52.7%–64.6%) | 1.000 | — | 🔵 reference |
| Native American or Alaska Native | 68 | 39 | 57.4% (45.5%–68.4%) | 0.976 (0.78–1.23) | 0.835 | ⚪ excluded (<2% of sample) |
| Asian | 950 | 498 | 52.4% (49.2%–55.6%) | 0.892 (0.79–1.00) | 0.071 | 🟢 ok |
| White | 2,381 | 1,229 | 51.6% (49.6%–53.6%) | 0.879 (0.79–0.98) | 0.030 | 🟢 ok |
| Hispanic or Latino | 1,156 | 536 | 46.4% (43.5%–49.2%) | 0.789 (0.70–0.89) | <0.001 | 🔴 adverse impact |
| Black or African American | 1,076 | 467 | 43.4% (40.5%–46.4%) | 0.739 (0.65–0.84) | <0.001 | 🔴 adverse impact |

Unknown / not disclosed: **112**

## Age

| Category | Applicants | Selected | Scoring rate (95% CI) | Impact ratio (95% CI) | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Under 40 | 4,091 | 2,169 | 53.0% (51.5%–54.5%) | 1.000 | — | 🔵 reference |
| 40 and over | 1,909 | 817 | 42.8% (40.6%–45.0%) | 0.807 (0.76–0.86) | <0.001 | 🟢 ok |

Unknown / not disclosed: **0**

## Sex × Race/Ethnicity

| Category | Applicants | Selected | Scoring rate (95% CI) | Impact ratio (95% CI) | p-value | Status |
|---|---:|---:|---:|---:|---:|---|
| Non-binary × Two or More Races | <5 | <5 | 100.0% (51.0%–100.0%) | 1.724 (1.49–1.99) | 0.092 | ⚪ excluded (<2% of sample) |
| Male × Native American or Alaska Native | 31 | 21 | 67.7% (50.1%–81.4%) | 1.168 (0.88–1.55) | 0.320 | ⚪ excluded (<2% of sample) |
| Non-binary × White | 32 | 21 | 65.6% (48.3%–79.6%) | 1.131 (0.85–1.51) | 0.432 | ⚪ excluded (<2% of sample) |
| Male × Two or More Races | 131 | 76 | 58.0% (49.5%–66.1%) | 1.000 | — | 🔵 reference |
| Female × Two or More Races | 116 | 66 | 56.9% (47.8%–65.5%) | 0.981 (0.79–1.22) | 0.859 | 🟢 ok |
| Male × Asian | 440 | 246 | 55.9% (51.2%–60.5%) | 0.964 (0.81–1.14) | 0.670 | 🟢 ok |
| Male × White | 1,163 | 639 | 54.9% (52.1%–57.8%) | 0.947 (0.81–1.11) | 0.503 | 🟢 ok |
| Male × Hispanic or Latino | 554 | 271 | 48.9% (44.8%–53.1%) | 0.843 (0.71–1.00) | 0.061 | 🟢 ok |
| Female × Asian | 479 | 233 | 48.6% (44.2%–53.1%) | 0.838 (0.71–1.00) | 0.057 | 🟢 ok |
| Female × White | 1,131 | 537 | 47.5% (44.6%–50.4%) | 0.818 (0.70–0.96) | 0.022 | 🟢 ok |
| Female × Native American or Alaska Native | 36 | 17 | 47.2% (32.0%–63.0%) | 0.814 (0.56–1.18) | 0.248 | ⚪ excluded (<2% of sample) |
| Male × Black or African American | 532 | 245 | 46.1% (41.9%–50.3%) | 0.794 (0.67–0.94) | 0.014 | 🔴 adverse impact |
| Female × Hispanic or Latino | 567 | 247 | 43.6% (39.5%–47.7%) | 0.751 (0.63–0.89) | 0.003 | 🔴 adverse impact |
| Non-binary × Hispanic or Latino | 14 | 6 | 42.9% (21.4%–67.4%) | 0.739 (0.40–1.38) | 0.277 | ⚪ excluded (<2% of sample) |
| Female × Black or African American | 515 | 212 | 41.2% (37.0%–45.5%) | 0.710 (0.59–0.85) | <0.001 | 🔴 adverse impact |
| Non-binary × Asian | 10 | <5 | 40.0% (16.8%–68.7%) | 0.689 (0.32–1.49) | 0.268 | ⚪ excluded (<2% of sample) |
| Non-binary × Black or African American | 16 | 5 | 31.2% (14.2%–55.6%) | 0.539 (0.26–1.13) | 0.042 | ⚪ excluded (<2% of sample) |

Unknown / not disclosed: **229**

## Drift over time (lowest impact ratio per period)

| Dimension | 2026-Q1 | 2026-Q2 | 2026-Q3 | 2026-Q4 |
|---|---:|---:|---:|---:|
| Sex | 0.969 | 0.880 | 0.859 | 0.788 ⚠️ |
| Race/Ethnicity | 0.779 ⚠️ | 0.765 ⚠️ | 0.635 ⚠️ | 0.691 ⚠️ |
| Age | 0.865 | 0.759 ⚠️ | 0.789 ⚠️ | 0.821 |
| Sex × Race/Ethnicity | 0.665 ⚠️ | 0.737 ⚠️ | 0.682 ⚠️ | 0.578 ⚠️ |

## Warnings

- Sex: 120 record(s) (2.0%) have an unknown category and are excluded from this dimension.
- Race/Ethnicity: 112 record(s) (1.9%) have an unknown category and are excluded from this dimension.
- Sex × Race/Ethnicity: 229 record(s) (3.8%) have an unknown category and are excluded from this dimension.

## How to read this report

- **Scoring rate**: share of a category that received a favourable outcome.
- **Impact ratio**: a category's rate divided by the rate of the most-favoured category (the *reference*).
- 🔴 **adverse impact**: impact ratio below 0.8 *and* statistically significant (p < 0.05).
- 🟠 **below threshold (not significant)**: under 0.8 but could plausibly be noise; monitor closely.
- ⚪ **insufficient data / excluded**: fewer than 30 records or under 2% of the sample.
- A clean audit is necessary, **not sufficient**, evidence of fairness. Review job-relatedness, proxies and accessibility too.
