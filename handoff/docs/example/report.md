# handoff audit report

**4000 predictions** · target accuracy for automated decisions **95.0%** · result **❌ FAIL**

| Accuracy | Mean confidence | ECE | MCE | Brier |
|---|---|---|---|---|
| 85.1% | 95.3% | 10.2% | 25.3% | 0.119 |

## Findings

- `FAIL` Miscalibrated: ECE 10.2% > 5.0%. The model is overconfident (says 95.3%, is right 85.1%).
- `FIX ` Platt scaling (a=0.59, b=-0.63) cuts held-out ECE 10.2% -> 1.4%. Apply it before trusting raw scores.
- `PLAN` Automate when confidence >= 0.995: the AI decides 45.4% of cases at 96.0% accuracy (>= 95.0% with 95% confidence); 54.6% go to a human.
- `FAIL` Calibration gap between groups: 'V-VI' ECE 16.8% vs 'I-II' 8.2%. Its confidence scores mean less.
- `FAIL` Group 'V-VI': automated accuracy 93.2% (n=118) is below the 95.0% target. One global threshold does not protect this group.
- `NOTE` 'V-VI' cases go to a human 1.8x as often as 'I-II' (79.9% vs 45.2%). Staff review queues accordingly.

## By group

| Group | n | Accuracy | Confidence | ECE | Sent to human | Automated accuracy |
|---|---:|---:|---:|---:|---:|---:|
| I-II | 1822 | 88.7% | 96.9% | 8.2% | 45.2% | 96.1% |
| III-IV | 1592 | 85.8% | 96.0% | 10.2% | 56.1% | 96.4% |
| V-VI | 586 | 71.8% | 88.6% | 16.8% | 79.9% | 93.2% |

## Charts

![reliability.svg](reliability.svg)
![coverage.svg](coverage.svg)
![groups.svg](groups.svg)

## Reliability table

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---:|---:|---:|---:|
| 0.5–0.6 | 135 | 51.8% | 34.8% | +17.0 pts |
| 0.6–0.7 | 54 | 65.2% | 44.4% | +20.7 pts |
| 0.7–0.8 | 97 | 75.8% | 50.5% | +25.3 pts |
| 0.8–0.9 | 204 | 85.6% | 63.2% | +22.4 pts |
| 0.9–1.0 | 3510 | 98.5% | 89.9% | +8.7 pts |
