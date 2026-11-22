"""Command-line interface: ``python -m fairhire data.csv --outcome hired --attrs sex race``."""

from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

from . import __version__, chart, report
from .data import load_csv
from .metrics import Status, audit


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fairhire", description="Bias audit for automated hiring decisions "
                                "(selection rates, impact ratios, four-fifths rule, significance).")
    p.add_argument("csv", help="CSV with one row per candidate")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--outcome", help="column with the decision (hired/advanced/1/yes …)")
    src.add_argument("--score", help="numeric score column; 'selected' = above the sample median (LL144 scoring rate)")
    p.add_argument("--attrs", nargs="+", required=True, help="demographic columns to audit, e.g. sex race")
    p.add_argument("--intersect", action="store_true", help="also audit intersections of the attributes")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--min-share", type=float, default=0.02, help="exclude categories below this share (default 0.02)")
    p.add_argument("--no-correction", action="store_true", help="skip Holm–Bonferroni multiple-comparison correction")
    p.add_argument("--format", choices=["text", "md", "json"], default="text")
    p.add_argument("-o", "--out", help="write the report to this file instead of stdout")
    p.add_argument("--svg", help="also write an impact-ratio chart (SVG)")
    p.add_argument("--strict", action="store_true", help="exit 1 on any 'adverse' finding (CI gate)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = load_csv(args.csv)
        dims = [[a] for a in args.attrs]
        if args.intersect:
            dims += [list(c) for k in range(2, len(args.attrs) + 1) for c in combinations(args.attrs, k)]
        audits = [audit(rows, d, outcome=args.outcome, score=args.score, threshold=args.threshold,
                        alpha=args.alpha, min_share=args.min_share, correct=not args.no_correction) for d in dims]
    except (OSError, ValueError) as e:
        print(f"fairhire: error: {e}", file=sys.stderr)
        return 2

    chart_ref = None
    if args.svg:
        Path(args.svg).write_text(chart.svg(audits), encoding="utf-8")
        chart_ref = Path(args.svg).name if args.out and Path(args.svg).parent == Path(args.out).parent \
            else args.svg

    out = {"text": report.text, "json": report.to_json}.get(args.format)
    rendered = out(audits) if out else report.markdown(audits, chart=chart_ref)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    return 1 if args.strict and any(a.worst is Status.ADVERSE for a in audits) else 0
