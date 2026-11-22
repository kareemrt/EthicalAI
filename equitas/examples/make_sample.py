"""Generate a synthetic, reproducible hiring dataset with known, planted bias.

The screening model here is deliberately unfair so the audit has something to find:
  * applicants aged 40+ are penalised regardless of qualification
  * women who are also Black are penalised more than either group alone (intersectional)
No real people are represented.

    python examples/make_sample.py > examples/applicants.csv
"""
import csv
import random
import sys

rng = random.Random(42)
RACE = [("White", .52), ("Hispanic or Latino", .19), ("Black or African American", .14),
        ("Asian", .11), ("Two or More Races", .03), ("Native Hawaiian or Pacific Islander", .01)]


def pick(options):
    r, acc = rng.random(), 0.0
    for value, w in options:
        acc += w
        if r < acc:
            return value
    return options[-1][0]


w = csv.writer(sys.stdout)
w.writerow(["applicant_id", "sex", "race_ethnicity", "age_band", "qualified", "score", "advanced"])
for i in range(1, 3001):
    sex = pick([("Female", .48), ("Male", .49), ("", .03)])  # some applicants decline to answer
    race = pick(RACE)
    age = pick([("Under 40", .68), ("40 and over", .32)])
    qualified = rng.random() < 0.45
    score = rng.gauss(68 if qualified else 52, 9)
    score -= 7 if age == "40 and over" else 0                              # planted bias
    score -= 9 if (sex == "Female" and race == "Black or African American") else 0  # planted bias
    w.writerow([f"A{i:04d}", sex, race, age, int(qualified), round(score, 1), int(score > 62)])
