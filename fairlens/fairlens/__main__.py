"""Command-line entry point:  python -m fairlens decisions.csv --outcome hired --attrs sex race"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, report
from .data import load
from .metrics import run_audit


def parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="fairlens",
        description="Audit an automated decision system for adverse impact "
                    "(EEOC four-fifths rule / NYC Local Law 144 impact ratios).")
    p.add_argument("csv", help="decision log, one row per person")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--outcome", help="yes/no decision column (e.g. hired)")
    src.add_argument("--score", help="numeric score column; 'selected' = above median")
    p.add_argument("--attrs", nargs="+", required=True, help="protected-attribute columns")
    p.add_argument("--label", help="optional ground-truth column (e.g. qualified) for error rates")
    p.add_argument("--intersect", action="store_true", help="also audit attribute combinations")
    p.add_argument("--title", default="Bias audit", help="report title")
    p.add_argument("--html", type=Path, help="write a self-contained HTML report")
    p.add_argument("--md", type=Path, help="write a Markdown report")
    p.add_argument("--json", type=Path, help="write machine-readable results")
    p.add_argument("--strict", action="store_true",
                   help="exit with code 1 on any 'fail' (use as a CI / deployment gate)")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--version", action="version", version=f"fairlens {__version__}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    try:
        ds = load(args.csv, outcome=args.outcome, score=args.score, label=args.label)
        missing = [a for a in args.attrs if a not in ds.rows[0]]
        if missing:
            raise ValueError(f"Attribute column(s) not found: {', '.join(missing)}")
    except (OSError, ValueError) as err:
        print(f"fairlens: {err}", file=sys.stderr)
        return 2

    audit = run_audit(ds, args.attrs, intersect=args.intersect)
    print(report.terminal(audit, color=sys.stdout.isatty() and not args.no_color))

    outputs = {args.html: report.html, args.md: report.markdown}
    for path, render in outputs.items():
        if path:
            path.write_text(render(audit, args.title), encoding="utf-8")
            print(f"  → wrote {path}")
    if args.json:
        args.json.write_text(report.to_json(audit), encoding="utf-8")
        print(f"  → wrote {args.json}")

    return 1 if args.strict and audit.status == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
