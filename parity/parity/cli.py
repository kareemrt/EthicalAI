"""Command-line entry point:  parity data.csv --outcome hired --by sex race"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import __version__
from .metrics import audit
from .report import to_html, to_json, to_markdown, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="parity",
        description="Audit automated decisions for disparate impact (four-fifths rule).")
    p.add_argument("csv", type=Path, help="CSV with one row per person")
    p.add_argument("-o", "--outcome", required=True, help="decision or score column")
    p.add_argument("-b", "--by", nargs="+", required=True, metavar="COL",
                   help="demographic column(s) to audit, e.g. sex race")
    p.add_argument("--score", action="store_true",
                   help="outcome is a numeric score; favourable = above the sample median")
    p.add_argument("--no-intersect", action="store_true",
                   help="skip the intersectional (combined) audit")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio benchmark (default 0.8)")
    p.add_argument("--min-share", type=float, default=0.02,
                   help="groups below this share are reported but not flagged (default 0.02)")
    p.add_argument("--html", type=Path, metavar="FILE", help="write a self-contained HTML report")
    p.add_argument("--md", type=Path, metavar="FILE", help="write a Markdown report")
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    p.add_argument("--fail-on-adverse", action="store_true",
                   help="exit with status 1 if any group shows adverse impact (for CI)")
    p.add_argument("--version", action="version", version=f"parity {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with args.csv.open(newline="", encoding="utf-8-sig") as fh:
            result = audit(csv.DictReader(fh), args.outcome, args.by,
                           scored=args.score, intersect=not args.no_intersect,
                           threshold=args.threshold, min_share=args.min_share)
    except (OSError, ValueError) as err:
        print(f"parity: error: {err}", file=sys.stderr)
        return 2

    print(to_json(result) if args.json else to_text(result, color=sys.stdout.isatty()))
    if args.html:
        args.html.write_text(to_html(result, source=args.csv.name), encoding="utf-8")
    if args.md:
        args.md.write_text(to_markdown(result), encoding="utf-8")
    return 1 if args.fail_on_adverse and result.has_adverse_impact else 0


if __name__ == "__main__":
    sys.exit(main())
