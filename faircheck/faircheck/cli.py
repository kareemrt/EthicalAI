"""Command-line entry point: `python -m faircheck data.csv --outcome hired --attr sex`."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .audit import load_csv, run_audit
from .chart import impact_svg
from .report import to_json, to_markdown, to_terminal


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="faircheck",
        description="Audit automated decisions for disparate impact (four-fifths rule / NYC LL144).",
    )
    p.add_argument("csv", help="CSV file, one row per person")
    p.add_argument("--outcome", required=True, help="decision column (yes/no) or score column (numeric)")
    p.add_argument("--attr", action="append", required=True, metavar="COLUMN",
                   help="protected attribute column; repeat for several (e.g. --attr sex --attr race)")
    p.add_argument("--label", help="optional ground-truth column (yes/no) for TPR/FPR analysis")
    p.add_argument("--cutoff", type=float, help="score cutoff (default: sample median)")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--min-share", type=float, default=0.02,
                   help="groups below this share of rows are reported but not judged (default 0.02)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--no-intersections", action="store_true", help="skip combined attribute groups")
    p.add_argument("--out", type=Path, help="write report.md, report.json and impact_ratios.svg here")
    p.add_argument("--fail-on", choices=["adverse", "significant", "never"], default="significant",
                   help="exit 1 when adverse impact is found — for CI gates (default: significant)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = run_audit(
            load_csv(args.csv), args.outcome, args.attr, label=args.label, cutoff=args.cutoff,
            threshold=args.threshold, min_share=args.min_share, alpha=args.alpha,
            intersections=not args.no_intersections,
        )
    except (OSError, ValueError) as e:
        print(f"faircheck: error: {e}", file=sys.stderr)
        return 2

    print(to_terminal(audit))
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "report.md").write_text(to_markdown(audit), encoding="utf-8")
        (args.out / "report.json").write_text(to_json(audit), encoding="utf-8")
        (args.out / "impact_ratios.svg").write_text(impact_svg(audit), encoding="utf-8")
        print(f"\nReport written to {args.out}/")

    if args.fail_on == "never":
        return 0
    return 1 if audit.adverse(significant_only=args.fail_on == "significant") else 0
