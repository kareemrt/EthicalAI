"""Command-line interface: `fairaudit data.csv --outcome hired --attr sex --attr race`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .chart import to_svg
from .metrics import audit, load_csv
from .report import to_json, to_markdown, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fairaudit",
        description="Audit decisions (hiring, lending, admissions…) for adverse impact "
                    "using the four-fifths rule and NYC Local Law 144 impact ratios.")
    p.add_argument("csv", help="CSV file with one row per person")
    p.add_argument("-o", "--outcome", required=True,
                   help="column holding the decision (yes/no, 1/0, hired…) or a numeric score")
    p.add_argument("-a", "--attr", action="append", required=True, metavar="COLUMN",
                   help="demographic column to audit (repeatable)")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio flag threshold (default 0.8)")
    p.add_argument("--min-share", type=float, default=0.0, metavar="FRACTION",
                   help="exclude groups smaller than this share of records, e.g. 0.02 (LL144 option)")
    p.add_argument("--mode", choices=["auto", "selection", "scoring"], default="auto",
                   help="treat outcome as yes/no selections or numeric scores (default: auto-detect)")
    p.add_argument("--no-intersect", action="store_true", help="skip the intersectional (A × B) breakdown")
    p.add_argument("--md", metavar="PATH", help="write a Markdown report")
    p.add_argument("--json", metavar="PATH", help="write machine-readable JSON results")
    p.add_argument("--svg", metavar="PATH", help="write an SVG impact-ratio chart")
    p.add_argument("--check", action="store_true", help="exit with code 1 if any group is flagged (for CI)")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    p.add_argument("-V", "--version", action="version", version=f"fairaudit {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit(load_csv(args.csv), args.outcome, args.attr, threshold=args.threshold,
                       min_share=args.min_share, intersect=not args.no_intersect, mode=args.mode)
    except (OSError, ValueError) as e:
        print(f"fairaudit: error: {e}", file=sys.stderr)
        return 2

    color = not args.no_color and sys.stdout.isatty() and "NO_COLOR" not in os.environ
    print(to_text(result, color=color))

    if args.svg:
        Path(args.svg).write_text(to_svg(result), encoding="utf-8")
    if args.md:
        chart = os.path.relpath(args.svg, Path(args.md).parent) if args.svg else None
        Path(args.md).write_text(to_markdown(result, chart), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(to_json(result), encoding="utf-8")

    return 1 if args.check and not result.passed else 0
