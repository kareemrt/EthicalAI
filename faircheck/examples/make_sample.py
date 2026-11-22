"""Generate a synthetic résumé-screening dataset with a hidden proxy bias.

The fictional screening model never sees `sex` or `race`. It does, however,
penalise résumé "career gaps" and favour a short list of "target schools" —
two features that correlate with protected attributes. That is how most real
algorithmic discrimination happens: through proxies, not explicit rules.

Everything here is synthetic. Run:  python examples/make_sample.py
"""

import csv
import random
from pathlib import Path

SEED, N = 7, 3000
RACES = [  # EEO-1 categories with rough US labour-force shares
    ("White", 0.60), ("Hispanic or Latino", 0.18), ("Black or African American", 0.12),
    ("Asian", 0.07), ("Two or More Races", 0.02), ("Native American or Alaska Native", 0.01),
]
# Unequal historical access to "target schools" — the second proxy.
TARGET_SCHOOL_P = {"White": 0.30, "Asian": 0.34, "Two or More Races": 0.24,
                   "Hispanic or Latino": 0.15, "Black or African American": 0.14,
                   "Native American or Alaska Native": 0.12}


def applicant(rng: random.Random, i: int) -> dict:
    sex = rng.choices(["Female", "Male"], weights=[0.48, 0.52])[0]
    race = rng.choices([r for r, _ in RACES], weights=[w for _, w in RACES])[0]
    skill = rng.gauss(0, 1)                               # true ability: identical across groups
    gap = rng.random() < (0.32 if sex == "Female" else 0.10)  # caregiving gaps skew female
    school = rng.random() < TARGET_SCHOOL_P[race]

    # The "model": mostly skill, plus two proxy terms that carry no job signal.
    score = 60 + 12 * skill - 9 * gap + 7 * school + rng.gauss(0, 4)
    return {
        "applicant_id": f"A{i:05d}",
        "sex": sex,
        "race": race,
        "career_gap": int(gap),
        "target_school": int(school),
        "model_score": round(score, 1),
        "advanced": "yes" if score > 68 else "no",
        "qualified": "yes" if skill > 0.5 else "no",  # ground truth, known only in hindsight
    }


def main(path: Path = Path(__file__).with_name("screening_sample.csv")) -> None:
    rng = random.Random(SEED)
    rows = [applicant(rng, i) for i in range(N)]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} synthetic applicants to {path}")


if __name__ == "__main__":
    main()
