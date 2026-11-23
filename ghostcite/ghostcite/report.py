"""Render findings as a terminal report, Markdown or JSON."""
from __future__ import annotations

import json
from collections import Counter

from .models import FAILING, SEVERITY, Finding

ICON = {"malformed": "✗", "not_found": "✗", "mismatch": "≠", "unmatched": "?",
        "unchecked": "·", "verified": "✓"}
COLOR = {"malformed": "31", "not_found": "31", "mismatch": "33", "unmatched": "35",
         "unchecked": "90", "verified": "32"}
LABEL = {"malformed": "MALFORMED", "not_found": "NOT FOUND", "mismatch": "MISMATCH",
         "unmatched": "UNMATCHED", "unchecked": "UNCHECKED", "verified": "VERIFIED"}


def _short(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def summary(findings: list[Finding]) -> dict:
    counts = Counter(f.verdict for f in findings)
    return {"total": len(findings), "suspect": sum(counts[v] for v in FAILING),
            **{v: counts[v] for v in SEVERITY if counts[v]}}


def text(findings: list[Finding], color: bool = True, source: str = "") -> str:
    paint = (lambda code, s: f"\033[{code}m{s}\033[0m") if color else (lambda code, s: s)
    if not findings:
        return "No citations found.\n"
    width = max(len(f"{f.citation.kind}:{_short(f.citation.value, 44)}") for f in findings)
    lines = [paint("1", f"ghostcite · {source}") if source else "", ""]
    for f in findings:
        ident = f"{f.citation.kind}:{_short(f.citation.value, 44)}"
        verdict = paint(COLOR[f.verdict], f"{ICON[f.verdict]} {LABEL[f.verdict]:<9}")
        lines.append(f"  {verdict}  {paint('90', f'L{f.citation.line:<4}')} "
                     f"{ident:<{width}}  {paint('90', _short(f.reason, 90))}")
    s = summary(findings)
    tally = "  ".join(paint(COLOR[v], f"{s[v]} {LABEL[v].lower()}") for v in SEVERITY if v in s)
    verdict = (paint("1;31", f"{s['suspect']} of {s['total']} citations look fabricated or wrong")
               if s["suspect"] else paint("1;32", f"No fabricated citations among {s['total']}"))
    lines += ["", f"  {verdict}", f"  {tally}", ""]
    return "\n".join(lines).lstrip("\n")


def markdown(findings: list[Finding], source: str = "") -> str:
    s = summary(findings)
    out = [f"## Citation check{f' — `{source}`' if source else ''}", "",
           f"**{s['suspect']} of {s['total']}** citations look fabricated or wrong.", "",
           "| | Verdict | Line | Citation | Why |", "|---|---|---|---|---|"]
    for f in findings:
        val = _short(f.citation.value, 70).replace("|", "\\|")
        out.append(f"| {ICON[f.verdict]} | {LABEL[f.verdict]} | {f.citation.line} | "
                   f"`{f.citation.kind}:{val}` | {f.reason.replace('|', '/')} |")
    return "\n".join(out) + "\n"


def as_json(findings: list[Finding], source: str = "") -> str:
    return json.dumps({"source": source, "summary": summary(findings),
                       "findings": [f.to_dict() for f in findings]}, indent=2, ensure_ascii=False)
