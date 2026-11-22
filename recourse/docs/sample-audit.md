# Recourse audit: Example credit scorecard

600 records, grouped by `group`. *Effort* is the minimum total cost of changes that would flip a decline into an approval under the model's action policy.

| group | n | declined | median effort | no recourse | locked penalty |
|---|---|---|---|---|---|
| Group A | 300 | 72 (24%) | 1.14 | 0 (0%) | -0.49 |
| Group B | 300 | 153 (51%) | 1.62 | 17 (11%) | -0.75 |

## Findings

- ⚠ 17 of 225 declined people (8%) have no achievable path to approval.
- ⚠ Recourse burden ratio 1.42: 'Group B' needs a median 1.62 effort points vs 1.14 for 'Group A'.
- ⚠ No-recourse ratio ∞: 11% of declined 'Group B' are stuck vs 0% of 'Group A'.
- · Fixed feature 'Missed payments (24 mo)' carries weight -0.55 — only ages out with time.
- · Fixed feature 'Credit history' carries weight +0.06 — only grows with time.
- · Fixed feature 'Area risk index' carries weight -2 — set by home postcode; a likely geographic proxy for race and income.
