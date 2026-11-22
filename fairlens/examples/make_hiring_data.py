"""Generate a synthetic résumé-screening dataset with a known, planted bias.

Every applicant has a true `qualified` label drawn from the SAME distribution for all
groups. The screening model then under-selects some groups anyway, the way a model trained on
historically skewed hiring data would. FairLens should find exactly that.

    python examples/make_hiring_data.py > examples/hiring.csv
"""
import csv
import random
import sys

random.seed(144)  # NYC Local Law 144

GENDERS = [("Female", 0.47), ("Male", 0.49), ("Nonbinary", 0.04)]
RACES = [("White", 0.52), ("Black", 0.17), ("Hispanic", 0.18), ("Asian", 0.11), ("Native American", 0.02)]
AGE_BANDS = [("<40", 0.70), ("40+", 0.30)]

# Planted bias: score penalty applied by the "model" (not by true qualification).
PENALTY = {"Female": 6, "Black": 9, "Hispanic": 4, "40+": 5}


def pick(options):
    return random.choices([o for o, _ in options], [w for _, w in options])[0]


writer = csv.writer(sys.stdout)
writer.writerow(["applicant_id", "gender", "race", "age_band", "model_score", "advanced", "qualified"])
for i in range(1, 3001):
    gender, race, age = pick(GENDERS), pick(RACES), pick(AGE_BANDS)
    skill = random.gauss(60, 12)
    qualified = skill > 62
    score = skill + random.gauss(0, 6) - sum(PENALTY.get(a, 0) for a in (gender, race, age))
    score = max(0.0, min(100.0, score))
    writer.writerow([f"A{i:04d}", gender, race, age, f"{score:.1f}",
                     "yes" if score >= 60 else "no", int(qualified)])
