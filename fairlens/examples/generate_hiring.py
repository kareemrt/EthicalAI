"""Generate a synthetic résumé-screening dataset with a known, injected bias.

Scenario: an AI screener decides who advances to interview. `qualified` is the
ground truth from a structured human review. The screener was trained on
historical decisions, so it under-selects qualified women and older applicants.

    python examples/generate_hiring.py > examples/hiring.csv
"""
import csv
import random
import sys

rng = random.Random(42)
SEX = [("Male", 0.52), ("Female", 0.46), ("Non-binary", 0.02)]
RACE = [("White", 0.55), ("Black", 0.15), ("Hispanic", 0.18), ("Asian", 0.12)]
AGE = [("<40", 0.7), ("40+", 0.3)]
# Multiplier applied to a qualified applicant's chance of being advanced.
PENALTY = {"Female": 0.70, "Non-binary": 0.85, "40+": 0.75, "Black": 0.88}


def pick(options):
    return rng.choices([o for o, _ in options], [w for _, w in options])[0]


w = csv.writer(sys.stdout, lineterminator="\n")
w.writerow(["applicant_id", "sex", "race", "age_band", "qualified", "advanced"])
for i in range(1, 2001):
    sex, race, age = pick(SEX), pick(RACE), pick(AGE)
    qualified = rng.random() < 0.40
    p = 0.80 if qualified else 0.12
    for attr in (sex, race, age):
        p *= PENALTY.get(attr, 1.0)
    w.writerow([f"A{i:04d}", sex, race if rng.random() > 0.01 else "", age, int(qualified), int(rng.random() < p)])
