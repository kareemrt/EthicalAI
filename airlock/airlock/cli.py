"""Command line: `airlock scan PATH...` and `airlock sanitize PATH`.

Exit codes: 0 = nothing at/above --fail-on, 1 = findings at/above it, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .findings import Report, Severity
from .sanitize import sanitize
from .scanner import scan

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".html", ".htm", ".xml", ".json", ".jsonl",
                 ".csv", ".tsv", ".yaml", ".yml", ".eml", ".rst", ".svg", ".srt", ".vtt"}

_COLORS = {Severity.HIGH: "31", Severity.MEDIUM: "33", Severity.LOW: "36",
           "dangerous": "1;31", "suspicious": "1;33", "clean": "1;32", "dim": "2"}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "sanitize":
            name, text = next(_read(args.path))
            sys.stdout.write(sanitize(text))
            return 0
        reports = [scan(text, name) for name, text in _iter_inputs(args.paths)]
    except OSError as e:
        print(f"airlock: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False))
    else:
        paint = _painter(args.color)
        for r in reports:
            if r.findings or not args.quiet:
                print(_render(r, paint))
        if len(reports) > 1:
            flagged = sum(bool(r.findings) for r in reports)
            print(paint("dim", f"{len(reports)} inputs scanned, {flagged} flagged."))

    threshold = Severity[args.fail_on.upper()]
    return int(any(r.worst and r.worst >= threshold for r in reports))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="airlock", description="Check untrusted text for prompt "
                                "injection before an AI agent reads it.")
    p.add_argument("--version", action="version", version=f"airlock {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="report injection risks in files, folders or stdin")
    s.add_argument("paths", nargs="*", default=["-"], help="files or folders ('-' = stdin)")
    s.add_argument("--format", choices=("text", "json"), default="text")
    s.add_argument("--fail-on", choices=("low", "medium", "high"), default="medium",
                   help="lowest severity that makes the exit code 1 (default: medium)")
    s.add_argument("--quiet", "-q", action="store_true", help="only print inputs with findings")
    s.add_argument("--color", choices=("auto", "always", "never"), default="auto")

    z = sub.add_parser("sanitize", help="print a neutralized copy of one input")
    z.add_argument("path", nargs="?", default="-", help="file ('-' = stdin)")
    return p


def _iter_inputs(paths):
    for raw in paths:
        path = Path(raw)
        if raw != "-" and path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES:
                    yield from _read(str(f))
        else:
            yield from _read(raw)


def _read(raw: str):
    if raw == "-":
        yield "<stdin>", sys.stdin.read()
    else:
        yield raw, Path(raw).read_text(encoding="utf-8", errors="replace")


def _painter(mode: str):
    on = mode == "always" or (mode == "auto" and sys.stdout.isatty() and "NO_COLOR" not in os.environ)
    return (lambda key, s: f"\033[{_COLORS[key]}m{s}\033[0m") if on else (lambda key, s: s)


def _render(r: Report, paint) -> str:
    head = (f"{r.source}  {paint(r.verdict, r.verdict.upper())}  risk {r.score}/100"
            f"  ({len(r.findings)} finding{'s' * (len(r.findings) != 1)})")
    lines = [head]
    for f in r.findings:
        lines.append(f"  {paint(f.severity, f'{str(f.severity).upper():<6}')} "
                     f"{f'{f.line}:{f.col}':>7}  {f.rule:<28} {f.message}")
        if f.excerpt:
            lines.append(paint("dim", f"{'':17}└ {f.excerpt}"))
    return "\n".join(lines) + "\n"
