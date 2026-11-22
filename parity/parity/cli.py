"""Command-line entry point.

    parity audit decisions.csv --outcome hired --protected sex race --html report.html

Exit code is 0 when every group passes, 1 when any group fails — so it can gate CI.
"""

import argparse
import sys
from pathlib import Path

from . import report
from .data import load_csv, outcomes
from .metrics import ALPHA, FOUR_FIFTHS, MIN_SHARE, audit_attribute, intersect
from .proxies import MODERATE, find_proxies

RESET, COLORS = "\033[0m", {"reference": "\033[90m", "pass": "\033[32m",
                            "watch": "\033[33m", "fail": "\033[31m", "excluded": "\033[90m"}


def fail_usage(msg: str):
    print(f"parity: error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def run_audit(args) -> dict:
    rows = load_csv(args.csv)
    if not rows:
        fail_usage("CSV has no rows")
    needed = args.protected + [c for c in (args.outcome, args.score) if c]
    missing = [c for c in needed if c not in rows[0]]
    if missing:
        fail_usage(f"missing column(s): {', '.join(missing)}")

    selected = outcomes(rows, args.outcome, args.score)
    attributes = [[c] for c in args.protected]
    if args.intersectional and len(args.protected) > 1:
        attributes.append(args.protected)

    sections = []
    for cols in attributes:
        groups = intersect(rows, cols)
        results = audit_attribute(groups, selected, args.threshold, args.min_share, args.alpha)
        sections.append({"attribute": " × ".join(cols), "groups": [r.as_dict() for r in results]})

    proxies = []
    if not args.no_proxies:
        exclude = [c for c in (args.outcome, args.score) if c] + args.ignore
        proxies = [p for p in find_proxies(rows, args.protected, exclude) if p["v"] >= MODERATE]

    measure = f"selection rate of '{args.outcome}'" if args.outcome else f"scoring rate of '{args.score}' (> median)"
    return report.build(args.title or Path(args.csv).stem, len(rows), measure,
                        args.threshold, args.min_share, sections, proxies)


def print_summary(audit: dict, color: bool) -> None:
    c = (lambda s, t: f"{COLORS[s]}{t}{RESET}") if color else (lambda s, t: t)
    print(f"\n  Parity audit · {audit['title']} · {audit['records']:,} records\n")
    for sec in audit["sections"]:
        print(f"  {sec['attribute']}")
        rated = [g for g in sec["groups"] if g["status"] != "excluded"]
        excluded = len(sec["groups"]) - len(rated)
        for g in rated:
            ir = f"{g['impact_ratio']:.2f}"
            bar = "█" * round(min(g["impact_ratio"], 1) * 20)
            line = f"{report.STATUS_ICON[g['status']]} {g['group'][:30]:<30} {g['rate']:>6.1%}  IR {ir}  {bar}"
            print("    " + c(g["status"], line))
        if excluded:
            print("    " + c("excluded", f"– {excluded} small group(s) excluded (<{audit['min_share']:.0%} of records)"))
        print()
    if audit["proxies"]:
        print("  Proxy features")
        for p in audit["proxies"]:
            s = "fail" if p["level"] == "strong" else "watch"
            print("    " + c(s, f"{p['feature']:<24} → {p['attribute']:<16} V = {p['v']:.2f} ({p['level']})"))
        print()
    v = report.verdict(audit)
    print("  " + c(v, f"Verdict: {v.upper()}") + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="parity", description="Bias audits for automated decision systems.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="audit a CSV of decisions")
    a.add_argument("csv", help="one row per person/decision")
    out = a.add_mutually_exclusive_group(required=True)
    out.add_argument("--outcome", help="binary outcome column (1/0, yes/no, hired, ...)")
    out.add_argument("--score", help="numeric score column; 'selected' = above median (LL144 scoring rate)")
    a.add_argument("--protected", nargs="+", required=True, help="protected attribute columns")
    a.add_argument("--intersectional", action="store_true", help="also audit the combination of all protected columns")
    a.add_argument("--threshold", type=float, default=FOUR_FIFTHS, help="impact-ratio threshold (default 0.8)")
    a.add_argument("--min-share", type=float, default=MIN_SHARE, help="exclude groups below this share (default 0.02)")
    a.add_argument("--alpha", type=float, default=ALPHA, help="significance level (default 0.05)")
    a.add_argument("--ignore", nargs="*", default=[], help="columns to skip in proxy detection (e.g. IDs)")
    a.add_argument("--no-proxies", action="store_true", help="skip proxy detection")
    a.add_argument("--title", help="report title (default: CSV filename)")
    a.add_argument("--html", metavar="PATH", help="write a self-contained HTML report")
    a.add_argument("--md", metavar="PATH", help="write a Markdown report")
    a.add_argument("--json", metavar="PATH", help="write machine-readable JSON ('-' for stdout)")
    a.add_argument("--quiet", action="store_true", help="no terminal summary")
    args = ap.parse_args(argv)

    try:
        audit = run_audit(args)
    except (ValueError, OSError) as err:
        fail_usage(str(err))
    for path, render in ((args.html, report.to_html), (args.md, report.to_markdown), (args.json, report.to_json)):
        if path == "-":
            print(render(audit))
        elif path:
            Path(path).write_text(render(audit), encoding="utf-8")
    if not args.quiet and args.json != "-":
        print_summary(audit, color=sys.stdout.isatty())
    return 1 if report.verdict(audit) == "fail" else 0
