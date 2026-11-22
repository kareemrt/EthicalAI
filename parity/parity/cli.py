"""Command-line interface: ``parity <csv> --group COL --decision COL``."""

import argparse
import sys
from pathlib import Path

from . import __version__, report
from .data import load
from .metrics import FAIL, WARN, Policy, run

EPILOG = """examples:
  parity hiring.csv --group gender --decision hired
  parity loans.csv  --group race --group sex --decision score --cutoff 0.6
  parity preds.csv  --group age_band --decision pred --label actual -f html -o audit.html

exit codes: 0 pass · 1 adverse impact found · 2 needs review (with --strict) · 3 bad input
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="parity",
        description="Audit automated decisions for disparate impact.",
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("csv", help="CSV file with one row per decision")
    p.add_argument("-g", "--group", action="append", required=True, metavar="COL",
                   help="protected attribute column (repeat for intersectional audit)")
    p.add_argument("-d", "--decision", required=True, metavar="COL",
                   help="outcome column (1/yes/true/hired... = favourable)")
    p.add_argument("-l", "--label", metavar="COL",
                   help="optional ground-truth column (was the person qualified?)")
    p.add_argument("--cutoff", type=float, metavar="X",
                   help="treat decision as a score; favourable if score >= X")
    p.add_argument("-f", "--format", choices=["text", "md", "json", "html"], default="text")
    p.add_argument("-o", "--output", metavar="FILE", help="write report to FILE")
    p.add_argument("--threshold", type=float, default=0.80, help="impact-ratio floor (0.80)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (0.05)")
    p.add_argument("--min-n", type=int, default=30, help="small-sample cutoff (30)")
    p.add_argument("--max-gap", type=float, default=0.10, help="TPR/FPR gap tolerance (0.10)")
    p.add_argument("--strict", action="store_true", help="exit non-zero on warnings too")
    p.add_argument("-V", "--version", action="version", version=f"parity {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    policy = Policy(args.threshold, args.alpha, args.min_n, args.max_gap)
    try:
        records = load(args.csv, args.group, args.decision, args.label, args.cutoff)
    except (OSError, ValueError) as e:
        print(f"parity: {e}", file=sys.stderr)
        return 3

    audits = run(records, args.group, policy)
    to_file = bool(args.output)
    out = {
        "text": lambda: report.to_text(audits, color=not to_file and sys.stdout.isatty()),
        "md": lambda: report.to_markdown(audits, args.csv, policy),
        "json": lambda: report.to_json(audits, policy),
        "html": lambda: report.to_html(audits, args.csv, policy),
    }[args.format]()

    if to_file:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
        print(f"parity: {report.LABEL[report.overall(audits)]} → {args.output}", file=sys.stderr)
    else:
        print(out)

    status = report.overall(audits)
    return 1 if status == FAIL else 2 if (status == WARN and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
