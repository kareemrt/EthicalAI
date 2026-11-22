"""Command line interface.

    redflag check "message text"      # or pipe text in on stdin
    redflag check --json < msg.txt
    redflag train                     # re-learn weights from data/messages.jsonl
    redflag eval                      # cross-validation + held-out metrics
    redflag serve                     # local web UI on http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from .model import Model, Report

DATA = Path(__file__).resolve().parents[1] / "data" / "messages.jsonl"
COLORS = {"danger": "\033[1;31m", "warn": "\033[1;33m", "ok": "\033[1;32m"}
DIM, BOLD, UNDER, RESET = "\033[2m", "\033[1m", "\033[4m", "\033[0m"


def load_data(path: Path = DATA) -> tuple[list[str], list[int]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r["text"] for r in rows], [r["label"] for r in rows]


def render(report: Report, color: bool = True) -> str:
    c = (lambda code, s: f"{code}{s}{RESET}") if color else (lambda _, s: s)
    spans = sorted({(h.start, h.end) for f in report.flags for h in f.hits})
    text, out, pos = report.text, [], 0
    for start, end in spans:  # underline every piece of evidence
        if start < pos:
            continue
        out += [text[pos:start], c(UNDER, text[start:end])]
        pos = end
    out.append(text[pos:])

    bar = "█" * round(report.risk * 20) + "░" * (20 - round(report.risk * 20))
    lines = [
        "", "  " + "".join(out), "",
        f"  {c(COLORS[report.level], report.verdict.upper())}   {bar}  {min(report.risk, 0.99):.0%} risk", "",
    ]
    for i, f in enumerate(report.flags, 1):
        quotes = ", ".join(f'"{h.text}"' for h in f.hits[:3])
        lines += [f"  {i}. {c(BOLD, f.signal.label)}  {c(DIM, quotes)}",
                  f"     Why: {f.signal.why}",
                  f"     Do:  {f.signal.advice}", ""]
    if not report.flags:
        lines += ["  No known scam patterns found. Still unsure? Contact the sender through a", "  number or website you already trust.", ""]
    return "\n".join(lines)


def metrics(preds: list[bool], labels: list[int]) -> dict[str, float]:
    tp = sum(p and y for p, y in zip(preds, labels))
    fp = sum(p and not y for p, y in zip(preds, labels))
    fn = sum(y and not p for p, y in zip(preds, labels))
    tn = len(labels) - tp - fp - fn
    return {"accuracy": (tp + tn) / len(labels), "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1),
            "false_positive_rate": fp / max(fp + tn, 1), "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def cross_validate(texts: list[str], labels: list[int], k: int = 5, seed: int = 1) -> dict[str, float]:
    idx = list(range(len(texts)))
    random.Random(seed).shuffle(idx)
    preds = [False] * len(texts)
    for fold in range(k):
        test = set(idx[fold::k])
        m = Model.train([texts[i] for i in idx if i not in test], [labels[i] for i in idx if i not in test])
        for i in test:
            preds[i] = m.score(texts[i]).risk >= 0.5
    return metrics(preds, labels)


def holdout(model: Model) -> dict[str, float]:
    texts, labels = load_data(DATA.with_name("holdout.jsonl"))
    return metrics([model.score(t).risk >= 0.5 for t in texts], labels)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="redflag", description="Explainable, offline scam-message checker.")
    sub = p.add_subparsers(dest="cmd", required=True)
    chk = sub.add_parser("check", help="check a message")
    chk.add_argument("text", nargs="*", help="message text (reads stdin if omitted)")
    chk.add_argument("--json", action="store_true", help="machine-readable output")
    sub.add_parser("train", help="re-learn weights from data/messages.jsonl")
    sub.add_parser("eval", help="cross-validation + held-out metrics")
    srv = sub.add_parser("serve", help="run the local web UI")
    srv.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)

    if args.cmd == "check":
        text = " ".join(args.text) if args.text else sys.stdin.read()
        report = Model.load().score(text.strip())
        print(json.dumps(report.to_dict(), indent=2) if args.json else render(report, sys.stdout.isatty()))
        return 2 if report.level == "danger" else 1 if report.level == "warn" else 0

    if args.cmd == "train":
        texts, labels = load_data()
        model = Model.train(texts, labels)
        model.save()
        print(f"trained on {len(texts)} messages; bias {model.bias:+.2f}")
        for f, w in sorted(model.weights.items(), key=lambda kv: -kv[1]):
            print(f"  {f:<18} {w:+.2f}")
        return 0

    if args.cmd == "eval":
        for title, m in (("5-fold cross-validation (training set)", cross_validate(*load_data())),
                         ("Held-out set (never used for tuning)", holdout(Model.load()))):
            print(title)
            for k in ("accuracy", "precision", "recall", "false_positive_rate"):
                print(f"  {k:<20} {m[k]:.1%}")
            print(f"  confusion            TP={m['tp']} FP={m['fp']} TN={m['tn']} FN={m['fn']}\n")
        return 0

    if args.cmd == "serve":
        from .server import serve
        serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
