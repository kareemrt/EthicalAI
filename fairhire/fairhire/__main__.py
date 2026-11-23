"""Command-line entry point:  python -m fairhire data.csv --outcome hired --attrs sex race"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .audit import SEVERITY, run_audit
from .report import render_html, render_json, render_markdown, render_text


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="fairhire",
        description="Audit hiring decisions for adverse impact (NYC LL144 / EEOC four-fifths rule).")
    p.add_argument("csv", type=Path, help="CSV file, one row per candidate")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--outcome", help="binary column (1/yes/true/hired/selected = selected)")
    target.add_argument("--score", help="numeric column; 'selected' = scored above the median")
    p.add_argument("--attrs", nargs="+", required=True, help="protected-attribute columns")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio floor (default 0.8)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--min-share", type=float, default=0.02,
                   help="exclude groups below this share of records from flagging (default 0.02)")
    p.add_argument("--no-intersect", action="store_true", help="skip the intersectional breakdown")
    p.add_argument("--html", type=Path, help="write a self-contained HTML report")
    p.add_argument("--md", type=Path, help="write a Markdown report")
    p.add_argument("--json", type=Path, help="write machine-readable JSON")
    p.add_argument("--fail-on", choices=["never", "watch", "adverse"], default="never",
                   help="exit 1 if the audit reaches this status (for CI gates)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        with args.csv.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        audit = run_audit(rows, args.attrs, args.outcome, args.score, not args.no_intersect,
                          args.threshold, args.alpha, args.min_share)
    except (OSError, ValueError) as exc:
        print(f"fairhire: error: {exc}", file=sys.stderr)
        return 2

    print(render_text(audit))
    for path, render in ((args.html, render_html), (args.md, render_markdown), (args.json, render_json)):
        if path:
            path.write_text(render(audit), encoding="utf-8")
            print(f"→ wrote {path}")

    if args.fail_on != "never" and SEVERITY[audit.status] >= SEVERITY[args.fail_on]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
