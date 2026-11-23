"""Generate a synthetic résumé-screening dataset with a hidden bias baked in.

The "AI screener" gives every applicant a score from job-relevant skill plus a
small penalty that leaks through proxy features (e.g. résumé gaps, zip code).
No real people are represented. Re-run to regenerate examples/hiring.csv:

    python examples/generate_hiring_data.py
"""

import csv
import random
from pathlib import Path

SEED, N = 7, 1500
SEX = [("Female", 0.48), ("Male", 0.50), ("", 0.02)]  # "" = declined to answer
RACE = [("White", 0.46), ("Black", 0.18), ("Hispanic or Latino", 0.18), ("Asian", 0.14),
        ("Native American", 0.012), ("", 0.028)]
# Proxy penalty the screener learned from historical data (in score points).
PENALTY = {"Female": 4, "Black": 7, "Hispanic or Latino": 3, "Native American": 5}


def pick(rng: random.Random, options):
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def main() -> None:
    rng = random.Random(SEED)
    rows = []
    for i in range(1, N + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        skill = rng.gauss(60, 12)                       # identical across groups
        score = skill - PENALTY.get(sex, 0) - PENALTY.get(race, 0) + rng.gauss(0, 4)
        score = max(0, min(100, round(score, 1)))
        rows.append({"applicant_id": f"A{i:04d}", "sex": sex, "race": race,
                     "ai_score": score, "advanced": "yes" if score >= 62 else "no"})

    out = Path(__file__).with_name("hiring.csv")
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows → {out}")


if __name__ == "__main__":
    main()
