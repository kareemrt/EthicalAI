"""Render an Audit as terminal text, Markdown or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from .metrics import Audit, AttributeResult, GroupResult

GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def _status(g: GroupResult, threshold: float) -> str:
    if g.excluded:
        return "too small"
    if g.is_reference:
        return "reference"
    if g.impact_ratio is None:
        return "n/a"
    if g.impact_ratio < threshold:
        return "ADVERSE*" if (g.p_value or 1) < 0.05 else "ADVERSE"
    return "ok"


def _fmt_ir(g: GroupResult) -> str:
    return "—" if g.impact_ratio is None or g.excluded else f"{g.impact_ratio:.2f}"


def _fmt_p(g: GroupResult) -> str:
    if g.p_value is None:
        return "—"
    return "<0.001" if g.p_value < 0.001 else f"{g.p_value:.3f}"


def _bar(ir: float | None, width: int = 20) -> str:
    if ir is None:
        return ""
    filled = round(min(ir, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def _summary_line(a: Audit) -> str:
    flags = a.flagged()
    if not flags:
        return f"PASS — no group falls below the {a.threshold:.0%} impact-ratio threshold."
    return f"FAIL — {len(flags)} group(s) below the {a.threshold:.0%} impact-ratio threshold."


def _rate_label(a: Audit) -> str:
    return "Scoring rate" if a.mode == "scoring" else "Selection rate"


# ── terminal ─────────────────────────────────────────────────────────────────

def to_text(a: Audit, color: bool = True) -> str:
    c = (lambda code, s: f"{code}{s}{RESET}") if color else (lambda code, s: s)
    lines = [c(BOLD, f"fairaudit · outcome '{a.outcome}' · {a.total:,} records · {a.mode} mode")]
    if a.median_score is not None:
        lines.append(c(DIM, f"scoring rate = share scoring above the overall median ({a.median_score:g})"))

    for attr in a.attributes:
        width = max([len(g.group) for g in attr.groups] + [len(attr.attribute)])
        lines += ["", c(BOLD, attr.attribute)]
        lines.append(c(DIM, f"  {'group':<{width}}  {'n':>6}  {'rate':>6}  {'impact':>6}  "
                            f"{'p':>6}  {'':20}  status"))
        for g in attr.groups:
            st = _status(g, a.threshold)
            tint = RED if st.startswith("ADVERSE") else DIM if st in ("too small", "n/a") else GREEN
            lines.append(f"  {g.group:<{width}}  {g.n:>6,}  {g.rate:>6.1%}  {_fmt_ir(g):>6}  "
                         f"{_fmt_p(g):>6}  {c(tint, _bar(None if g.excluded else g.impact_ratio))}  "
                         f"{c(tint, st)}")
        if attr.unknown:
            lines.append(c(DIM, f"  ({attr.unknown:,} records with unknown {attr.attribute} excluded)"))

    lines += ["", c(GREEN if a.passed else RED, c(BOLD, _summary_line(a)))]
    if not a.passed:
        lines.append(c(DIM, "* gap is statistically significant (p < 0.05) versus the reference group"))
    return "\n".join(lines)


# ── markdown ─────────────────────────────────────────────────────────────────

def _md_table(attr: AttributeResult, a: Audit) -> list[str]:
    rows = [f"| Group | Applicants | Selected | {_rate_label(a)} | Impact ratio | p-value | Status |",
            "|---|---:|---:|---:|---:|---:|---|"]
    icons = {"ok": "✅ ok", "reference": "⭐ reference", "too small": "⚪ too small", "n/a": "—"}
    for g in attr.groups:
        st = _status(g, a.threshold)
        rows.append(f"| {g.group} | {g.n:,} | {g.selected:,} | {g.rate:.1%} | {_fmt_ir(g)} | "
                    f"{_fmt_p(g)} | {icons.get(st, '🔴 ' + st.lower())} |")
    if attr.unknown:
        rows.append(f"\n_{attr.unknown:,} records with unknown {attr.attribute} were excluded._")
    return rows


def to_markdown(a: Audit, chart_path: str | None = None) -> str:
    md = ["# Bias Audit Report", "",
          f"**Outcome:** `{a.outcome}` · **Records:** {a.total:,} · **Mode:** {a.mode} · "
          f"**Threshold:** {a.threshold:.2f}" + (f" · **Min group share:** {a.min_share:.0%}" if a.min_share else ""),
          "", f"> **{_summary_line(a)}**", ""]
    if a.median_score is not None:
        md += [f"Scoring rate = share of a group scoring above the overall median score ({a.median_score:g}).", ""]
    if chart_path:
        md += [f"![Impact ratios]({chart_path})", ""]
    for attr in a.attributes:
        md += [f"## {attr.attribute}", "", *_md_table(attr, a), ""]
    md += ["---", "",
           "**How to read this.** *Impact ratio* = group rate ÷ rate of the most-selected group. "
           f"Below **{a.threshold:.2f}** indicates potential adverse impact under the EEOC four-fifths rule. "
           "*p-value* comes from a two-proportion z-test against the reference group; "
           "`*` marks gaps unlikely to be chance (p < 0.05). "
           "This report is a screening signal, not a legal determination.", ""]
    return "\n".join(md)


# ── json ─────────────────────────────────────────────────────────────────────

def to_json(a: Audit) -> str:
    data = asdict(a)
    data["passed"] = a.passed
    return json.dumps(data, indent=2)
