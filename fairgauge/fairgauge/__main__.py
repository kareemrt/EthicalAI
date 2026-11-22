"""Command-line entry point: python -m fairgauge data.csv --attr sex --selected hired"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .data import load
from .metrics import FOUR_FIFTHS, run
from .report import RENDERERS


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="fairgauge",
        description="Audit automated decisions (hiring, lending, admissions) for adverse impact.",
    )
    p.add_argument("csv", help="CSV file with one row per person")
    p.add_argument("-a", "--attr", action="append", required=True, metavar="COL",
                   help="demographic column to audit (repeatable)")
    out = p.add_mutually_exclusive_group(required=True)
    out.add_argument("-s", "--selected", metavar="COL", help="yes/no column: did the tool select this person?")
    out.add_argument("--score", metavar="COL", help="numeric column: selected = score above sample median")
    p.add_argument("--outcome", metavar="COL", help="ground-truth yes/no column (enables equal-opportunity check)")
    p.add_argument("-x", "--intersectional", action="store_true", help="also audit combinations of attributes")
    p.add_argument("-t", "--threshold", type=float, default=FOUR_FIFTHS, help="impact-ratio threshold (default 0.8)")
    p.add_argument("-f", "--format", choices=RENDERERS, help="output format (default: from -o extension, else md)")
    p.add_argument("-o", "--output", metavar="FILE", help="write report to FILE instead of stdout")
    p.add_argument("--fail-on-flag", action="store_true", help="exit 1 if any group shows adverse impact (for CI)")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    try:
        records = load(args.csv, args.attr, args.selected, args.score, args.outcome)
    except (OSError, ValueError) as e:
        print(f"fairgauge: {e}", file=sys.stderr)
        return 2

    audits = run(records, args.attr, args.intersectional, args.threshold)
    fmt = args.format or (Path(args.output).suffix.lstrip(".") if args.output else "md")
    render = RENDERERS.get(fmt, RENDERERS["md"])
    text = render(audits, len(records), Path(args.csv).name)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"report written to {args.output}", file=sys.stderr)
    else:
        print(text)

    flagged = any(a.flagged for a in audits)
    return 1 if flagged and args.fail_on_flag else 0


if __name__ == "__main__":
    sys.exit(main())
