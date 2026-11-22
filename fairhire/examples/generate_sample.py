"""Generate a synthetic applicant dataset with a known, planted bias.

Run:  python examples/generate_sample.py > examples/applicants.csv

Nothing here is real data. The screening model below is deliberately unfair so
the audit has something to find: it penalises women and Black applicants and
was trained on too few Native Hawaiian / Pacific Islander examples to judge.
"""

import csv
import random
import sys

SEX = [("Male", 0.52), ("Female", 0.45), ("", 0.03)]  # "" = declined to state
RACE = [("White", 0.50), ("Hispanic or Latino", 0.18), ("Black or African American", 0.14),
        ("Asian", 0.12), ("Two or More Races", 0.04), ("Native Hawaiian or Pacific Islander", 0.015),
        ("", 0.005)]
PENALTY = {"Female": -6.0, "Black or African American": -9.0}  # planted bias, in score points


def pick(rng, table):
    return rng.choices([v for v, _ in table], [w for _, w in table])[0]


def main(n: int = 2000, seed: int = 7) -> None:
    rng = random.Random(seed)
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["applicant_id", "sex", "race", "score", "advanced"])
    for i in range(1, n + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        skill = rng.gauss(60, 12)                       # true, group-independent ability
        score = skill + PENALTY.get(sex, 0) + PENALTY.get(race, 0) + rng.gauss(0, 4)
        w.writerow([f"A{i:05d}", sex, race, round(score, 1), "yes" if score >= 63 else "no"])


if __name__ == "__main__":
    main()
