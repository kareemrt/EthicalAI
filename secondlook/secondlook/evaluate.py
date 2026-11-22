"""Score the engine against a labelled corpus.

    python -m secondlook.evaluate [examples/corpus.jsonl]

"caution" and "high" both count as flagged. The bundled corpus is small and
hand-written to illustrate common scam types; treat the numbers as a
regression check, not a benchmark.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .engine import check

DEFAULT = Path(__file__).resolve().parent.parent / "examples" / "corpus.jsonl"


def evaluate(path: Path) -> dict:
    tp = fp = tn = fn = 0
    misses = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        r = check(row["text"])
        flagged, scam = r.level != "low", row["label"] == "scam"
        tp += flagged and scam
        fp += flagged and not scam
        tn += not flagged and not scam
        fn += not flagged and scam
        if flagged != scam:
            misses.append((row["label"], round(r.risk * 100), row["text"][:70]))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return dict(tp=tp, fp=fp, tn=tn, fn=fn, precision=precision, recall=recall, misses=misses)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    m = evaluate(path)
    print(f"              flagged   not flagged")
    print(f"  scam        {m['tp']:>7}   {m['fn']:>11}")
    print(f"  legit       {m['fp']:>7}   {m['tn']:>11}")
    print(f"\n  precision {m['precision']:.0%}   recall {m['recall']:.0%}")
    for label, risk, text in m["misses"]:
        print(f"  miss: [{label} {risk}%] {text}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
