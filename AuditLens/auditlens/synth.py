"""Synthetic applicant data with a realistic, *hidden* bias -- for demos and tests.

The simulated screening model never sees sex or race. It does, however, penalise
three seemingly neutral features:

* ``employment_gap`` -- career breaks, which are far more common among women
  (caregiving),
* ``commute_zone``  -- a location score that, because of residential
  segregation, acts as a proxy for race, and
* ``years_experience`` above 11 -- an "over-qualified" penalty that acts as a
  proxy for age.

The penalty on the gap feature grows each quarter, mimicking a model that is
retrained on its own biased decisions (a feedback loop). This is exactly the
kind of "fairness through unawareness" failure AuditLens is designed to catch.
"""

from __future__ import annotations

import csv
import random
from typing import Dict, List

SEX = [("Female", 0.48), ("Male", 0.485), ("Non-binary", 0.015), ("", 0.02)]
RACE = [
    ("White", 0.40),
    ("Hispanic or Latino", 0.20),
    ("Black or African American", 0.18),
    ("Asian", 0.15),
    ("Two or More Races", 0.04),
    ("Native American or Alaska Native", 0.012),
    ("", 0.018),
]
AGE = [("Under 40", 0.68), ("40 and over", 0.32)]
QUARTERS = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]
FIELDS = ["applicant_id", "quarter", "sex", "race_ethnicity", "age_band",
          "years_experience", "employment_gap", "commute_zone", "score", "advanced"]


def _pick(rng: random.Random, options) -> str:
    r, acc = rng.random(), 0.0
    for value, p in options:
        acc += p
        if r < acc:
            return value
    return options[-1][0]


def generate(n: int = 6000, seed: int = 7, selection_rate: float = 0.30) -> List[Dict[str, str]]:
    rng = random.Random(seed)
    people = []
    for i in range(n):
        q = i * len(QUARTERS) // n
        sex, race, age = _pick(rng, SEX), _pick(rng, RACE), _pick(rng, AGE)
        exp = max(0.0, rng.gauss(14 if age == "40 and over" else 6, 3.5))
        gap_p = 0.38 if sex == "Female" else 0.12
        gap = rng.random() < gap_p
        far_p = 0.55 if race in ("Black or African American", "Hispanic or Latino") else 0.22
        zone = "outer" if rng.random() < far_p else "inner"
        merit = rng.gauss(0, 1) + 0.03 * min(exp, 12)
        bias = (0.15 + 0.3 * q) * gap + 0.75 * (zone == "outer") + 0.55 * (exp > 11)  # "over-qualified" penalty -> age proxy
        score = round(70 + 10 * (merit - bias), 1)
        people.append({
            "applicant_id": f"A{i:05d}", "quarter": QUARTERS[q], "sex": sex,
            "race_ethnicity": race, "age_band": age, "years_experience": f"{exp:.1f}",
            "employment_gap": "yes" if gap else "no", "commute_zone": zone,
            "score": score,
        })
    # Each quarter advances its top `selection_rate` share of applicants.
    for quarter in QUARTERS:
        cohort = sorted((p for p in people if p["quarter"] == quarter), key=lambda p: -p["score"])
        cut = int(len(cohort) * selection_rate)
        for j, p in enumerate(cohort):
            p["advanced"] = "1" if j < cut else "0"
    for p in people:
        p["score"] = f"{p['score']:.1f}"
    return people


def write_csv(path: str, rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
