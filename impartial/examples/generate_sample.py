"""Generate a synthetic, deliberately biased hiring dataset for demos and tests.

Run:  python examples/generate_sample.py  (writes examples/hiring_sample.csv)

The data is fictional. Bias is injected on purpose so the audit has something
to find: the screening model under-scores some groups and the dataset contains
missing values and a tiny group, like real HR exports do.
"""

import csv
import random
from pathlib import Path

SEXES = [("Male", 0.52), ("Female", 0.46), ("Non-binary", 0.02)]
RACES = [("White", 0.45), ("Black", 0.18), ("Hispanic or Latino", 0.20), ("Asian", 0.14), ("Native American", 0.012)]
# Penalty (in score points) the hypothetical model applies to each group.
PENALTY = {"Female": 6, "Non-binary": 4, "Black": 9, "Hispanic or Latino": 4, "Native American": 5}


def pick(rng: random.Random, options):
    labels, weights = zip(*options)
    return rng.choices(labels, weights)[0]


def generate(n: int = 2400, seed: int = 7):
    rng = random.Random(seed)
    for i in range(1, n + 1):
        sex, race = pick(rng, SEXES), pick(rng, RACES)
        skill = rng.gauss(60, 12)  # true, group-independent qualification
        score = skill - PENALTY.get(sex, 0) - PENALTY.get(race, 0) + rng.gauss(0, 5)
        score = round(max(0, min(100, score)), 1)
        hired = int(score >= 62)
        if rng.random() < 0.03:
            race = ""  # applicant declined to self-identify
        yield {"applicant_id": f"A{i:05d}", "sex": sex, "race_ethnicity": race, "model_score": score, "hired": hired}


if __name__ == "__main__":
    out = Path(__file__).with_name("hiring_sample.csv")
    rows = list(generate())
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}")
