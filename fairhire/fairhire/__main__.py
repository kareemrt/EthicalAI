"""Command-line entry point:  python -m fairhire applicants.csv --groups sex,race --outcome advanced"""

from __future__ import annotations

import argparse
import sys

from . import report
from .data import DataError, load_csv
from .metrics import FOUR_FIFTHS, MIN_SHARE, run_audit


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fairhire",
        description="Audit an automated hiring tool's decisions for adverse impact.",
        epilog="Exit code is 1 when any group falls below the threshold, so it can gate a CI pipeline.",
    )
    p.add_argument("csv", help="one row per applicant")
    p.add_argument("-g", "--groups", required=True, help="comma-separated protected-attribute columns, e.g. sex,race")
    p.add_argument("-o", "--outcome", help="yes/no column: did the tool advance this applicant?")
    p.add_argument("-s", "--score", help="numeric score column (used alone → scoring rate above the median)")
    p.add_argument("-l", "--label", help="optional yes/no ground-truth column, enables TPR/FPR")
    p.add_argument("-t", "--threshold", type=float, default=FOUR_FIFTHS, help="impact-ratio threshold (default 0.8)")
    p.add_argument("--min-share", type=float, default=MIN_SHARE, help="skip groups under this share (default 0.02)")
    p.add_argument("--no-intersections", action="store_true", help="don't audit combinations of groups")
    p.add_argument("--html", metavar="PATH", help="write a self-contained HTML report")
    p.add_argument("--md", metavar="PATH", help="write a Markdown report")
    p.add_argument("--json", action="store_true", help="print JSON instead of the text summary")
    a = p.parse_args(argv)

    cols = [c.strip() for c in a.groups.split(",") if c.strip()]
    try:
        records = load_csv(a.csv, cols, a.outcome, a.score, a.label)
    except (DataError, OSError) as e:
        print(f"fairhire: {e}", file=sys.stderr)
        return 2

    audit = run_audit(records, cols, a.threshold, a.min_share, not a.no_intersections)

    for path, render in ((a.html, report.to_html), (a.md, report.to_markdown)):
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(render(audit))
    print(report.to_json(audit) if a.json else report.to_text(audit))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
