"""Command-line interface: `equitas audit ...` and `equitas sample ...`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, data, metrics, report, sample

EPILOG = """examples:
  equitas sample -o hiring.csv
  equitas audit hiring.csv --groups sex race --outcome advanced --label qualified
  equitas audit hiring.csv --groups sex race --score score -f html -o report.html
  equitas audit decisions.csv --groups gender --outcome approved --strict   # CI gate
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="equitas", description="Audit automated decisions for adverse impact.",
                                epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"equitas {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="audit a CSV of decisions")
    a.add_argument("csv", type=Path, help="one row per decision")
    a.add_argument("-g", "--groups", nargs="+", required=True, metavar="COL", help="protected-attribute columns")
    src = a.add_mutually_exclusive_group(required=True)
    src.add_argument("--outcome", metavar="COL", help="yes/no column: was the decision favourable?")
    src.add_argument("--score", metavar="COL", help="numeric score column (favourable when >= threshold)")
    a.add_argument("--threshold", type=float, help="score cut-off (default: median, as in NYC LL144)")
    a.add_argument("--label", metavar="COL", help="optional yes/no ground truth, enables error-rate metrics")
    a.add_argument("--ratio", type=float, default=0.8, help="impact-ratio threshold (default 0.8)")
    a.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    a.add_argument("--min-share", type=float, default=0.02, help="exclude groups below this share (default 0.02)")
    a.add_argument("--no-intersections", action="store_true", help="skip the combined-attribute audit")
    a.add_argument("-f", "--format", choices=report.RENDERERS, help="output format (default: from -o suffix, else text)")
    a.add_argument("-o", "--out", type=Path, help="write to file instead of stdout")
    a.add_argument("--strict", action="store_true", help="exit 1 if adverse impact is found")

    s = sub.add_parser("sample", help="write a synthetic, deliberately biased hiring dataset")
    s.add_argument("-n", type=int, default=2000, help="rows (default 2000)")
    s.add_argument("--seed", type=int, default=7)
    s.add_argument("--fair", action="store_true", help="no injected bias (an unbiased baseline)")
    s.add_argument("-o", "--out", type=Path, help="write to file instead of stdout")
    return p


def _format(args: argparse.Namespace) -> str:
    if args.format:
        return args.format
    suffix = args.out.suffix.lstrip(".").lower() if args.out else ""
    return {"htm": "html", "markdown": "md"}.get(suffix, suffix) if suffix in {*report.RENDERERS, "htm", "markdown"} else "text"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "sample":
        sample.write(sample.generate(args.n, args.seed, args.fair), args.out)
        return 0

    try:
        records, outcome = data.load(args.csv, args.groups, args.outcome, args.score, args.threshold, args.label)
    except (OSError, ValueError) as e:
        print(f"equitas: error: {e}", file=sys.stderr)
        return 2

    cfg = metrics.Config(ratio=args.ratio, alpha=args.alpha, min_share=args.min_share,
                         intersections=not args.no_intersections)
    result = metrics.run(records, args.groups, outcome, args.csv.name, cfg)
    text = report.RENDERERS[_format(args)](result)

    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"{report.ICON[result.status]} {report.LABEL[result.status]} → {args.out}", file=sys.stderr)
    else:
        print(text)
    return 1 if args.strict and result.status == metrics.FAIL else 0
