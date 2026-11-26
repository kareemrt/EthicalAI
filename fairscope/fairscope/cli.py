"""Command-line interface: `fairscope audit decisions.csv --by gender --outcome hired`."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .data import groups, load_rows, outcomes, require, to_bool
from .metrics import FAIL, REVIEW, audit, worst
from .report import RENDERERS

EXIT = {"never": set(), "fail": {FAIL}, "review": {FAIL, REVIEW}}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fairscope", description="Audit automated decisions for adverse impact.")
    p.add_argument("--version", action="version", version=f"fairscope {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("audit", help="audit a CSV of decisions")
    a.add_argument("file", help="CSV with one row per person/decision")
    a.add_argument("--by", action="append", required=True, metavar="COL",
                   help="protected attribute column (repeatable)")
    a.add_argument("--intersect", action="store_true", help="also audit the intersection of all --by columns")
    src = a.add_mutually_exclusive_group(required=True)
    src.add_argument("--outcome", metavar="COL", help="yes/no column: did the person get the favourable outcome?")
    src.add_argument("--score", metavar="COL", help="numeric score column (selected = above --cutoff)")
    a.add_argument("--cutoff", type=float, help="score cutoff (default: overall median, as in NYC LL144)")
    a.add_argument("--label", metavar="COL", help="optional ground-truth yes/no column (enables TPR/FPR parity)")
    a.add_argument("--threshold", type=float, default=0.8, help="minimum acceptable impact ratio (default 0.8)")
    a.add_argument("--min-share", type=float, default=0.02, help="exclude groups below this share (default 0.02)")
    a.add_argument("--format", choices=RENDERERS, help="output format (default: from -o extension, else text)")
    a.add_argument("-o", "--output", help="write report to this file instead of stdout")
    a.add_argument("--fail-on", choices=EXIT, default="fail",
                   help="exit with status 1 on this verdict or worse (default: fail)")
    return p


def run_audit(args) -> int:
    rows = load_rows(args.file)
    require(rows, *args.by, args.outcome, args.score, args.label)
    selected = outcomes(rows, args.outcome, args.score, args.cutoff)
    labels = [to_bool(r[args.label], args.label) for r in rows] if args.label else None

    sets = [[c] for c in args.by] + ([args.by] if args.intersect and len(args.by) > 1 else [])
    audits = [audit(" × ".join(cols), groups(rows, cols), selected, labels, args.threshold, args.min_share)
              for cols in sets]

    fmt = args.format or {".md": "md", ".html": "html", ".json": "json"}.get(
        os.path.splitext(args.output or "")[1], "text")
    report = RENDERERS[fmt](audits, os.path.basename(args.file))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
        print(f"{worst(a.verdict for a in audits)} → report written to {args.output}", file=sys.stderr)
    else:
        print(report)
    return 1 if worst(a.verdict for a in audits) in EXIT[args.fail_on] else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_audit(args)
    except (OSError, ValueError) as e:
        print(f"fairscope: error: {e}", file=sys.stderr)
        return 2
