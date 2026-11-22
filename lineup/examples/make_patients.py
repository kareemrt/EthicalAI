"""Generate examples/patients.csv: 1,000 synthetic clinic records.

Everything is random (seeded), no real people. The shape mirrors a typical
"de-identified" research extract: names and emails were left in by mistake,
and ZIP + birth date + sex remain - the combination that famously let
researchers re-identify a state governor's medical records in 1997.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(7)
FIRST = "Ana Ben Chloe Dev Elena Farid Grace Hiro Ines Jamal Kofi Lena Mateo Nia Omar Priya Quinn Rosa Sami Tara".split()
LAST = "Adams Baker Chen Diaz Evans Fofana Garcia Hughes Ito Jones Khan Lopez Moreau Nguyen Okafor Patel Rossi Silva Tanaka Weber".split()
ZIPS = [f"021{n:02d}" for n in range(16, 46)]
RACE = (["White"] * 55 + ["Black"] * 15 + ["Hispanic"] * 17 + ["Asian"] * 9 + ["Other"] * 4)
DIAG = (["Hypertension"] * 24 + ["Type 2 diabetes"] * 16 + ["Asthma"] * 14 + ["Depression"] * 14
        + ["Back pain"] * 18 + ["Migraine"] * 10 + ["HIV"] * 2 + ["Opioid use disorder"] * 2)

rows = []
for i in range(1000):
    first, last = rng.choice(FIRST), rng.choice(LAST)
    born = date(1940, 1, 1) + timedelta(days=rng.randrange(65 * 365))
    rows.append({
        "patient_id": f"P{100000 + i}",
        "name": f"{first} {last}",
        "email": f"{first}.{last}{rng.randrange(100)}@example.org".lower(),
        "zip": rng.choice(ZIPS),
        "birth_date": born.isoformat(),
        "sex": rng.choice("FM"),
        "race": rng.choice(RACE),
        "diagnosis": rng.choice(DIAG),
        "visits_last_year": rng.randint(1, 12),
    })

out = Path(__file__).with_name("patients.csv")
with out.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0])
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {len(rows)} rows to {out}")
