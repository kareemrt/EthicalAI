"""Command-line entry point: `python -m fairhire applicants.csv --group sex --selected hired`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .data import load
from .metrics import FOUR_FIFTHS, MIN_SHARE, audit
from .report import RENDERERS, flagged


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="fairhire",
        description="Bias audit for automated hiring decisions (impact ratios, four-fifths rule, NYC LL144).",
    )
    p.add_argument("csv", help="CSV with one row per applicant")
    p.add_argument("-g", "--group", action="append", required=True, metavar="COL",
                   help="demographic column to audit; repeat for several (adds an intersectional view)")
    outcome = p.add_mutually_exclusive_group(required=True)
    outcome.add_argument("-s", "--selected", metavar="COL", help="yes/no outcome column (selection-rate mode)")
    outcome.add_argument("--score", metavar="COL", help="numeric score column (scoring-rate mode)")
    p.add_argument("-f", "--format", choices=RENDERERS, help="output format (default: from -o extension, else md)")
    p.add_argument("-o", "--output", metavar="FILE", help="write report to FILE instead of stdout")
    p.add_argument("--min-share", type=float, default=MIN_SHARE, metavar="X",
                   help=f"skip impact ratio for categories under this share of data (default {MIN_SHARE})")
    p.add_argument("--strict", action="store_true", help="exit with code 1 if any category is flagged (for CI)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        ds = load(args.csv, args.group, args.selected, args.score)
    except (OSError, ValueError) as exc:
        print(f"fairhire: error: {exc}", file=sys.stderr)
        return 2

    results = [(v.name, v.unknown, audit(v.records, args.min_share)) for v in ds.views]

    fmt = args.format or (Path(args.output).suffix.lstrip(".") if args.output else "md")
    render = RENDERERS.get(fmt, RENDERERS["md"])
    report = render(results, ds, Path(args.csv).name)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        hits = len(flagged(results))
        print(f"wrote {args.output} — {hits} categor{'y' if hits == 1 else 'ies'} below {FOUR_FIFTHS:g}", file=sys.stderr)
    else:
        print(report)

    return 1 if args.strict and flagged(results) else 0
