"""Command-line entry point: `fairlens data.csv --outcome hired --groups sex,race`."""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

from . import __version__
from .chart import impact_svg
from .data import read_rows, tally
from .metrics import analyse
from .report import to_json, to_markdown, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fairlens",
        description="Audit automated decisions (hiring, lending, admissions) for adverse impact.",
        epilog="Exit codes: 0 pass · 1 adverse impact found (with --strict) · 2 usage/data error.")
    p.add_argument("csv", help="CSV file with one row per decision")
    p.add_argument("-o", "--outcome", required=True, help="column holding the decision (1/yes/hired/…)")
    p.add_argument("-g", "--groups", required=True, help="comma-separated protected-attribute columns")
    p.add_argument("-l", "--label", help="optional ground-truth column (qualified / repaid) → TPR & FPR")
    p.add_argument("--positive", help="exact outcome value meaning 'selected' (default: common truthy words)")
    p.add_argument("-x", "--intersect", action="store_true", help="also audit every pair of attributes")
    p.add_argument("-t", "--threshold", type=float, default=0.8, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--min-n", type=int, default=30, help="groups smaller than this get a small-sample flag")
    p.add_argument("-f", "--format", choices=["text", "md", "json"], default="text")
    p.add_argument("--report", metavar="DIR", help="write report.md, impact.svg and audit.json to DIR")
    p.add_argument("--strict", action="store_true", help="exit 1 if any group shows adverse impact (CI gate)")
    p.add_argument("-V", "--version", action="version", version=f"fairlens {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cols = [c.strip() for c in args.groups.split(",") if c.strip()]
    attrs = cols + (["*".join(pair) for pair in itertools.combinations(cols, 2)] if args.intersect else [])
    try:
        stats, seen = tally(read_rows(args.csv), attrs, args.outcome, args.label, args.positive)
    except (OSError, KeyError, ValueError) as e:
        print(f"fairlens: error: {e.args[-1] if isinstance(e, KeyError) else e}", file=sys.stderr)
        return 2
    if not seen:
        print("fairlens: error: no data rows", file=sys.stderr)
        return 2

    audits = [analyse(a, g, args.threshold, args.min_n, bool(args.label)) for a, g in stats.items() if g]
    if not audits:
        print("fairlens: error: every row is missing the group columns", file=sys.stderr)
        return 2

    source = Path(args.csv).name
    if args.report:
        out = Path(args.report)
        out.mkdir(parents=True, exist_ok=True)
        (out / "impact.svg").write_text(impact_svg(audits), encoding="utf-8")
        (out / "report.md").write_text(to_markdown(audits, seen, source, "impact.svg"), encoding="utf-8")
        (out / "audit.json").write_text(to_json(audits, seen) + "\n", encoding="utf-8")

    render = {"text": lambda: to_text(audits, seen),
              "md": lambda: to_markdown(audits, seen, source),
              "json": lambda: to_json(audits, seen)}[args.format]
    print(render())
    if args.report:
        print(f"\nReport written to {args.report}/", file=sys.stderr)

    return 1 if args.strict and any(a.flagged for a in audits) else 0


if __name__ == "__main__":
    sys.exit(main())
