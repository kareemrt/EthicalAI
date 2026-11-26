"""Generate a synthetic resume-screening dataset with a known, planted bias.

The screening model scores applicants on a latent 'merit' plus noise, but
penalises one group by a few points — the kind of skew a proxy feature
(e.g. employment gaps, zip code, name) quietly introduces. fairscope should
catch it. Deterministic: same seed, same file.

    python examples/make_sample.py > examples/screening.csv
"""

import csv
import random
import sys

rng = random.Random(7)
GENDER = [("Female", 0.47), ("Male", 0.49), ("Non-binary", 0.04)]
RACE = [("White", 0.52), ("Black", 0.18), ("Hispanic", 0.17), ("Asian", 0.11), ("Two or more", 0.015),
        ("Native American", 0.005)]
PENALTY = {"Black": 6.0, "Hispanic": 3.5}          # the planted bias, in score points


def pick(options):
    return rng.choices([o for o, _ in options], [w for _, w in options])[0]


w = csv.writer(sys.stdout)
w.writerow(["applicant_id", "gender", "race", "score", "advanced", "qualified"])
for i in range(1, 2401):
    gender, race = pick(GENDER), pick(RACE)
    merit = rng.gauss(60, 12)
    qualified = merit > 62                          # ground truth: would succeed in the role
    score = merit + rng.gauss(0, 6) - PENALTY.get(race, 0) - (2.0 if gender == "Female" else 0)
    advanced = score > 64                           # screening decision
    w.writerow([f"A{i:05d}", gender, race, round(score, 1), "yes" if advanced else "no",
                "yes" if qualified else "no"])
