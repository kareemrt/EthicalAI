"""Command line:  python -m recourse {inspect,explain,audit} ..."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, report
from .audit import audit, read_csv
from .model import Model


def _load_record(path: str, row_id: str | None) -> dict:
    if path.endswith(".csv"):
        rows = read_csv(path)
        if row_id is None:
            sys.exit("explain: pass --id to pick a row from a CSV file")
        match = [r for r in rows if r.get("id") == row_id]
        if not match:
            sys.exit(f"explain: no row with id {row_id!r} in {path}")
        return match[0]
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="recourse", description="Actionable recourse for automated decisions.")
    p.add_argument("--version", action="version", version=f"recourse {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("inspect", help="summarise a model and its action policy")
    s.add_argument("model")

    s = sub.add_parser("explain", help="explain one decision and what would change it")
    s.add_argument("model")
    s.add_argument("record", help="JSON file, or CSV file with --id")
    s.add_argument("--id", help="row id when RECORD is a CSV")
    s.add_argument("--json", action="store_true", help="machine-readable output")

    s = sub.add_parser("audit", help="compare recourse burden across groups")
    s.add_argument("model")
    s.add_argument("data", help="CSV with one row per person")
    s.add_argument("--group", default="group", help="column to group by (default: group)")
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.add_argument("--md", metavar="FILE", help="also write a Markdown report")
    s.add_argument("--svg", metavar="FILE", help="also write an SVG chart")
    s.add_argument("--strict", action="store_true", help="exit 1 if any finding is flagged (for CI)")

    a = p.parse_args(argv)
    model = Model.load(a.model)

    if a.cmd == "inspect":
        print(report.inspect_text(model))
        return 0

    if a.cmd == "explain":
        rec = _load_record(a.record, a.id)
        x = model.vector(rec)
        if a.json:
            print(json.dumps(report.explain_data(model, x), indent=2))
        else:
            print(report.explain_text(model, x, who=str(rec.get("id", "applicant"))))
        return 0

    r = audit(model, read_csv(a.data), a.group)
    print(json.dumps(report.audit_data(r), indent=2) if a.json else report.audit_text(r))
    if a.md:
        Path(a.md).write_text(report.audit_markdown(r))
    if a.svg:
        Path(a.svg).write_text(report.audit_svg(r))
    return 1 if a.strict and any(f.severity == "flag" for f in r.findings) else 0
