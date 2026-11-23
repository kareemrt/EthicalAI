"""Generate a SYNTHETIC dermatology-triage dataset for the handoff demo.

It mimics a pattern documented in real skin-lesion classifiers: the model is
less accurate on darker skin (Fitzpatrick V-VI, under-represented in training
images) yet reports the same high confidence. No real patients are involved.

    python examples/make_triage.py > examples/triage.csv
"""

import csv
import math
import random
import sys

GROUPS = [  # (Fitzpatrick band, share of cases, mean evidence strength)
    ("I-II", 0.45, 2.6),
    ("III-IV", 0.40, 2.3),
    ("V-VI", 0.15, 1.3),
]


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def main(n: int = 4000, seed: int = 7) -> None:
    rng = random.Random(seed)
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["case_id", "skin_type", "confidence", "correct"])
    for i in range(n):
        r, acc = rng.random(), 0.0
        for name, share, mu in GROUPS:
            acc += share
            if r <= acc:
                break
        z = rng.gauss(mu, 1.3)                      # how clear-cut the image is
        p_right = sigmoid(z)                         # true chance the model is right
        conf = sigmoid(1.7 * z + 1.0 + rng.gauss(0, 0.25))  # over-stretched, inflated
        conf = min(max(conf, 0.5), 0.9999)           # top-label of a binary call
        w.writerow([f"c{i:05d}", name, f"{conf:.4f}", int(rng.random() < p_right)])


if __name__ == "__main__":
    main()
