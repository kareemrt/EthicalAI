"""Command-line interface: `candor scan` and `candor rules`."""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .patterns import PATTERNS, SEVERITIES
from .report import RENDERERS, render_text
from .scanner import Report, scan_paths, scan_text


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="candor", description="Lint UI markup and copy for deceptive design patterns.")
    ap.add_argument("--version", action="version", version=f"candor {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="scan files or directories ('-' reads stdin)")
    scan.add_argument("paths", nargs="+")
    scan.add_argument("-f", "--format", choices=RENDERERS, default="text")
    scan.add_argument("-o", "--output", help="write report to a file instead of stdout")
    scan.add_argument("--min-severity", choices=SEVERITIES, default="low", help="hide findings below this level")
    scan.add_argument("--fail-under", type=int, default=0, metavar="N", help="exit 1 if the score is below N (for CI)")
    scan.add_argument("--no-color", action="store_true")

    sub.add_parser("rules", help="list every pattern Candor detects")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.cmd == "rules":
        for p in PATTERNS:
            print(f"{p.severity:<7}{p.id:<20}{p.name}  ·  {p.why}")
        return 0

    if args.paths == ["-"]:
        report = Report([scan_text(sys.stdin.read(), "<stdin>")])
    else:
        report = scan_paths(args.paths, args.min_severity)
        if not report.files:
            print("candor: no scannable files found", file=sys.stderr)
            return 2

    if args.format == "text":
        color = not args.no_color and not args.output and sys.stdout.isatty() and "NO_COLOR" not in os.environ
        out = render_text(report, color)
    else:
        out = RENDERERS[args.format](report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"candor: score {report.score}/100 (grade {report.grade}) → {args.output}", file=sys.stderr)
    else:
        print(out)
    return 1 if report.score < args.fail_under else 0
