"""Command-line entry point:  python -m fairaudit data.csv --outcome hired --groups sex race"""

from __future__ import annotations

import argparse
import sys

from . import data, report
from .metrics import FOUR_FIFTHS, audit, binarize


def parse(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="fairaudit", description="Bias audit for automated decision tools.")
    p.add_argument("csv", help="one row per person: demographics + the tool's decision or score")
    p.add_argument("--outcome", required=True, help="column with the decision (yes/no, 1/0) or score")
    p.add_argument("--score", action="store_true", help="outcome is a numeric score (uses LL144 scoring rate)")
    p.add_argument("--threshold", type=float, help="score cut-off (default: overall median)")
    p.add_argument("--groups", nargs="+", required=True, help="demographic columns to audit one by one")
    p.add_argument("--intersect", nargs="+", metavar="COL", help="columns to combine, e.g. sex race")
    p.add_argument("--label", help="optional ground-truth column (qualified yes/no) for equal opportunity")
    p.add_argument("--out", default="audit", help="output directory (default: ./audit)")
    p.add_argument("--fail-under", type=float, metavar="RATIO",
                   help=f"exit 1 if any category's impact ratio is below RATIO (e.g. {FOUR_FIFTHS}); for CI")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = parse(argv)
    try:
        rows = data.load(a.csv)
        data.require(rows, a.outcome, a.label or "", *a.groups, *(a.intersect or []))
        if a.score:
            selected, cut = binarize([data.as_float(r[a.outcome]) for r in rows], a.threshold)
            note = f"Scores binarised at **{cut:g}** ({'given' if a.threshold is not None else 'overall median'})."
        else:
            selected, note = [data.as_bool(r[a.outcome]) for r in rows], ""
    except (OSError, ValueError) as e:
        print(f"fairaudit: {e}", file=sys.stderr)
        return 2

    qualified = [data.as_bool(r[a.label]) for r in rows] if a.label else None
    dims = {g: [g] for g in a.groups}
    if a.intersect:
        dims[" × ".join(a.intersect)] = a.intersect
    results = {name: audit(data.column(rows, *cols), selected, qualified) for name, cols in dims.items()}

    path = report.write(a.out, a.csv, a.outcome, results, note)
    print(report.terminal(results, color=sys.stdout.isatty()))
    print(f"\nReport → {path}")

    if a.fail_under is not None:
        worst = min(st.impact_ratio for ss in results.values() for st in ss if "small-sample" not in st.flags)
        if worst < a.fail_under:
            print(f"FAIL: lowest impact ratio {worst:.2f} < {a.fail_under}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
