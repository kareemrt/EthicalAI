"""Command-line interface.

Examples
--------
Generate demo data and audit it::

    python -m auditlens demo --out examples/

Audit your own decisions::

    python -m auditlens audit decisions.csv --outcome advanced \\
        --attr "Sex=sex" --attr "Race/Ethnicity=race" \\
        --intersect "Sex,Race/Ethnicity" --period quarter \\
        --html report.html --md report.md
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import __version__, synth
from .audit import audit, load_csv
from .report import to_html, to_json, to_markdown, write_charts


def _parse_attr(spec: str):
    if "=" in spec:
        name, col = spec.split("=", 1)
        return name.strip(), col.strip()
    return spec.strip(), spec.strip()


def _add_audit_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio threshold (default 0.8, the four-fifths rule)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument("--min-share", type=float, default=0.02, help="exclude categories below this share of the sample (default 0.02)")
    p.add_argument("--min-group-size", type=int, default=30, help="minimum records before a group can be flagged (default 30)")
    p.add_argument("--suppress-below", type=int, default=0, help="mask counts below N in reports to protect privacy (e.g. 5)")
    p.add_argument("--fail-on-adverse", action="store_true", help="exit with status 2 if adverse impact is found (for CI pipelines)")


def _emit(result, args, md: Optional[str], html_path: Optional[str], json_path: Optional[str], charts: Optional[str]) -> int:
    if md:
        _write(md, to_markdown(result, args.suppress_below))
    if html_path:
        _write(html_path, to_html(result, args.suppress_below))
    if json_path:
        _write(json_path, to_json(result))
    if charts:
        write_charts(result, charts)
    _summary(result)
    if args.fail_on_adverse and result.verdict == "ADVERSE IMPACT DETECTED":
        return 2
    return 0


def _write(path: str, text: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"  wrote {path}", file=sys.stderr)


def _summary(result) -> None:
    print(f"\n{result.title}: {result.verdict}")
    print(f"  {result.total:,} records · overall rate {result.overall_rate:.1%}")
    for d in result.dimensions:
        low = d.min_impact_ratio
        line = f"  {d.name:<32} min impact ratio {low:.2f}" if low is not None else f"  {d.name:<32} n/a"
        if d.flagged:
            line += "  ⚠ " + ", ".join(g.category for g in d.flagged)
        print(line)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="auditlens", description="Open, explainable bias audits for automated hiring tools.")
    parser.add_argument("--version", action="version", version=f"auditlens {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("audit", help="audit a CSV of decisions or scores")
    a.add_argument("csv", help="input CSV, one row per person")
    a.add_argument("--outcome", required=True, help="decision column (selection mode) or score column (scoring mode)")
    a.add_argument("--mode", choices=["selection", "scoring"], default="selection")
    a.add_argument("--attr", action="append", required=True, metavar="NAME=COLUMN", help="demographic dimension; repeatable")
    a.add_argument("--intersect", action="append", default=[], metavar="NAME,NAME", help="cross two or more dimensions; repeatable")
    a.add_argument("--period", help="column for drift tracking, e.g. quarter")
    a.add_argument("--title", default="Bias Audit")
    a.add_argument("--md"), a.add_argument("--html"), a.add_argument("--json")
    a.add_argument("--charts", metavar="DIR", help="also write standalone SVG charts to DIR")
    _add_audit_options(a)

    d = sub.add_parser("demo", help="generate synthetic data with a hidden proxy bias and audit it")
    d.add_argument("--out", default="examples", help="output directory (default examples/)")
    d.add_argument("--n", type=int, default=6000)
    d.add_argument("--seed", type=int, default=7)
    _add_audit_options(d)

    args = parser.parse_args(argv)

    try:
        if args.command == "audit":
            rows = load_csv(args.csv)
            attrs = dict(_parse_attr(s) for s in args.attr)
            inters = [tuple(x.strip() for x in s.split(",")) for s in args.intersect]
            result = audit(rows, args.outcome, attrs, mode=args.mode, intersections=inters, period=args.period,
                           threshold=args.threshold, alpha=args.alpha, min_share=args.min_share,
                           min_group_size=args.min_group_size, title=args.title)
            return _emit(result, args, args.md, args.html, args.json, args.charts)

        rows = synth.generate(n=args.n, seed=args.seed)
        os.makedirs(args.out, exist_ok=True)
        data_path = os.path.join(args.out, "applicants.csv")
        synth.write_csv(data_path, rows)
        print(f"  wrote {data_path}", file=sys.stderr)
        attrs = {"Sex": "sex", "Race/Ethnicity": "race_ethnicity", "Age": "age_band"}
        common = dict(intersections=[("Sex", "Race/Ethnicity")], period="quarter", threshold=args.threshold,
                      alpha=args.alpha, min_share=args.min_share, min_group_size=args.min_group_size)
        sel = audit(rows, "advanced", attrs, mode="selection", title="Resume Screener — Selection Audit", **common)
        rc = _emit(sel, args, os.path.join(args.out, "selection_audit.md"), os.path.join(args.out, "selection_audit.html"),
                   os.path.join(args.out, "selection_audit.json"), os.path.join(args.out, "charts"))
        sco = audit(rows, "score", attrs, mode="scoring", title="Resume Screener — Scoring Audit", **common)
        _emit(sco, args, os.path.join(args.out, "scoring_audit.md"), None, None, None)
        return rc
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
