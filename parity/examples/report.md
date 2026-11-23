# Parity audit — `advanced`

| Records | Favourable rate | Mode | Threshold | Verdict |
|---:|---:|---|---:|---|
| 2,400 | 33.5% | selection | 0.80 | ⚠️ adverse impact found |

## Findings

- Female (sex) were selected at 75% the rate of Male — 28.4% vs 37.9%. The gap is statistically significant (p < 0.001).
- Black or African American (race) were selected at 63% the rate of White — 23.2% vs 37.0%. The gap is statistically significant (p < 0.001).
- Female · White (sex × race) were selected at 77% the rate of Male · White — 31.8% vs 41.4%. The gap is statistically significant (p < 0.001).
- Male · Black or African American (sex × race) were selected at 67% the rate of Male · White — 27.5% vs 41.4%. The gap is statistically significant (p < 0.001).
- Female · Asian (sex × race) were selected at 65% the rate of Male · White — 26.7% vs 41.4%. The gap is statistically significant (p = 0.005).
- Female · Hispanic or Latino (sex × race) were selected at 62% the rate of Male · White — 25.7% vs 41.4%. The gap is statistically significant (p < 0.001).
- Female · Black or African American (sex × race) were selected at 42% the rate of Male · White — 17.2% vs 41.4%. The gap is statistically significant (p < 0.001).
- Watch: Hispanic or Latino (race) pass the benchmark at 0.85, but the gap to White is statistically significant (p = 0.038).

### Data notes

- 59 record(s) had unknown sex and were left out of that dimension.
- 2 race group(s) under 2% of the sample were reported but not flagged: American Indian or Alaska Native, Native Hawaiian or Pacific Islander.
- 6 record(s) had unknown race and were left out of that dimension.
- 6 sex × race group(s) under 2% of the sample were reported but not flagged: Male · Native Hawaiian or Pacific Islander, Male · American Indian or Alaska Native, Female · Two or More Races, Female · American Indian or Alaska Native, Male · Two or More Races, Female · Native Hawaiian or Pacific Islander.
- 65 record(s) had unknown sex × race and were left out of that dimension.

## sex

| Group | n | Rate | Impact ratio | p-value | Verdict | Notes |
|---|---:|---:|---:|---:|---|---|
| Male | 1,188 | 37.9% | 1.00 | — | reference |  |
| Female | 1,153 | 28.4% | 0.75 | <0.001 | **ADVERSE** |  |

_Unknown sex: 59 record(s)._

## race

| Group | n | Rate | Impact ratio | p-value | Verdict | Notes |
|---|---:|---:|---:|---:|---|---|
| American Indian or Alaska Native | 29 | 44.8% | 1.21 | 0.388 | excluded (<min share) | low-n |
| White | 1,292 | 37.0% | 1.00 | — | reference |  |
| Two or More Races | 68 | 33.8% | 0.91 | 0.597 | ok |  |
| Asian | 231 | 32.5% | 0.88 | 0.187 | ok |  |
| Hispanic or Latino | 423 | 31.4% | 0.85 | 0.038 | ok |  |
| Native Hawaiian or Pacific Islander | 10 | 30.0% | 0.81 | 0.648 | excluded (<min share) | fragile, low-n |
| Black or African American | 341 | 23.2% | 0.63 | <0.001 | **ADVERSE** |  |

_Unknown race: 6 record(s)._

## sex × race

| Group | n | Rate | Impact ratio | p-value | Verdict | Notes |
|---|---:|---:|---:|---:|---|---|
| Male · Native Hawaiian or Pacific Islander | 4 | 50.0% | 1.21 | 0.728 | excluded (<min share) | fragile, low-n |
| Male · American Indian or Alaska Native | 13 | 46.2% | 1.12 | 0.730 | excluded (<min share) | low-n |
| Male · White | 633 | 41.4% | 1.00 | — | reference |  |
| Male · Asian | 126 | 38.1% | 0.92 | 0.492 | ok |  |
| Female · Two or More Races | 35 | 37.1% | 0.90 | 0.619 | excluded (<min share) |  |
| Male · Hispanic or Latino | 199 | 36.7% | 0.89 | 0.238 | ok |  |
| Female · American Indian or Alaska Native | 14 | 35.7% | 0.86 | 0.670 | excluded (<min share) | fragile, low-n |
| Female · White | 629 | 31.8% | 0.77 | <0.001 | **ADVERSE** |  |
| Male · Two or More Races | 32 | 31.2% | 0.76 | 0.255 | excluded (<min share) | fragile |
| Male · Black or African American | 178 | 27.5% | 0.67 | <0.001 | **ADVERSE** |  |
| Female · Asian | 101 | 26.7% | 0.65 | 0.005 | **ADVERSE** |  |
| Female · Hispanic or Latino | 214 | 25.7% | 0.62 | <0.001 | **ADVERSE** |  |
| Female · Black or African American | 151 | 17.2% | 0.42 | <0.001 | **ADVERSE** |  |
| Female · Native Hawaiian or Pacific Islander | 6 | 16.7% | 0.40 | 0.221 | excluded (<min share) | fragile, low-n |

_Unknown sex × race: 65 record(s)._

---
_The four-fifths rule is a screening heuristic, not proof of discrimination or of its absence. Significance uses a two-proportion z-test against the reference group. Results marked fragile flip if a single person's outcome changes; groups with fewer than 30 people are marked low-n. This tool does not replace an independent auditor or legal advice._
