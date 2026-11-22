"""Command line: `plainspeak notice.txt [--html report.html] [--fail-under 70]`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyze import analyze, fix
from .report import to_html, to_json, to_text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="plainspeak",
        description="Check whether a notice can be understood and acted on by the person who receives it.",
    )
    p.add_argument("files", nargs="+", help="text files to check, or - for stdin")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON")
    p.add_argument("--html", metavar="PATH", help="write an HTML report (single file only)")
    p.add_argument("--fix", action="store_true", help="print a draft with jargon swapped for plain words")
    p.add_argument("--target-grade", type=float, default=8.0, metavar="N", help="target reading grade (default 8)")
    p.add_argument("--fail-under", type=int, metavar="SCORE", help="exit 1 if any score is below SCORE (for CI)")
    p.add_argument("--version", action="version", version=f"plainspeak {__version__}")
    a = p.parse_args(argv)

    docs = []
    for name in a.files:
        if name == "-":
            docs.append(("<stdin>", sys.stdin.read()))
        else:
            path = Path(name)
            if not path.is_file():
                p.error(f"no such file: {name}")
            docs.append((name, path.read_text(encoding="utf-8")))

    if a.fix:
        for _, text in docs:
            sys.stdout.write(fix(text))
        return 0

    reports = [analyze(text, name, a.target_grade) for name, text in docs]

    if a.html:
        if len(reports) != 1:
            p.error("--html takes exactly one input file")
        Path(a.html).write_text(to_html(reports[0]), encoding="utf-8")
        print(f"wrote {a.html}", file=sys.stderr)

    if a.json:
        print(to_json(reports))
    else:
        for r in reports:
            print(to_text(r))

    if a.fail_under is not None:
        failing = [r for r in reports if r.score < a.fail_under]
        for r in failing:
            print(f"FAIL {r.source}: {r.score} < {a.fail_under}", file=sys.stderr)
        return 1 if failing else 0
    return 0
