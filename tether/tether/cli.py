"""Command line: tether ANSWER SOURCE [SOURCE ...]"""
import argparse
import pathlib
import sys

from . import __version__, report
from .core import Source, check

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".text", ""}


def load_sources(paths):
    """Files are taken as given; directories contribute their text files, sorted."""
    files = []
    for p in map(pathlib.Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES)
        else:
            files.append(p)
    return [Source(f.name, f.read_text(encoding="utf-8", errors="replace")) for f in files]


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="tether",
        description="Check that every sentence of an AI-generated answer is backed by your sources.")
    ap.add_argument("answer", help="file with the answer to check, or - for stdin")
    ap.add_argument("sources", nargs="+", help="source files or directories; [n] citations follow this order")
    ap.add_argument("--html", metavar="FILE", help="also write a self-contained HTML report")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    ap.add_argument("--fail-under", type=float, metavar="X",
                    help="exit 1 if groundedness is below X (0-1); handy in CI pipelines")
    ap.add_argument("--supported", type=float, default=0.7, help="score needed for 'supported' (default 0.7)")
    ap.add_argument("--weak", type=float, default=0.4, help="score needed for 'weak' (default 0.4)")
    ap.add_argument("-v", "--verbose", action="store_true", help="show evidence for every claim")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=f"tether {__version__}")
    args = ap.parse_args(argv)

    answer = sys.stdin.read() if args.answer == "-" else pathlib.Path(args.answer).read_text(encoding="utf-8")
    sources = load_sources(args.sources)
    if not sources:
        ap.error("no readable source files found")
    result = check(answer, sources, supported=args.supported, weak=args.weak)

    print(report.to_json(result) if args.json else
          report.terminal(result, color=False if args.no_color else None, verbose=args.verbose))
    if args.html:
        pathlib.Path(args.html).write_text(report.to_html(result), encoding="utf-8")
        print(f"\nHTML report written to {args.html}", file=sys.stderr)
    if args.fail_under is not None and result.groundedness < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
