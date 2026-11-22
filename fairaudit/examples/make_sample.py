"""Generate a synthetic résumé-screening dataset with a hidden bias baked in.

The "tool" scores candidates on true qualification plus noise, but quietly
penalises applicants aged 50+ and those whose résumés mention a career gap
(which in this simulation correlates with sex). The audit should catch it.

    python examples/make_sample.py > examples/screening.csv
"""

import csv
import random
import sys

RACES = [("White", .58), ("Hispanic or Latino", .17), ("Black or African American", .12),
         ("Asian", .09), ("Two or More Races", .025), ("American Indian or Alaska Native", .01),
         ("Native Hawaiian or Pacific Islander", .005)]
AGES = [("Under 30", .30), ("30–49", .50), ("50+", .20)]


def pick(rng, options):
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def main(n=4000, seed=1):
    rng = random.Random(seed)
    out = csv.writer(sys.stdout)
    out.writerow(["applicant_id", "sex", "race", "age_band", "qualified", "score", "advanced"])
    for i in range(n):
        sex = rng.choices(["Female", "Male"], weights=[.48, .52])[0]
        race, age = pick(rng, RACES), pick(rng, AGES)
        qualified = rng.random() < 0.45
        career_gap = rng.random() < (0.30 if sex == "Female" else 0.08)
        score = 60 + 18 * qualified + rng.gauss(0, 9)
        score -= 9 * career_gap + 8 * (age == "50+")          # the hidden bias
        score = max(0, min(100, round(score, 1)))
        out.writerow([f"A{i:05d}", sex, race, age, "yes" if qualified else "no", score,
                      "yes" if score >= 70 else "no"])


if __name__ == "__main__":
    main()
