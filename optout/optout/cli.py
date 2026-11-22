"""Command line: `optout check <site>` and `optout generate <categories>`."""

import argparse
import sys

from . import __version__, audit, generate, report
from .agents import ANSWER, TRAINING, USER
from .site import open_site


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="optout", description="Audit and fix a website's AI-crawler opt-out.")
    p.add_argument("--version", action="version", version=f"optout {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="audit a live URL or a local build folder")
    c.add_argument("target", help="https://example.com, example.com, or ./public")
    c.add_argument("--path", default="/", help="page path to evaluate (default: /)")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    c.add_argument("-v", "--verbose", action="store_true", help="list every crawler, not just open ones")
    c.add_argument("--strict", action="store_true",
                   help="exit 1 if any training crawler is open or a search engine is blocked (for CI)")
    c.add_argument("--no-color", action="store_true")

    g = sub.add_parser("generate", help="print opt-out rules")
    g.add_argument("categories", nargs="*", default=[TRAINING],
                   help=f"any of: {TRAINING} (default), {ANSWER}, {USER}")
    g.add_argument("--tdmrep", action="store_true", help="also print tdmrep.json, meta tags and headers")
    g.add_argument("--policy", help="URL of your licensing policy, embedded in tdmrep.json")

    a = p.parse_args(argv)
    if a.cmd == "check":
        result = audit.run(open_site(a.target), a.path)
        print(report.as_json(result) if a.json
              else report.text(result, color=False if a.no_color else None, verbose=a.verbose), end="")
        return 1 if a.strict and result.problems else 0

    try:
        print(generate.robots_txt(a.categories))
    except ValueError as e:
        print(f"optout: {e}", file=sys.stderr)
        return 2
    if a.tdmrep:
        print("# --- /.well-known/tdmrep.json ---\n" + generate.tdmrep_json(a.policy))
        print("# --- <head> meta tags ---\n" + generate.html_meta())
        print("# --- HTTP response headers ---\n" + generate.headers(), end="")
    return 0
