"""Command line interface.

    python -m parity decisions.csv --outcome hired --groups sex race --intersect
"""

import argparse
import sys

from .data import load_rows
from .metrics import audit
from .report import render_html, render_json, render_markdown, render_text, svg_chart, verdict

RENDERERS = {"md": render_markdown, "json": render_json, "html": render_html}


def build_parser():
    p = argparse.ArgumentParser(
        prog="parity",
        description="Audit an automated decision system for disparate impact (NYC LL144 / four-fifths rule).")
    p.add_argument("csv", help="decision log: one row per person")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--outcome", metavar="COL", help="yes/no decision column (selection mode)")
    what.add_argument("--score", metavar="COL", help="numeric score column (scoring mode)")
    p.add_argument("--groups", nargs="+", required=True, metavar="COL",
                   help="protected-attribute column(s), audited one by one")
    p.add_argument("--intersect", action="store_true",
                   help="also audit the intersection of all --groups (e.g. sex × race)")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--min-share", type=float, default=0.02,
                   help="groups below this share are marked small (default 0.02, per LL144)")
    p.add_argument("--format", choices=["text", *RENDERERS], default="text")
    p.add_argument("-o", "--output", metavar="FILE", help="write the report here instead of stdout")
    p.add_argument("--svg", metavar="PREFIX", help="also write one SVG chart per audit: PREFIX-<attr>.svg")
    p.add_argument("--strict", action="store_true", help="exit 1 on 'review' as well as 'flag'")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        rows = load_rows(args.csv)
        sets = [[g] for g in args.groups]
        if args.intersect and len(args.groups) > 1:
            sets.append(args.groups)
        audits = [audit(rows, cols, outcome=args.outcome, score=args.score, threshold=args.threshold,
                        alpha=args.alpha, min_share=args.min_share) for cols in sets]
    except (OSError, ValueError) as e:
        print(f"parity: error: {e}", file=sys.stderr)
        return 2

    if args.format == "text":
        color = not args.output and sys.stdout.isatty()
        report = render_text(audits, args.csv, color=color)
    else:
        report = RENDERERS[args.format](audits, args.csv)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(report)

    if args.svg:
        for a, cols in zip(audits, sets):
            path = f"{args.svg}-{'-'.join(cols)}.svg"
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg_chart(a, standalone=True))
            print(f"wrote {path}", file=sys.stderr)

    state, _ = verdict(audits)
    return 1 if state == "fail" or (args.strict and state == "review") else 0


if __name__ == "__main__":
    sys.exit(main())
