"""Generate a synthetic résumé-screening log with a known, injected bias.

The "AI screener" below scores candidates on genuine skill, but it has also
learned two proxies that real systems have been caught using: penalising
career gaps (which fall disproportionately on women) and a zip-code signal
correlated with race. FairLens should find both — that's the point.

    python examples/generate_hiring.py            # writes examples/hiring.csv
"""

import csv
import random
from pathlib import Path

SEX = [("Male", 0.505), ("Female", 0.48), ("Non-binary", 0.015)]
RACE = [("White", 0.50), ("Hispanic or Latino", 0.17), ("Black or African American", 0.14),
        ("Asian", 0.12), ("Two or More Races", 0.035), ("American Indian", 0.015), ("", 0.02)]
ZIP_PENALTY = {"Black or African American": 0.55, "Hispanic or Latino": 0.35}


def pick(rng: random.Random, options):
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def generate(n: int = 2400, seed: int = 7):
    rng = random.Random(seed)
    for i in range(1, n + 1):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        skill = rng.gauss(0, 1)                                   # what *should* matter
        gap = rng.random() < (0.32 if sex == "Female" else 0.12)  # career gap
        score = skill - 0.6 * gap - ZIP_PENALTY.get(race, 0) * (rng.random() < 0.7)
        score += rng.gauss(0, 0.35)
        yield {
            "applicant_id": f"A{i:05d}",
            "sex": sex,
            "race_ethnicity": race,
            "qualified": "yes" if skill > 0.25 else "no",
            "ai_score": round(50 + 15 * score, 1),
            "advanced": "yes" if score > 0.3 else "no",
        }


if __name__ == "__main__":
    out = Path(__file__).with_name("hiring.csv")
    rows = list(generate())
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} rows → {out}")
