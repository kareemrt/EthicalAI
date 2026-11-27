"""Command-line entry point: ``python -m impartial data.csv --groups sex race --outcome hired``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .data import load_csv
from .metrics import run_audit
from .report import overall, to_html, to_json, to_markdown, to_svg, to_text

FORMATS = ("text", "md", "html", "json", "svg")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="impartial",
        description="Audit automated decisions (hiring, lending, admissions) for adverse impact.",
    )
    p.add_argument("csv", help="CSV file with one row per person")
    p.add_argument("-g", "--groups", nargs="+", required=True, metavar="COL", help="protected-attribute column(s)")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("-o", "--outcome", metavar="COL", help="yes/no column (1, true, hired, approved...)")
    target.add_argument("-s", "--score", metavar="COL", help="numeric score column (favourable = above median)")
    p.add_argument("-f", "--format", choices=FORMATS, default="text", help="output format (default: text)")
    p.add_argument("--out", metavar="FILE", help="write report to FILE instead of stdout")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio threshold (default: 0.8)")
    p.add_argument("--min-share", type=float, default=0.02, help="exclude groups below this share (default: 0.02)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default: 0.05)")
    p.add_argument("--no-intersections", action="store_true", help="skip the combined-attribute analysis")
    p.add_argument("--strict", action="store_true", help="exit 1 on REVIEW as well as FAIL (for CI gates)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records, meta = load_csv(args.csv, args.groups, args.outcome, args.score)
    except (OSError, ValueError) as exc:
        print(f"impartial: error: {exc}", file=sys.stderr)
        return 2

    results = run_audit(
        records,
        args.groups,
        intersectional=not args.no_intersections,
        threshold=args.threshold,
        min_share=args.min_share,
        alpha=args.alpha,
    )

    to_file = bool(args.out)
    render = {
        "text": lambda: to_text(results, meta, color=not to_file and sys.stdout.isatty()),
        "md": lambda: to_markdown(results, meta, args.threshold),
        "html": lambda: to_html(results, meta, args.threshold),
        "json": lambda: to_json(results, meta),
        "svg": lambda: to_svg(results[-1], args.threshold),
    }[args.format]()

    if to_file:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(render + "\n")
        print(f"Report written to {args.out} · overall: {overall(results)}", file=sys.stderr)
    else:
        print(render)

    verdict = overall(results)
    return 1 if verdict == "FAIL" or (args.strict and verdict == "REVIEW") else 0
