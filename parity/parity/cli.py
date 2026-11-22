"""Command-line interface: ``parity decisions.csv -y hired -g sex -g race``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .audit import ADVERSE, REVIEW, run_audit
from .io import load_csv
from .report import RENDERERS, to_text

EPILOG = """examples:
  parity hires.csv -y hired -g sex -g race
  parity scores.csv -y score -g gender --threshold 70 -f html -o audit.html
  parity loans.csv -y approved -g age_band -l repaid --fail-on review   # CI gate
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="parity",
        description="Audit an automated decision log for disparate impact.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("csv", type=Path, help="decision log, one row per person")
    p.add_argument("-y", "--outcome", required=True, help="column with the decision (yes/no) or a score")
    p.add_argument("-g", "--group", action="append", required=True, metavar="COLUMN",
                   help="demographic column to audit (repeatable)")
    p.add_argument("-l", "--label", help="optional ground-truth column, enables TPR/FPR parity")
    p.add_argument("-t", "--threshold", type=float, help="score cut-off (default: median)")
    p.add_argument("--no-intersect", action="store_true", help="skip intersectional groups")
    p.add_argument("--min-share", type=float, default=0.02, help="judge groups only above this share (0.02)")
    p.add_argument("--min-n", type=int, default=30, help="judge groups only above this size (30)")
    p.add_argument("-f", "--format", choices=sorted(RENDERERS), default="text", help="output format")
    p.add_argument("-o", "--output", type=Path, help="write the report to a file instead of stdout")
    p.add_argument("--fail-on", choices=["adverse", "review"],
                   help="exit with status 1 if this verdict (or worse) is found")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = run_audit(
            load_csv(args.csv), args.outcome, args.group, label=args.label,
            threshold=args.threshold, intersect=not args.no_intersect,
            min_share=args.min_share, min_n=args.min_n,
        )
    except (OSError, ValueError) as exc:
        print(f"parity: error: {exc}", file=sys.stderr)
        return 2

    if args.format == "text" and not args.output:
        report = to_text(audit, color=sys.stdout.isatty())
    else:
        report = RENDERERS[args.format](audit)

    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"parity: wrote {args.output} — {audit.verdict}", file=sys.stderr)
    else:
        print(report)

    failing = {"adverse": {ADVERSE}, "review": {ADVERSE, REVIEW}}.get(args.fail_on, set())
    return 1 if audit.verdict in failing else 0
