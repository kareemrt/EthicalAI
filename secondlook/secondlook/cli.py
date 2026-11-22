"""Command line: check a message from a file, an argument, or stdin.

    python -m secondlook "Your package is on hold, pay $1.99 at usps-redeliver.top"
    python -m secondlook message.txt --json
    pbpaste | python -m secondlook
    python -m secondlook --serve            # local web page on 127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

from .engine import Report, check

COLORS = {"high": "\033[1;31m", "caution": "\033[1;33m", "low": "\033[1;32m"}
DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


def render(report: Report, color: bool = True) -> str:
    c = (lambda code, s: f"{code}{s}{RESET}") if color else (lambda code, s: s)
    pct = round(report.risk * 100)
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    wrap = lambda s, ind: textwrap.fill(s, 78, initial_indent=ind, subsequent_indent=ind)

    tone = COLORS[report.level]
    lines = ["", f"{c(tone, f'  {report.headline.upper()}  ')}  {c(tone, bar)} {pct}% risk", ""]
    if report.flags:
        lines.append(c(BOLD, "  What we noticed"))
        for f in report.flags:
            lines.append(f"  • {c(BOLD, f.title)}")
            lines.append(wrap(f.why, "    "))
            lines.append(c(DIM, wrap(f'found: "{f.evidence}"', "    ")))
        lines.append("")
    lines.append(c(BOLD, "  What to do"))
    lines += [wrap(a, "    ").replace("    ", "  → ", 1) for a in report.advice]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="secondlook", description=__doc__.split("\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("message", nargs="?", help="message text, or a path to a text file")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON")
    p.add_argument("--serve", action="store_true", help="start the local web page")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)

    if args.serve:
        from .web import serve
        serve(args.port)
        return 0

    if args.message and Path(args.message).is_file():
        text = Path(args.message).read_text(encoding="utf-8", errors="replace")
    elif args.message:
        text = args.message
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        p.print_help()
        return 2

    report = check(text)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        print(render(report, color))
    return {"low": 0, "caution": 1, "high": 3}[report.level]
