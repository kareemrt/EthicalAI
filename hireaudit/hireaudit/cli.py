"""Command-line entry point: ``hireaudit`` or ``python -m hireaudit``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .charts import impact_chart
from .data import load
from .metrics import Config, audit_all
from .report import overall, render_html, render_json, render_markdown, render_text, slug


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="hireaudit",
        description="Bias audit for automated hiring decisions "
                    "(NYC Local Law 144 impact ratios + EEOC four-fifths rule).")
    p.add_argument("csv", help="CSV file with one row per applicant")
    p.add_argument("-g", "--groups", nargs="+", required=True, metavar="COL",
                   help="demographic column(s), e.g. sex race_ethnicity")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("-o", "--outcome", metavar="COL",
                        help="yes/no outcome column (selection-rate mode)")
    target.add_argument("-s", "--score", metavar="COL",
                        help="numeric score column (scoring-rate mode: above median = positive)")
    p.add_argument("--positive", nargs="+", metavar="VALUE",
                   help="values counted as positive outcome (default: 1, yes, true, hired, ...)")
    p.add_argument("--threshold", type=float, default=0.8, help="impact-ratio threshold (0.8)")
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (0.05)")
    p.add_argument("--min-share", type=float, default=0.02,
                   help="exclude categories below this share of data (0.02)")
    p.add_argument("--no-intersect", action="store_true",
                   help="skip the intersectional (combined columns) audit")
    p.add_argument("--out", metavar="DIR",
                   help="write report.md, report.html, report.json and charts/ here")
    p.add_argument("--strict", action="store_true",
                   help="exit with status 1 if any group FAILs (use as a CI gate)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        ds = load(args.csv, args.groups, args.outcome, args.score, args.positive)
    except (OSError, ValueError) as e:
        print(f"hireaudit: error: {e}", file=sys.stderr)
        return 2

    cfg = Config(args.threshold, args.alpha, args.min_share, not args.no_intersect)
    audits = audit_all(ds, cfg)
    print(render_text(ds, audits))

    if args.out:
        out = Path(args.out)
        (out / "charts").mkdir(parents=True, exist_ok=True)
        for a in audits:
            (out / "charts" / f"{slug(a.attribute)}.svg").write_text(impact_chart(a), "utf-8")
        (out / "report.md").write_text(render_markdown(ds, audits), "utf-8")
        (out / "report.html").write_text(render_html(ds, audits), "utf-8")
        (out / "report.json").write_text(render_json(ds, audits), "utf-8")
        print(f"\nReports written to {out}/")

    return 1 if args.strict and overall(audits) == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
