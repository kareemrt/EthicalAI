"""Generate a synthetic applicant dataset with a realistic, *hidden* bias.

The screening model never sees race or sex. It does see "employment gap" and
"zip-code tier" — proxies that correlate with protected groups. That is how
most real-world algorithmic discrimination happens, and why outcome audits
matter more than inspecting a model's inputs.

    python examples/generate_sample.py > examples/applicants.csv
"""

import csv
import random
import sys

random.seed(1978)  # the year of the EEOC Uniform Guidelines

SEX = [("Female", 0.47), ("Male", 0.50), ("Non-binary", 0.03)]
RACE = [("White", 0.52), ("Black", 0.16), ("Hispanic", 0.19), ("Asian", 0.11), ("Native American", 0.02)]
GAP_RISK = {"Female": 0.30, "Male": 0.10, "Non-binary": 0.18}       # caregiving gaps
ZIP_PENALTY = {"White": 0.0, "Asian": 0.02, "Hispanic": 0.08, "Black": 0.12, "Native American": 0.10}


def pick(options):
    return random.choices([o for o, _ in options], [w for _, w in options])[0]


def main(n=2400):
    w = csv.writer(sys.stdout)
    w.writerow(["applicant_id", "sex", "race", "years_experience", "employment_gap", "score", "qualified", "advanced"])
    for i in range(1, n + 1):
        sex, race = pick(SEX), pick(RACE)
        skill = random.gauss(0.6, 0.15)                          # true ability: identical across groups
        years = max(0, round(random.gauss(6, 3)))
        gap = random.random() < GAP_RISK[sex]
        # The model's score: skill + noise, minus proxy penalties it learned from past hires.
        score = skill + random.gauss(0, 0.07) - (0.08 if gap else 0) - ZIP_PENALTY[race]
        score = round(min(max(score, 0), 1), 3)
        w.writerow([f"A{i:05d}", sex, race, years, int(gap), score, int(skill >= 0.62), int(score >= 0.58)])


if __name__ == "__main__":
    main()
