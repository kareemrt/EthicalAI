"""Command line: python -m handoff predictions.csv [--group col] [--out dir]"""

import argparse
import sys

from . import __version__, report
from .audit import run_audit
from .data import load_csv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="handoff",
        description="Audit a classifier's confidence and find when it should hand off to a human.")
    ap.add_argument("csv", help="predictions: columns confidence,correct  or  score,label")
    ap.add_argument("-g", "--group", help="column to break results down by (e.g. site, age_band)")
    ap.add_argument("-t", "--target", type=float, default=0.95,
                    help="accuracy required on automated cases (default 0.95)")
    ap.add_argument("--max-ece", type=float, default=0.05, help="calibration gate (default 0.05)")
    ap.add_argument("--max-gap", type=float, default=0.03,
                    help="max ECE difference between groups (default 0.03)")
    ap.add_argument("-o", "--out", help="write report.md, summary.json and SVG charts here")
    ap.add_argument("--version", action="version", version=f"handoff {__version__}")
    args = ap.parse_args(argv)

    try:
        preds = load_csv(args.csv, args.group)
    except (OSError, ValueError) as e:
        print(f"handoff: {e}", file=sys.stderr)
        return 2
    audit = run_audit(preds, args.target, args.max_ece, args.max_gap)
    print(report.text(audit))
    if args.out:
        report.write(audit, preds, args.out)
        print(f"\nReport written to {args.out}/report.md")
    return 0 if audit.passed else 1
