"""Generate a synthetic hiring dataset with a known, injected bias.

Useful for demos and tests: the 'true' qualification rate is equal across
groups, but the screening model under-scores some of them.
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

SEX = [("Female", 0.47), ("Male", 0.50), ("Nonbinary", 0.03)]
RACE = [("White", 0.52), ("Black", 0.18), ("Hispanic", 0.18), ("Asian", 0.10), ("", 0.02)]
# Score penalty the biased model applies (on a 0–100 scale).
PENALTY = {"Female": 6, "Nonbinary": 4, "Black": 9, "Hispanic": 4}


def _pick(rng: random.Random, options: list[tuple[str, float]]) -> str:
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def generate(n: int = 2000, seed: int = 7, fair: bool = False) -> list[dict]:
    """`fair=True` removes the injected penalty, giving an unbiased baseline."""
    rng = random.Random(seed)
    penalty = {} if fair else PENALTY
    rows = []
    for i in range(n):
        sex, race = _pick(rng, SEX), _pick(rng, RACE)
        skill = rng.gauss(60, 12)                              # latent ability, same for every group
        qualified = int(skill + rng.gauss(0, 5) >= 65)
        score = skill + rng.gauss(0, 6) - penalty.get(sex, 0) - penalty.get(race, 0)
        score = round(min(100, max(0, score)), 1)
        rows.append({
            "applicant_id": f"A{i:05d}", "sex": sex, "race": race,
            "score": score, "advanced": "yes" if score >= 62 else "no", "qualified": qualified,
        })
    return rows


def write(rows: list[dict], path: str | Path | None) -> None:
    fh = open(path, "w", newline="", encoding="utf-8") if path else sys.stdout
    try:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    finally:
        if path:
            fh.close()
