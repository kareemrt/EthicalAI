"""Generate a synthetic hiring-funnel dataset with a known, planted bias.

Each row is one applicant screened by a hypothetical résumé-scoring model.
The model's score carries a small penalty for some groups — the kind of
skew that creeps in when a model learns from historically biased hiring.
Because we planted it, we can check that Parity finds it.

    python examples/generate_sample.py > examples/applicants.csv
"""
import csv
import random
import sys

SEED = 1964  # the year Title VII of the Civil Rights Act was signed

SEX = [("Female", 0.47), ("Male", 0.50), ("", 0.03)]  # "" = not disclosed
RACE = [
    ("White", 0.52), ("Hispanic or Latino", 0.18), ("Black or African American", 0.13),
    ("Asian", 0.11), ("Two or More Races", 0.035),
    ("Native Hawaiian or Pacific Islander", 0.008), ("American Indian or Alaska Native", 0.012),
    ("", 0.005),
]
# Planted score penalties (points on a 0–100 scale).
PENALTY = {"Female": 3.0, "Black or African American": 5.0, "Hispanic or Latino": 2.0}
CUTOFF = 66  # applicants scoring above this advance to interview


def pick(rng, options):
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def main(n: int = 2400) -> None:
    rng = random.Random(SEED)
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["applicant_id", "sex", "race", "score", "advanced"])
    for i in range(1, n + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        score = rng.gauss(64, 11) - PENALTY.get(sex, 0) - PENALTY.get(race, 0)
        score = max(0.0, min(100.0, score))
        out.writerow([f"A{i:05d}", sex, race, f"{score:.1f}", "yes" if score > CUTOFF else "no"])


if __name__ == "__main__":
    main()
