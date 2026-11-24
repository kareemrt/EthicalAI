"""Generate a synthetic resume-screening log with a known, injected bias.

The fictional screener scores 2,400 applicants 0-100 and advances anyone
scoring 60+. A hidden penalty is applied to some groups so the audit has
something real to find. Seeded, so the output is reproducible.

    python examples/make_hiring_data.py > examples/hiring.csv
"""

import csv
import random
import sys

RACES = [  # (category, population share, hidden score penalty)
    ("White", 0.46, 0),
    ("Hispanic or Latino", 0.19, 6),
    ("Black or African American", 0.14, 9),
    ("Asian", 0.13, 0),
    ("Two or More Races", 0.05, 3),
    ("Native American or Alaska Native", 0.02, 4),
    ("Native Hawaiian or Pacific Islander", 0.01, 0),
]
SEXES = [("Male", 0.50, 0), ("Female", 0.47, 4), ("", 0.03, 0)]  # "" = undisclosed


def pick(rng: random.Random, options):
    return rng.choices(options, weights=[w for _, w, _ in options])[0]


def main(n: int = 2400, seed: int = 7) -> None:
    rng = random.Random(seed)
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["applicant_id", "sex", "race", "score", "advanced"])
    for i in range(1, n + 1):
        sex, _, sp = pick(rng, SEXES)
        race, _, rp = pick(rng, RACES)
        score = max(0, min(100, round(rng.gauss(62, 12) - sp - rp)))
        w.writerow([f"A{i:05d}", sex, race, score, "yes" if score >= 60 else "no"])


if __name__ == "__main__":
    main()
