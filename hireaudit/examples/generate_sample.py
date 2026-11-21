"""Generate a synthetic applicant dataset for a fictional AI resume screener.

The screener scores applicants 0-100 and advances anyone scoring >= 70.
A hidden penalty is injected for some groups so the audit has something to
find. No real people are represented. Re-run to reproduce (seeded).

    python examples/generate_sample.py > examples/applicants.csv
"""
import csv
import random
import sys

SEED, N, CUTOFF = 7, 4000, 70

SEX = {"Female": 0.47, "Male": 0.49, "": 0.04}            # "" = not disclosed
RACE = {"White": 0.44, "Asian": 0.18, "Hispanic or Latino": 0.16,
        "Black or African American": 0.13, "Two or More Races": 0.035,
        "Native American or Alaska Native": 0.012, "Declined": 0.043}

# Hidden score penalties: the "bias" the audit should surface.
PENALTY = {"Female": 3.0, "Black or African American": 5.5, "Hispanic or Latino": 2.0}


def pick(rng, weights):
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def main(out=sys.stdout):
    rng = random.Random(SEED)
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["applicant_id", "sex", "race_ethnicity", "score", "advanced"])
    for i in range(1, N + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        score = rng.gauss(64, 11) - PENALTY.get(sex, 0) - PENALTY.get(race, 0)
        score = round(min(100, max(0, score)), 1)
        w.writerow([f"A{i:05d}", sex, race, score, "yes" if score >= CUTOFF else "no"])


if __name__ == "__main__":
    main()
