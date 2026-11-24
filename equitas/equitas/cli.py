"""Command-line entry point: `python -m equitas audit ...`"""

from __future__ import annotations

import argparse
import sys

from .audit import run_audit
from .data import DataError
from .metrics import ADVERSE, REVIEW
from .report import to_json, to_markdown, to_terminal, write_report

EXIT = {"ok": 0, REVIEW: 0, ADVERSE: 1}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="equitas",
        description="Bias audits for automated decisions (hiring, lending, admissions).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("audit", help="audit a CSV of decisions")
    a.add_argument("csv", help="one row per person: an outcome column + group columns")
    a.add_argument("-o", "--outcome", required=True, help="outcome column (yes/no or score)")
    a.add_argument("-g", "--groups", nargs="+", required=True,
                   help="demographic columns to audit, e.g. sex race")
    a.add_argument("--score", action="store_true",
                   help="outcome is a numeric score: use LL144 above-median scoring rate")
    a.add_argument("--no-intersect", action="store_true",
                   help="skip the intersectional (combined) categories")
    a.add_argument("--threshold", type=float, default=0.8,
                   help="impact-ratio flag threshold (default 0.8, four-fifths rule)")
    a.add_argument("--min-share", type=float, default=0.02,
                   help="exclude groups below this share from ratios (default 0.02)")
    a.add_argument("--alpha", type=float, default=0.05,
                   help="significance level (default 0.05)")
    a.add_argument("--out", metavar="DIR",
                   help="write report.md, audit.json and SVG charts to DIR")
    a.add_argument("--format", choices=["text", "markdown", "json"], default="text",
                   help="what to print to stdout (default text)")
    a.add_argument("--strict", action="store_true",
                   help="also exit non-zero on 'review' (use as a CI gate)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = run_audit(
            args.csv, args.outcome, args.groups,
            score=args.score, intersect=not args.no_intersect,
            threshold=args.threshold, min_share=args.min_share, alpha=args.alpha,
        )
    except (DataError, OSError) as e:
        print(f"equitas: error: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(to_json(audit))
    elif args.format == "markdown":
        print(to_markdown(audit, chart_dir=None))
    else:
        print(to_terminal(audit, color=sys.stdout.isatty()))

    if args.out:
        path = write_report(audit, args.out)
        print(f"\nReport written to {path}", file=sys.stderr)

    if args.strict and audit.status == REVIEW:
        return 1
    return EXIT.get(audit.status, 0)
