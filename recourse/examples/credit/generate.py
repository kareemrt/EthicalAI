"""Regenerate the synthetic applicants.csv (seeded, reproducible).

Group B is drawn with lower average income and a higher area risk index,
mirroring how residential segregation leaks into "neutral" features.
Usage:  python examples/credit/generate.py > examples/credit/applicants.csv
"""

import csv
import random
import sys

GROUPS = {  # income mean, area-risk mean
    "Group A": (62, 0.28),
    "Group B": (54, 0.46),
}


def clip(v, lo, hi):
    return max(lo, min(hi, v))


def main(n_per_group: int = 300, seed: int = 7) -> None:
    rng = random.Random(seed)
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["id", "group", "income_k", "utilization_pct", "debt_k",
                  "missed_payments_24m", "history_years", "area_risk_index"])
    i = 0
    for group, (inc, risk) in GROUPS.items():
        for _ in range(n_per_group):
            i += 1
            out.writerow([
                f"P-{i:04d}", group,
                round(clip(rng.gauss(inc, 18), 12, 220)),
                round(clip(rng.gauss(40, 22), 0, 100)),
                round(clip(rng.gauss(16, 10), 0, 80) * 2) / 2,
                min(5, int(rng.expovariate(1.6))),
                round(clip(rng.gauss(9, 5), 0, 35), 1),
                round(clip(rng.gauss(risk, 0.18), 0, 1), 2),
            ])


if __name__ == "__main__":
    main()
