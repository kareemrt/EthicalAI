"""Command line: ``candor PATH_OR_URL ... [--format html] [--fail-on medium]``."""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from . import __version__
from .report import FORMATS
from .rules import RULES, SEVERITIES
from .scanner import scan

HTML_EXT = {".html", ".htm", ".xhtml"}


def load(target: str) -> list[tuple[str, str]]:
    """Return ``(source, html)`` pairs for a URL, a file, or every HTML file in a folder."""
    if target.startswith(("http://", "https://")):
        req = urllib.request.Request(target, headers={"User-Agent": f"candor/{__version__}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return [(target, resp.read().decode(charset, "replace"))]
    path = Path(target)
    files = sorted(p for p in path.rglob("*") if p.suffix.lower() in HTML_EXT) if path.is_dir() else [path]
    return [(str(p), p.read_text(encoding="utf-8", errors="replace")) for p in files]


def list_rules() -> str:
    width = max(len(r.name) for r in RULES)
    return "\n".join(f"{r.id}  {r.severity:<6}  {r.name:<{width}}  {r.category}" for r in RULES)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="candor", description="Find deceptive design patterns (dark patterns) in HTML.")
    ap.add_argument("targets", nargs="*", help="HTML files, folders, or http(s) URLs")
    ap.add_argument("-f", "--format", choices=FORMATS, default="text")
    ap.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    ap.add_argument("--fail-on", choices=(*SEVERITIES, "never"), default="high",
                    help="exit 1 if any finding is at least this severe (default: high)")
    ap.add_argument("--only", help="comma-separated rule IDs to run, e.g. CD01,CD10")
    ap.add_argument("--rules", action="store_true", help="list all rules and exit")
    ap.add_argument("--version", action="version", version=f"candor {__version__}")
    args = ap.parse_args(argv)

    if args.rules:
        print(list_rules())
        return 0
    if not args.targets:
        ap.error("give at least one file, folder or URL (or --rules)")

    only = {s.strip().upper() for s in args.only.split(",")} if args.only else None
    try:
        pages = [page for t in args.targets for page in load(t)]
    except (OSError, ValueError) as e:
        print(f"candor: {e}", file=sys.stderr)
        return 2
    reports = [scan(html, src, only) for src, html in pages]

    render = FORMATS[args.format]
    color = args.format == "text" and not args.output and sys.stdout.isatty()
    out = render(reports, color) if args.format == "text" else render(reports)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"candor: wrote {args.output}", file=sys.stderr)
    else:
        print(out)

    if args.fail_on == "never":
        return 0
    limit = SEVERITIES.index(args.fail_on)
    return int(any(SEVERITIES.index(f.rule.severity) <= limit for r in reports for f in r.findings))
