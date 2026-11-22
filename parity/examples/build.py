"""Regenerate the example dataset, reports and README figures.

    python examples/build.py

The dataset is synthetic: 2,400 applicants screened by a fictional résumé
model that quietly under-selects some groups. Ground truth ("qualified") is
drawn independently of demographics, so any gap in selection is model bias.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from parity import load_csv, run_audit  # noqa: E402
from parity.report import to_html, to_markdown, to_svg  # noqa: E402

SEX = [("Female", 0.47), ("Male", 0.51), ("Non-binary", 0.02)]
RACE = [("White", 0.52), ("Hispanic or Latino", 0.19), ("Black", 0.14),
        ("Asian", 0.12), ("Two or more", 0.03)]
# Multiplicative bias the fictional model applies to qualified candidates.
BIAS = {"Female": 0.80, "Non-binary": 0.85, "Black": 0.70, "Hispanic or Latino": 0.88}


def pick(rng: random.Random, options):
    return rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]


def make_rows(n: int = 2400, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        sex, race = pick(rng, SEX), pick(rng, RACE)
        if rng.random() < 0.015:
            race = ""  # some applicants decline to self-identify
        qualified = rng.random() < 0.40
        p = (0.78 if qualified else 0.12) * BIAS.get(sex, 1) * BIAS.get(race, 1)
        score = round(min(100, max(0, rng.gauss(72 if qualified else 48, 12) * (0.5 + p))), 1)
        rows.append({"applicant_id": f"A{i:05d}", "sex": sex, "race": race,
                     "advanced": "yes" if rng.random() < p else "no",
                     "score": score, "qualified": int(qualified)})
    return rows


def main() -> None:
    data = ROOT / "examples" / "applicants.csv"
    rows = make_rows()
    with open(data, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    audit = run_audit(load_csv(data), "advanced", ["sex", "race"], label="qualified")
    (ROOT / "examples" / "report.md").write_text(to_markdown(audit) + "\n")
    (ROOT / "examples" / "report.html").write_text(to_html(audit, "Résumé screener — bias audit") + "\n")
    for dim in audit.dimensions[:2]:
        (ROOT / "docs" / f"impact-{dim.name}.svg").write_text(to_svg(dim) + "\n")
    print(f"wrote {data.name}, report.md, report.html and {len(audit.dimensions[:2])} figures "
          f"— verdict: {audit.verdict}")


if __name__ == "__main__":
    main()
