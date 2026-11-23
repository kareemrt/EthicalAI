"""Command-line interface: `ghostcite FILE [--online] [--format text|md|json]`."""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__, report
from .core import check_text
from .models import FAILING, UNMATCHED

KINDS = ["doi", "arxiv", "isbn", "pmid", "url", "ref"]


def parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ghostcite",
        description="Catch fabricated citations in AI-generated text.",
        epilog="Exit status: 0 = clean, 1 = suspect citations found, 2 = usage error.",
    )
    p.add_argument("files", nargs="*", default=["-"], help="text/markdown files ('-' = stdin)")
    p.add_argument("-o", "--online", action="store_true",
                   help="verify against Crossref, doi.org, arXiv, PubMed and Open Library")
    p.add_argument("-f", "--format", choices=["text", "md", "json"], default="text")
    p.add_argument("--only", metavar="KINDS",
                   help=f"comma-separated subset of: {','.join(KINDS)}")
    p.add_argument("--strict", action="store_true", help="also fail on 'unmatched' references")
    p.add_argument("-j", "--workers", type=int, default=4, help="parallel lookups (default 4)")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("-V", "--version", action="version", version=f"ghostcite {__version__}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    kinds = set(args.only.split(",")) if args.only else None
    if kinds and not kinds <= set(KINDS):
        print(f"ghostcite: unknown kind(s): {', '.join(sorted(kinds - set(KINDS)))}",
              file=sys.stderr)
        return 2
    color = (sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ)
    failing = FAILING | ({UNMATCHED} if args.strict else set())
    exit_code = 0

    for path in args.files:
        try:
            text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        except OSError as e:
            print(f"ghostcite: {e}", file=sys.stderr)
            return 2
        name = "stdin" if path == "-" else path
        findings = check_text(text, online=args.online, workers=args.workers, kinds=kinds)
        render = {"text": lambda: report.text(findings, color, name),
                  "md": lambda: report.markdown(findings, name),
                  "json": lambda: report.as_json(findings, name)}[args.format]
        print(render())
        if any(f.verdict in failing for f in findings):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
