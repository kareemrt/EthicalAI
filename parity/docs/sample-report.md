# Bias audit — Résumé screen (synthetic)

*4,000 records · selection rate of 'advanced' · threshold 80% · generated 2026-11-22*

**Overall verdict: FAIL**

## sex

| | Group | n | Selected | Rate | Impact ratio | p-value |
|---|---|--:|--:|--:|--:|--:|
| ★ | Nonbinary | 124 | 42 | 33.9% | 1.00 | — |
| ✓ | Male | 1,995 | 675 | 33.8% | 1.00 | — |
| ✗ | Female | 1,881 | 495 | 26.3% | 0.78 | <0.001 |

## race_ethnicity

| | Group | n | Selected | Rate | Impact ratio | p-value |
|---|---|--:|--:|--:|--:|--:|
| ★ | White | 2,287 | 826 | 36.1% | 1.00 | — |
| ✓ | Asian | 345 | 121 | 35.1% | 0.97 | — |
| ✗ | Hispanic | 717 | 147 | 20.5% | 0.57 | <0.001 |
| ✗ | Black | 521 | 69 | 13.2% | 0.37 | <0.001 |

*2 group(s) under the minimum share were excluded: Native American (n=62), Pacific Islander (n=68)*

## sex × race_ethnicity

| | Group | n | Selected | Rate | Impact ratio | p-value |
|---|---|--:|--:|--:|--:|--:|
| ★ | Male × White | 1,135 | 451 | 39.7% | 1.00 | — |
| ✓ | Male × Asian | 177 | 70 | 39.5% | 1.00 | — |
| ✓ | Female × White | 1,078 | 347 | 32.2% | 0.81 | — |
| △ | Female × Asian | 154 | 47 | 30.5% | 0.77 | 0.874 |
| ✗ | Male × Hispanic | 346 | 83 | 24.0% | 0.60 | 0.011 |
| ✗ | Female × Hispanic | 351 | 58 | 16.5% | 0.42 | <0.001 |
| ✗ | Male × Black | 266 | 43 | 16.2% | 0.41 | <0.001 |
| ✗ | Female × Black | 243 | 24 | 9.9% | 0.25 | <0.001 |

*10 group(s) under the minimum share were excluded: Nonbinary × Hispanic (n=20), Female × Native American (n=28), Male × Native American (n=32), Nonbinary × Native American (n=2), Male × Pacific Islander (n=39), Nonbinary × White (n=74), Nonbinary × Pacific Islander (n=2), Nonbinary × Black (n=12), Female × Pacific Islander (n=27), Nonbinary × Asian (n=14)*

## Proxy features

Features that encode a protected attribute can reintroduce bias even when that attribute is removed.

| Feature | Encodes | Cramér's V | Level |
|---|---|--:|---|
| zip_code | race_ethnicity | 0.38 | strong |
| employment_gap_months | sex | 0.23 | moderate |

---
★ reference · ✓ pass · △ below threshold, not significant · ✗ below threshold and significant
