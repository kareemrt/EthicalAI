"""Command line: `candor PAGE_OR_URL... [--format text|json|md|html] [--fail-on LEVEL]`."""
from __future__ import annotations

import argparse
import sys

from . import __version__, report
from .rules import RULES
from .scanner import SEVERITIES, expand, load, scan_html

FORMATS = {"text": report.text, "json": report.as_json, "md": report.markdown, "html": report.html}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="candor", description="Find manipulative design (dark patterns) in web pages.")
    p.add_argument("targets", nargs="*", help="HTML files, folders or http(s) URLs")
    p.add_argument("-f", "--format", choices=FORMATS, default="text")
    p.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    p.add_argument("--fail-on", choices=SEVERITIES, metavar="LEVEL",
                   help="exit 1 if any finding is at least this severe (high|medium|low) — for CI")
    p.add_argument("--rules", help="comma-separated rule ids to run (default: all)")
    p.add_argument("--list-rules", action="store_true", help="show every rule and exit")
    p.add_argument("--version", action="version", version=f"candor {__version__}")
    a = p.parse_args(argv)

    if a.list_rules:
        for r in RULES:
            print(f"{r.id:<22} {r.severity:<7} {r.summary}\n{'':<30}{r.reference}")
        return 0
    if not a.targets:
        p.error("give at least one file, folder or URL (try examples/)")

    only = set(a.rules.split(",")) if a.rules else None
    reports = []
    for t in expand(a.targets):
        try:
            reports.append(scan_html(load(t), t, only))
        except (OSError, ValueError) as e:
            print(f"candor: cannot read {t}: {e}", file=sys.stderr)
            return 2

    out = FORMATS[a.format](reports)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as fh:
            fh.write(out if a.format == "text" else out + "\n")
    else:
        sys.stdout.write(out if out.endswith("\n") else out + "\n")

    if a.fail_on:
        limit = SEVERITIES.index(a.fail_on)
        if any(SEVERITIES.index(f.severity) <= limit for r in reports for f in r.findings):
            return 1
    return 0
