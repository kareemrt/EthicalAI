"""Generate a synthetic resume-screener dataset with a known, planted bias.

Every applicant is equally likely to be qualified regardless of group, but
the simulated screener penalises women and applicants aged 40+. Running
Parity on the output should surface exactly that -- a quick way to see
what a real finding looks like.

    python examples/generate.py > examples/hiring.csv
"""

import csv
import random
import sys

rng = random.Random(42)  # deterministic: same file every run

GENDER = [("Man", .48), ("Woman", .48), ("Non-binary", .04)]
AGE = [("Under 40", .62), ("40 and over", .38)]
PASS_IF_QUALIFIED = {"Man": .72, "Woman": .52, "Non-binary": .60}
AGE_PENALTY = {"Under 40": 0.0, "40 and over": .14}
PASS_IF_UNQUALIFIED = .12


def pick(options):
    return rng.choices([o for o, _ in options], [w for _, w in options])[0]


w = csv.writer(sys.stdout)
w.writerow(["applicant_id", "gender", "age_band", "qualified", "advanced"])
for i in range(1, 1601):
    g, a = pick(GENDER), pick(AGE)
    qualified = rng.random() < .45
    p = PASS_IF_QUALIFIED[g] - AGE_PENALTY[a] if qualified else PASS_IF_UNQUALIFIED
    w.writerow([f"A{i:04d}", g, a, int(qualified), "yes" if rng.random() < p else "no"])
