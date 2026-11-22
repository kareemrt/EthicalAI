"""Command-line interface.  Exit codes: 0 pass · 1 adverse impact found · 2 usage error."""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__, data, report
from .metrics import FAIL, FOUR_FIFTHS, WARN, audit

EPILOG = """examples:
  fairlens applicants.csv -g gender -g race -d hired
  fairlens applicants.csv -g gender race -d hired --label qualified --intersect
  fairlens applicants.csv -g race --score model_score --md audit.md --svg audit.svg
"""


def parse(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="fairlens", epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Audit automated decisions (hiring, lending, admissions...) for adverse impact.")
    p.add_argument("csv", help="one row per person")
    p.add_argument("-g", "--group", nargs="+", action="extend", required=True, metavar="COL",
                   help="protected-attribute column(s), e.g. gender race age_band")

    out = p.add_mutually_exclusive_group(required=True)
    out.add_argument("-d", "--decision", metavar="COL", help="yes/no outcome column")
    out.add_argument("-s", "--score", metavar="COL", help="numeric score column (binarized at --cutoff)")

    p.add_argument("--positive", metavar="VALUE", help="value of --decision that counts as selected")
    p.add_argument("--cutoff", default="median", help="score cutoff: 'median' (NYC LL144) or a number")
    p.add_argument("-l", "--label", metavar="COL", help="ground-truth column; adds TPR/FPR (equalized odds)")
    p.add_argument("-i", "--intersect", action="store_true", help="also audit every combination of --group columns")
    p.add_argument("-t", "--threshold", type=float, default=FOUR_FIFTHS, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--min-share", type=float, default=0.0, metavar="FRAC",
                   help="exclude groups below this share of data from scoring, e.g. 0.02")
    p.add_argument("--strict", action="store_true", help="treat WARN as failure (exit 1)")
    p.add_argument("--md", metavar="FILE", help="write a Markdown report")
    p.add_argument("--svg", metavar="FILE", help="write an SVG chart")
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse(argv)
    try:
        rows = data.load(args.csv)
        cols = args.group + [c for c in (args.decision, args.score, args.label) if c]
        data.require(rows, cols)
        decisions = (data.decisions_from_scores(rows, args.score, args.cutoff) if args.score
                     else [data.to_bool(r[args.decision], args.positive) for r in rows])

        attrs = [[c] for c in args.group]
        if args.intersect and len(args.group) > 1:
            attrs.append(args.group)

        audits = [audit(data.to_records(rows, cols_, decisions, args.label), " × ".join(cols_),
                        args.threshold, args.alpha, args.min_share) for cols_ in attrs]
    except (OSError, ValueError) as e:
        print(f"fairlens: error: {e}", file=sys.stderr)
        return 2

    print(report.to_json(audits) if args.json else report.text(audits), end="")

    if args.svg:
        with open(args.svg, "w", encoding="utf-8") as f:
            f.write(report.svg(audits))
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            chart = os.path.relpath(args.svg, os.path.dirname(args.md) or ".") if args.svg else ""
            f.write(report.markdown(audits, os.path.basename(args.csv), chart))

    statuses = {a.status for a in audits}
    return 1 if FAIL in statuses or (args.strict and WARN in statuses) else 0


if __name__ == "__main__":
    sys.exit(main())
