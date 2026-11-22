"""Generate a synthetic applicant log for demos and tests.

The data is fictional. A bias is planted on purpose: a resume-screening model
that under-scores applicants with employment gaps — a pattern that falls
hardest on women (caregiving) and older applicants. FairHire should catch it.

    python examples/generate_sample.py > examples/applicants.csv
"""

import csv
import random
import sys

random.seed(144)

SEX = [("Female", 0.48), ("Male", 0.49), ("", 0.03)]
RACE = [("White", 0.42), ("Black", 0.18), ("Hispanic or Latino", 0.2), ("Asian", 0.14),
        ("Two or more races", 0.04), ("Native Hawaiian or Pacific Islander", 0.01), ("", 0.01)]
AGE = [("Under 40", 0.62), ("40 and over", 0.38)]


def pick(options):
    return random.choices([o for o, _ in options], weights=[w for _, w in options])[0]


w = csv.writer(sys.stdout)
w.writerow(["applicant_id", "sex", "race_ethnicity", "age_band", "screen_score", "advanced"])
for i in range(1, 2001):
    sex, race, age = pick(SEX), pick(RACE), pick(AGE)
    gap_prob = 0.12 + (0.22 if sex == "Female" else 0) + (0.15 if age == "40 and over" else 0)
    score = random.gauss(68, 11) - (14 if random.random() < gap_prob else 0)
    score = round(max(0, min(100, score)), 1)
    w.writerow([f"A{i:05d}", sex, race, age, score, "yes" if score >= 66 else "no"])
