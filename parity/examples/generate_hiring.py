"""Generate a synthetic résumé-screening dataset with realistic, *indirect* bias.

The simulated screening model never sees sex or race. It penalises employment
gaps and favours certain ZIP codes — features that correlate with sex (caregiving
leave) and race (residential segregation). Parity should catch both the disparate
outcomes and the proxies that cause them.

    python examples/generate_hiring.py > examples/hiring.csv
"""

import csv
import random
import sys

rng = random.Random(7)

RACES = [("White", .58), ("Black", .14), ("Hispanic", .17), ("Asian", .08),
         ("Native American", .015), ("Pacific Islander", .015)]
# ZIP codes with different demographic mixes (segregation → proxy)
ZIPS = {"White": [("10583", .5), ("11375", .3), ("10457", .1), ("11212", .1)],
        "Black": [("11212", .55), ("10457", .25), ("11375", .1), ("10583", .1)],
        "Hispanic": [("10457", .55), ("11212", .2), ("11375", .15), ("10583", .1)],
        "Asian": [("11375", .5), ("10583", .3), ("10457", .1), ("11212", .1)]}
ZIP_BONUS = {"10583": 6, "11375": 3, "10457": -3, "11212": -4}


def pick(options):
    return rng.choices([o for o, _ in options], [w for _, w in options])[0]


def applicant(i):
    sex = rng.choices(["Female", "Male", "Nonbinary"], [.48, .49, .03])[0]
    race = pick(RACES)
    age = rng.choices(["18-29", "30-44", "45-59", "60+"], [.3, .4, .22, .08])[0]
    zip_code = pick(ZIPS.get(race, ZIPS["White"]))
    exp = max(0, round(rng.gauss({"18-29": 3, "30-44": 10, "45-59": 18, "60+": 24}[age], 3)))
    gap_rate = .38 if sex == "Female" else .12
    gap = rng.choice([6, 12, 18, 24, 36]) if rng.random() < gap_rate else 0
    tier = rng.choices(["1", "2", "3"], [.2, .45, .35])[0]
    # The "model": legitimate signal + proxy penalties + noise. No protected inputs.
    score = (50 + 0.5 * min(exp, 15) + {"1": 8, "2": 3, "3": 0}[tier]
             + ZIP_BONUS[zip_code] - 0.9 * gap + rng.gauss(0, 7))
    return {"applicant_id": f"A{i:05d}", "sex": sex, "race_ethnicity": race, "age_band": age,
            "zip_code": zip_code, "years_experience": exp, "employment_gap_months": gap,
            "college_tier": tier, "score": round(score, 1)}


rows = [applicant(i) for i in range(4000)]
cutoff = sorted(r["score"] for r in rows)[int(len(rows) * .7)]  # top 30% advance
for r in rows:
    r["advanced"] = int(r["score"] >= cutoff)

w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]), lineterminator="\n")
w.writeheader()
w.writerows(rows)
