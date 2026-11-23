"""Load predictions from CSV into a flat, validated list."""

import csv
from dataclasses import dataclass
from typing import List, Optional

TRUTHY = {"1", "true", "yes", "y", "t"}
FALSY = {"0", "false", "no", "n", "f"}


@dataclass(frozen=True)
class Prediction:
    confidence: float  # model's probability that its own answer is right
    correct: bool      # was the answer actually right?
    group: str = "all"


def _bool(raw: str, line: int) -> bool:
    v = raw.strip().lower()
    if v in TRUTHY:
        return True
    if v in FALSY:
        return False
    raise ValueError(f"line {line}: expected 0/1 or true/false, got {raw!r}")


def _prob(raw: str, line: int) -> float:
    try:
        p = float(raw)
    except ValueError:
        raise ValueError(f"line {line}: expected a probability, got {raw!r}") from None
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"line {line}: probability {p} is outside [0, 1]")
    return p


def load_csv(path: str, group_col: Optional[str] = None) -> List[Prediction]:
    """Read predictions. Two layouts are accepted:

    * ``confidence,correct``  - any classifier (top-label confidence + hit/miss)
    * ``score,label``         - binary classifier (P(label=1) + true label);
                                the predicted class is ``score >= 0.5``
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
        if {"confidence", "correct"} <= cols:
            mode = "topl"
        elif {"score", "label"} <= cols:
            mode = "binary"
        else:
            raise ValueError(
                f"{path}: need columns 'confidence,correct' or 'score,label'; found {sorted(cols)}"
            )
        if group_col and group_col not in cols:
            raise ValueError(f"{path}: group column {group_col!r} not found")

        out = []
        for line, row in enumerate(reader, start=2):
            if mode == "topl":
                conf, ok = _prob(row["confidence"], line), _bool(row["correct"], line)
            else:
                score, label = _prob(row["score"], line), _bool(row["label"], line)
                conf, ok = max(score, 1 - score), (score >= 0.5) == label
            group = row[group_col].strip() if group_col else "all"
            out.append(Prediction(conf, ok, group or "unknown"))
    if not out:
        raise ValueError(f"{path}: no rows")
    return out
