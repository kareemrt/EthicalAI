"""Generate a synthetic hiring dataset with a known, deliberate bias.

The bias is planted so the audit has something to find:
  * the screening model under-scores women and Hispanic/Latino applicants
  * qualification (ground truth) is independent of demographics

Run:  python examples/generate_sample.py > examples/hiring_sample.csv
"""

import csv
import random
import sys

SEX = [("Male", 0.52), ("Female", 0.46), ("Nonbinary", 0.02)]
RACE = [("White", 0.45), ("Black", 0.18), ("Hispanic/Latino", 0.20), ("Asian", 0.14),
        ("Native American", 0.01), ("", 0.02)]
PENALTY = {"Female": 6, "Hispanic/Latino": 7, "Black": 2}   # points shaved off by the "model"


def pick(rng, options):
    return rng.choices([o for o, _ in options], [w for _, w in options])[0]


def main(n=2400, seed=7):
    rng = random.Random(seed)
    w = csv.writer(sys.stdout)
    w.writerow(["applicant_id", "sex", "race_ethnicity", "score", "advanced", "qualified"])
    for i in range(1, n + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        skill = rng.gauss(60, 12)
        qualified = skill > 62
        score = skill + rng.gauss(0, 6) - PENALTY.get(sex, 0) - PENALTY.get(race, 0)
        w.writerow([f"A{i:05d}", sex, race, round(score, 1), "yes" if score > 64 else "no",
                    "yes" if qualified else "no"])


if __name__ == "__main__":
    main()
