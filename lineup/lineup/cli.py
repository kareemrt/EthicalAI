"""Command line interface: `lineup scan` and `lineup fix`."""

import argparse
import os
import sys

from . import __version__
from .data import infer_kind, load_csv, write_csv
from .detect import direct_identifiers, suggest_columns
from .generalize import anonymize
from .report import RENDERERS
from .risk import assess, drivers


def _cols(text):
    return [c.strip() for c in text.split(",") if c.strip()] if text else None


def audit(path, qis=None, sensitive=None, k=5, fix=False, max_suppress=0.05):
    """Run the full audit (and optionally the fix). Returns a dict for rendering."""
    header, rows = load_csv(path)
    for col in (qis or []) + (sensitive or []):
        if col not in header:
            raise SystemExit(f"lineup: column '{col}' not found. Columns: {', '.join(header)}")
    direct = direct_identifiers(header, rows)
    # User-chosen columns are never treated as direct identifiers.
    for col in (qis or []) + (sensitive or []):
        direct.pop(col, None)
    guess_q, guess_s = suggest_columns(header, exclude=direct)
    qis = qis if qis is not None else guess_q
    sensitive = sensitive if sensitive is not None else guess_s

    risk = assess(rows, qis, sensitive, k)
    result = {
        "dataset": os.path.basename(path),
        "direct_identifiers": direct,
        "sensitive": sensitive,
        "drivers": drivers(rows, qis) if qis else [],
        "risk": risk,
    }
    if fix:
        kinds = {q: infer_kind(q, [r[q] for r in rows]) for q in qis}
        fixed = anonymize(rows, qis, kinds, k, max_suppress, drop=set(direct))
        result["fix"] = fixed
        result["after"] = assess(fixed.rows, qis, sensitive, k)
        result["header"] = [c for c in header if c not in direct]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="lineup",
        description="Find out whether people in a dataset can be re-identified, then fix it.")
    parser.add_argument("--version", action="version", version=f"lineup {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("csv", help="dataset to audit (CSV with a header row)")
        p.add_argument("--qi", help="quasi-identifier columns, comma-separated (default: auto-detect)")
        p.add_argument("--sensitive", help="sensitive columns, comma-separated (default: auto-detect)")
        p.add_argument("-k", "--k", type=int, default=5,
                       help="every record must hide among at least k people (default: 5)")
        p.add_argument("--format", choices=RENDERERS, default="text", help="report format")

    scan = sub.add_parser("scan", help="measure re-identification risk (exit 1 if below k)")
    common(scan)
    fix = sub.add_parser("fix", help="write a k-anonymous copy of the dataset")
    common(fix)
    fix.add_argument("-o", "--output", required=True, help="where to write the anonymized CSV")
    fix.add_argument("--max-suppress", type=float, default=0.05,
                     help="largest share of records that may be dropped (default: 0.05)")

    args = parser.parse_args(argv)
    if args.k < 1:
        parser.error("k must be at least 1")
    result = audit(args.csv, _cols(args.qi), _cols(args.sensitive), args.k,
                   fix=args.command == "fix",
                   max_suppress=getattr(args, "max_suppress", 0.05))
    if args.command == "fix":
        write_csv(args.output, result["header"], result["fix"].rows)
    print(RENDERERS[args.format](result))
    final = result.get("after") or result["risk"]
    return 0 if final.passes else 1


if __name__ == "__main__":
    sys.exit(main())
