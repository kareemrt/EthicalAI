"""Command line: `veil scan | scrub | restore | labels`."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from . import __version__
from .core import Vault, Veil
from .detectors import DETECTORS

USE_COLOR = sys.stderr.isatty()


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def _read(src: str) -> str:
    return sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")


def _write(text: str, dest: str | None) -> None:
    if dest:
        Path(dest).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _terms(args) -> list[str]:
    terms = list(args.term or [])
    if args.terms_file:
        lines = Path(args.terms_file).read_text(encoding="utf-8").splitlines()
        terms += [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    return terms


def _veil(args, vault: Vault | None = None) -> Veil:
    split = lambda s: [x.strip() for x in s.split(",")] if s else None  # noqa: E731
    return Veil(terms=_terms(args), only=split(args.only), skip=split(args.skip) or (), vault=vault)


def _summary(findings) -> str:
    counts = Counter(f.label for f in findings)
    return ", ".join(f"{n} {label}" for label, n in counts.most_common()) or "nothing"


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_scan(args) -> int:
    text = _read(args.input)
    findings = _veil(args).scan(text)
    if args.json:
        print(json.dumps([{"label": f.label, "kind": f.kind, "start": f.start, "end": f.end,
                           "preview": f.masked()} for f in findings], indent=2))
    else:
        for f in findings:
            line = text.count("\n", 0, f.start) + 1
            col = f.start - (text.rfind("\n", 0, f.start) + 1) + 1
            colour = "31" if f.kind == "secret" else "33"
            print(f"  {line:>4}:{col:<4} {_c(f'{f.label:<15}', colour)} {f.masked()}")
        verdict = _c("clean", "32") if not findings else _c(f"found {_summary(findings)}", "1")
        print(f"\n  {verdict}", file=sys.stderr)
    return 1 if findings else 0          # non-zero = "do not send", handy in CI / hooks


def cmd_scrub(args) -> int:
    vault = Vault.load(args.vault)
    veil = _veil(args, vault)
    text = _read(args.input)
    findings = veil.scan(text)
    _write(veil.scrub(text), args.output)
    vault.save(args.vault)
    if not args.quiet:
        print(_c(f"veil: redacted {_summary(findings)} → vault {args.vault}", "2"), file=sys.stderr)
    return 0


def cmd_restore(args) -> int:
    if not Path(args.vault).exists():
        print(f"veil: vault not found: {args.vault}", file=sys.stderr)
        return 2
    _write(Vault.load(args.vault).restore(_read(args.input)), args.output)
    return 0


def cmd_labels(_args) -> int:
    for d in DETECTORS:
        check = "validated" if d.validate else ""
        print(f"  {d.label:<15} {d.kind:<7} {check}")
    print("  TERM            custom  --term / --terms-file (use 'LABEL: value' to rename)")
    return 0


# ── parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="veil", description="Redact sensitive data before it reaches an AI model; restore it after.")
    p.add_argument("--version", action="version", version=f"veil {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("input", nargs="?", default="-", help="file to read (default: stdin)")
        sp.add_argument("-t", "--term", action="append", help="extra term to redact, e.g. a name (repeatable)")
        sp.add_argument("-T", "--terms-file", help="file with one term per line")
        sp.add_argument("--only", help="comma-separated labels to detect (default: all)")
        sp.add_argument("--skip", help="comma-separated labels to ignore")

    s = sub.add_parser("scan", help="report sensitive data; exit 1 if any is found")
    common(s)
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("scrub", help="replace sensitive data with placeholders")
    common(s)
    s.add_argument("-o", "--output", help="write here instead of stdout")
    s.add_argument("-v", "--vault", default=".veil-vault.json", help="vault file (created or extended)")
    s.add_argument("-q", "--quiet", action="store_true")
    s.set_defaults(func=cmd_scrub)

    s = sub.add_parser("restore", help="put the original values back")
    s.add_argument("input", nargs="?", default="-")
    s.add_argument("-o", "--output")
    s.add_argument("-v", "--vault", default=".veil-vault.json")
    s.set_defaults(func=cmd_restore)

    s = sub.add_parser("labels", help="list what veil can detect")
    s.set_defaults(func=cmd_labels)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, UnicodeDecodeError) as e:
        print(f"veil: {e}", file=sys.stderr)
        return 2
