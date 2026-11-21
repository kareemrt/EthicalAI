"""Generate a synthetic resume-screening log with a realistic, hidden bias.

The "model" never sees sex or race. It scores candidates on skills, plus two
features that look neutral but act as proxies — exactly how real tools go wrong:

  * career_gap   → penalised; gaps are more common among women (caregiving)
  * zip_prestige → rewarded; correlated with race through residential segregation

Run:  python examples/generate.py > examples/hiring.csv
All people in this file are fictional. Seeded, so output is reproducible.
"""

import csv
import random
import sys

RACES = [("White", .55), ("Hispanic or Latino", .17), ("Black or African American", .14),
         ("Asian", .10), ("Two or More Races", .025),
         ("Native American or Alaska Native", .01), ("Native Hawaiian or Pacific Islander", .005)]
ZIP_BIAS = {"White": .65, "Asian": .62, "Two or More Races": .5, "Hispanic or Latino": .36,
            "Black or African American": .32, "Native American or Alaska Native": .35,
            "Native Hawaiian or Pacific Islander": .4}


def pick(rng, weighted):
    r, acc = rng.random(), 0.0
    for value, w in weighted:
        acc += w
        if r < acc:
            return value
    return weighted[-1][0]


def candidate(rng, i):
    sex = pick(rng, [("Female", .48), ("Male", .49), ("Unknown", .03)])
    race = pick(rng, RACES)
    skills = rng.gauss(60, 12)                       # identically distributed for everyone
    gap = rng.random() < (.32 if sex == "Female" else .12)
    zip_prestige = rng.random() < ZIP_BIAS[race]
    score = skills - 9 * gap + 7 * zip_prestige + rng.gauss(0, 5)
    if rng.random() < .02:
        race = ""                                    # applicant declined to self-identify
    return {"applicant_id": f"A{i:05d}", "sex": sex, "race": race,
            "score": round(max(0, min(100, score)), 1), "advanced": int(score >= 66)}


def main(n=4000, seed=7):
    rng = random.Random(seed)
    w = csv.DictWriter(sys.stdout, fieldnames=["applicant_id", "sex", "race", "score", "advanced"])
    w.writeheader()
    for i in range(n):
        w.writerow(candidate(rng, i))


if __name__ == "__main__":
    main()
