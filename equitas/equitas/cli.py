"""Command-line entry point: ``equitas data.csv --outcome hired --attrs sex race``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .data import load
from .metrics import ADVERSE, audit
from .report import RENDERERS, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="equitas",
        description="Audit automated decisions for adverse impact (four-fifths rule + significance).",
        epilog="example: equitas applicants.csv -y hired -a sex race_ethnicity --label qualified -f html -o report.html",
    )
    p.add_argument("csv", help="CSV file, one row per decision")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("-y", "--outcome", help="yes/no decision column (e.g. hired, approved)")
    what.add_argument("-s", "--score", help="numeric score column; selected = above --threshold (default: median)")
    p.add_argument("-a", "--attrs", nargs="+", required=True, help="protected-attribute columns to audit")
    p.add_argument("--threshold", type=float, help="score cut-off (with --score)")
    p.add_argument("--positive", help="value in --outcome that means selected (default: 1/yes/true/hired/...)")
    p.add_argument("--label", help="optional ground-truth column (e.g. qualified) to measure error-rate gaps")
    p.add_argument("--ratio", type=float, default=0.8, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--min-share", type=float, default=0.02, help="skip scoring groups below this share (default 0.02)")
    p.add_argument("--no-intersect", action="store_true", help="skip pairwise intersectional groups")
    p.add_argument("-f", "--format", choices=sorted(RENDERERS), default="text", help="output format")
    p.add_argument("-o", "--out", help="write the report to this file instead of stdout")
    p.add_argument("--strict", action="store_true", help="exit with code 2 if any group is flagged adverse (for CI)")
    p.add_argument("--version", action="version", version=f"equitas {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = load(args.csv, args.attrs, outcome=args.outcome, score=args.score,
                       threshold=args.threshold, label=args.label, positive=args.positive)
        result = audit(records, args.attrs, ratio=args.ratio, alpha=args.alpha,
                       min_share=args.min_share, intersect=not args.no_intersect)
    except (OSError, ValueError) as exc:
        print(f"equitas: error: {exc}", file=sys.stderr)
        return 1

    if args.format == "text":
        report = to_text(result, color=not args.out and sys.stdout.isatty())
    else:
        report = RENDERERS[args.format](result)

    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")
        n = len(result.findings(ADVERSE))
        print(f"wrote {args.out} · {n} adverse finding{'s' * (n != 1)}", file=sys.stderr)
    else:
        print(report)

    return 2 if args.strict and result.findings(ADVERSE) else 0


if __name__ == "__main__":
    sys.exit(main())
