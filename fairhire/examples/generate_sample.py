"""Generate a synthetic applicant pool screened by a (deliberately) biased model.

Nothing here is real data. The "screener" adds a hidden penalty for some
groups — the kind of proxy bias that creeps in when a model learns from
historical hiring — so the audit has something to find.

    python examples/generate_sample.py > examples/applicants.csv
"""

import csv
import random
import sys

SEED, N = 7, 2000
SEX = [("Female", .48), ("Male", .48), ("Non-binary", .015), ("", .025)]
RACE = [("White", .48), ("Hispanic or Latino", .19), ("Black or African American", .14),
        ("Asian", .12), ("Two or more races", .05), ("Native American", .01), ("", .01)]
# Hidden penalty (in score points) the biased screener applies.
PENALTY = {"Female": 4, "Black or African American": 7, "Hispanic or Latino": 3}


def pick(rng, options):
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def main():
    rng = random.Random(SEED)
    out = csv.writer(sys.stdout)
    out.writerow(["applicant_id", "sex", "race", "score", "advanced"])
    for i in range(1, N + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        score = rng.gauss(70, 10) - PENALTY.get(sex, 0) - PENALTY.get(race, 0)
        score = max(0, min(100, score))
        out.writerow([f"A{i:05d}", sex, race, f"{score:.1f}", int(score >= 72)])


if __name__ == "__main__":
    main()
