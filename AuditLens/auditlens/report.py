"""Report rendering: Markdown, self-contained HTML (with inline SVG charts) and JSON."""

from __future__ import annotations

import html
import json
from datetime import date
from typing import Dict, List, Optional

from .audit import (
    STATUS_ADVERSE,
    STATUS_INSUFFICIENT,
    STATUS_OK,
    STATUS_REFERENCE,
    STATUS_WATCH,
    AuditResult,
    DimensionResult,
    GroupResult,
)

COLORS = {
    STATUS_REFERENCE: "#2563eb",
    STATUS_OK: "#0f9d76",
    STATUS_WATCH: "#d97706",
    STATUS_ADVERSE: "#dc2626",
    STATUS_INSUFFICIENT: "#9ca3af",
}
EXCLUDED_COLOR = "#cbd5e1"
ICONS = {
    STATUS_REFERENCE: "🔵",
    STATUS_OK: "🟢",
    STATUS_WATCH: "🟠",
    STATUS_ADVERSE: "🔴",
    STATUS_INSUFFICIENT: "⚪",
}


def _color(g: GroupResult) -> str:
    return EXCLUDED_COLOR if g.excluded else COLORS.get(g.status, "#64748b")


def _count(n: int, suppress_below: int) -> str:
    """Small-cell suppression so published reports can't re-identify people."""
    if suppress_below and 0 < n < suppress_below:
        return f"<{suppress_below}"
    return f"{n:,}"


def _ratio(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.3f}"


def _pval(p: Optional[float]) -> str:
    if p is None:
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _rate_word(result: AuditResult) -> str:
    return "Selection rate" if result.mode == "selection" else "Scoring rate"


# --------------------------------------------------------------------------- #
# SVG charts
# --------------------------------------------------------------------------- #

def impact_ratio_svg(dim: DimensionResult, threshold: float, width: int = 760) -> str:
    """Horizontal bar chart of impact ratios with CI whiskers and a threshold line."""
    groups = [g for g in dim.groups if g.impact_ratio is not None]
    row_h, top, bottom = 30, 44, 34
    label_w = min(330, 30 + 7 * max((len(g.category) for g in groups), default=10))
    plot_w = width - label_w - 70
    height = top + bottom + row_h * max(1, len(groups))
    xmax = 1.2

    def x(v: float) -> float:
        return label_w + plot_w * min(v, xmax) / xmax

    out: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'font-family="Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif" role="img" '
        f'aria-label="Impact ratios by {html.escape(dim.name)}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff" rx="10"/>',
        f'<text x="16" y="26" font-size="15" font-weight="600" fill="#0f172a">Impact ratio by {html.escape(dim.name)}</text>',
    ]
    for t in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2):
        xx = x(t)
        out.append(f'<line x1="{xx:.1f}" y1="{top - 6}" x2="{xx:.1f}" y2="{height - bottom + 4}" stroke="#eef2f7"/>')
        out.append(f'<text x="{xx:.1f}" y="{height - bottom + 20}" font-size="11" fill="#64748b" text-anchor="middle">{t:.1f}</text>')

    tx = x(threshold)
    out.append(f'<rect x="{label_w}" y="{top - 6}" width="{tx - label_w:.1f}" height="{height - top - bottom + 10}" fill="#fef2f2" opacity="0.7"/>')
    out.append(f'<line x1="{tx:.1f}" y1="{top - 10}" x2="{tx:.1f}" y2="{height - bottom + 4}" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{tx + 4:.1f}" y="{top - 12}" font-size="11" fill="#dc2626">{threshold:g} threshold</text>')

    for i, g in enumerate(groups):
        y = top + i * row_h
        cy = y + row_h / 2
        out.append(f'<text x="{label_w - 10}" y="{cy + 4:.1f}" font-size="12" fill="#1e293b" text-anchor="end">{html.escape(g.category)}</text>')
        out.append(f'<rect x="{label_w}" y="{y + 6}" width="{x(g.impact_ratio) - label_w:.1f}" height="{row_h - 12}" rx="3" fill="{_color(g)}"/>')
        if g.impact_ratio_ci:
            lo, hi = g.impact_ratio_ci
            out.append(f'<line x1="{x(lo):.1f}" y1="{cy:.1f}" x2="{x(hi):.1f}" y2="{cy:.1f}" stroke="#0f172a" stroke-width="1.2"/>')
            for v in (lo, hi):
                out.append(f'<line x1="{x(v):.1f}" y1="{cy - 5:.1f}" x2="{x(v):.1f}" y2="{cy + 5:.1f}" stroke="#0f172a" stroke-width="1.2"/>')
        value_color = "#64748b" if g.excluded else _color(g)
        out.append(f'<text x="{width - 12}" y="{cy + 4:.1f}" font-size="12" font-weight="600" fill="{value_color}" text-anchor="end">{g.impact_ratio:.2f}</text>')
    out.append("</svg>")
    return "\n".join(out)


def timeline_svg(result: AuditResult, width: int = 760, height: int = 300) -> str:
    """Line chart of the lowest impact ratio per dimension over time (drift)."""
    periods = sorted({p.period for p in result.timeline})
    dims = list(dict.fromkeys(p.dimension for p in result.timeline))
    palette = ["#2563eb", "#7c3aed", "#0f9d76", "#db2777", "#ea580c", "#0891b2"]
    left, right, top, bottom = 56, 170, 44, 40
    pw, ph = width - left - right, height - top - bottom

    def x(i: int) -> float:
        return left + (pw * i / max(1, len(periods) - 1))

    def y(v: float) -> float:
        return top + ph * (1 - min(v, 1.2) / 1.2)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'font-family="Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif" role="img" aria-label="Impact ratio drift over time">',
        f'<rect width="{width}" height="{height}" fill="#ffffff" rx="10"/>',
        '<text x="16" y="26" font-size="15" font-weight="600" fill="#0f172a">Lowest impact ratio over time</text>',
        f'<rect x="{left}" y="{y(result.threshold):.1f}" width="{pw}" height="{top + ph - y(result.threshold):.1f}" fill="#fef2f2" opacity="0.7"/>',
    ]
    for t in (0.0, 0.4, 0.8, 1.2):
        out.append(f'<line x1="{left}" y1="{y(t):.1f}" x2="{left + pw}" y2="{y(t):.1f}" stroke="#eef2f7"/>')
        out.append(f'<text x="{left - 8}" y="{y(t) + 4:.1f}" font-size="11" fill="#64748b" text-anchor="end">{t:.1f}</text>')
    out.append(f'<line x1="{left}" y1="{y(result.threshold):.1f}" x2="{left + pw}" y2="{y(result.threshold):.1f}" stroke="#dc2626" stroke-dasharray="5 4" stroke-width="1.5"/>')
    for i, p in enumerate(periods):
        out.append(f'<text x="{x(i):.1f}" y="{height - bottom + 20}" font-size="11" fill="#64748b" text-anchor="middle">{html.escape(p)}</text>')
    for j, dname in enumerate(dims):
        color = palette[j % len(palette)]
        pts = [(periods.index(p.period), p.min_impact_ratio) for p in result.timeline if p.dimension == dname and p.min_impact_ratio is not None]
        if not pts:
            continue
        path = " ".join(f"{'M' if k == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for k, (i, v) in enumerate(pts))
        out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>')
        for i, v in pts:
            out.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="3.5" fill="{color}"/>')
        ly = top + 8 + j * 20
        out.append(f'<rect x="{left + pw + 16}" y="{ly - 8}" width="12" height="12" rx="2" fill="{color}"/>')
        out.append(f'<text x="{left + pw + 34}" y="{ly + 2}" font-size="12" fill="#1e293b">{html.escape(dname)}</text>')
    out.append("</svg>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #

def to_markdown(result: AuditResult, suppress_below: int = 0) -> str:
    rw = _rate_word(result)
    lines = [
        f"# {result.title}",
        "",
        f"**Verdict: {result.verdict}**  ",
        f"Generated {date.today().isoformat()} by AuditLens · mode: `{result.mode}` · outcome column: `{result.outcome}`",
        "",
        "| Records | Overall rate | Threshold | Significance (α) | Min. group share | Min. group size |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {result.total:,} | {result.overall_rate:.1%} | {result.threshold:g} | {result.alpha:g} | {result.min_share:.0%} | {result.min_group_size} |",
        "",
    ]
    if result.median_score is not None:
        lines += [f"Scoring rate = share of a category scoring above the sample median score (**{result.median_score:g}**).", ""]

    for d in result.dimensions:
        lines += [
            f"## {d.name}",
            "",
            f"| Category | Applicants | Selected | {rw} (95% CI) | Impact ratio (95% CI) | p-value | Status |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for g in d.groups:
            ci = f"{g.rate:.1%} ({g.rate_ci[0]:.1%}–{g.rate_ci[1]:.1%})"
            irci = _ratio(g.impact_ratio)
            if g.impact_ratio_ci:
                irci += f" ({g.impact_ratio_ci[0]:.2f}–{g.impact_ratio_ci[1]:.2f})"
            icon = "⚪" if g.excluded else ICONS.get(g.status, "")
            lines.append(
                f"| {g.category} | {_count(g.n, suppress_below)} | {_count(g.positives, suppress_below)} | {ci} | {irci} | {_pval(g.p_value)} | {icon} {g.status} |"
            )
        lines += ["", f"Unknown / not disclosed: **{_count(d.unknown, suppress_below)}**", ""]

    if result.timeline:
        periods = sorted({p.period for p in result.timeline})
        dims = list(dict.fromkeys(p.dimension for p in result.timeline))
        lines += ["## Drift over time (lowest impact ratio per period)", "", "| Dimension | " + " | ".join(periods) + " |",
                  "|---|" + "---:|" * len(periods)]
        idx = {(p.dimension, p.period): p for p in result.timeline}
        for dname in dims:
            cells = []
            for per in periods:
                pt = idx.get((dname, per))
                v = pt.min_impact_ratio if pt else None
                flag = " ⚠️" if v is not None and v < result.threshold else ""
                cells.append(_ratio(v) + flag)
            lines.append(f"| {dname} | " + " | ".join(cells) + " |")
        lines.append("")

    if result.warnings:
        lines += ["## Warnings", ""] + [f"- {w}" for w in result.warnings] + [""]

    lines += [
        "## How to read this report",
        "",
        f"- **{rw}**: share of a category that received a favourable outcome.",
        "- **Impact ratio**: a category's rate divided by the rate of the most-favoured category (the *reference*).",
        f"- 🔴 **adverse impact**: impact ratio below {result.threshold:g} *and* statistically significant (p < {result.alpha:g}).",
        f"- 🟠 **below threshold (not significant)**: under {result.threshold:g} but could plausibly be noise; monitor closely.",
        f"- ⚪ **insufficient data / excluded**: fewer than {result.min_group_size} records or under {result.min_share:.0%} of the sample.",
        "- A clean audit is necessary, **not sufficient**, evidence of fairness. Review job-relatedness, proxies and accessibility too.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #

_CSS = """
:root{--bg:#f6f8fb;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Inter,-apple-system,Segoe UI,Helvetica,Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:0 0 12px}.muted{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0;overflow-x:auto}
.verdict{display:inline-block;font-weight:700;padding:6px 14px;border-radius:999px;color:#fff;margin:12px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}.kpi b{display:block;font-size:22px}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:12px}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child,th:last-child,td:last-child{text-align:left}th{color:var(--muted);font-weight:600}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;color:#fff;font-size:12px;font-weight:600}
svg{max-width:100%;height:auto}ul{padding-left:20px}
"""


def to_html(result: AuditResult, suppress_below: int = 0) -> str:
    rw = _rate_word(result)
    vcolor = {"ADVERSE IMPACT DETECTED": "#dc2626", "REVIEW RECOMMENDED": "#d97706"}.get(result.verdict, "#0f9d76")
    flagged = sum(len(d.flagged) for d in result.dimensions)
    e = html.escape
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>{e(result.title)}</title><style>{_CSS}</style></head><body><main>",
        f"<h1>{e(result.title)}</h1>",
        f"<div class='muted'>Generated {date.today().isoformat()} by AuditLens · mode <code>{e(result.mode)}</code> · outcome <code>{e(result.outcome)}</code></div>",
        f"<div class='verdict' style='background:{vcolor}'>{e(result.verdict)}</div>",
        "<div class='kpis'>",
        f"<div class='kpi'><span class='muted'>Records audited</span><b>{result.total:,}</b></div>",
        f"<div class='kpi'><span class='muted'>Overall {rw.lower()}</span><b>{result.overall_rate:.1%}</b></div>",
        f"<div class='kpi'><span class='muted'>Groups with adverse impact</span><b>{flagged}</b></div>",
        f"<div class='kpi'><span class='muted'>Impact-ratio threshold</span><b>{result.threshold:g}</b></div>",
        "</div>",
    ]
    for d in result.dimensions:
        parts.append(f"<section class='card'><h2>{e(d.name)}</h2>{impact_ratio_svg(d, result.threshold)}")
        parts.append(f"<table><tr><th>Category</th><th>Applicants</th><th>Selected</th><th>{rw} (95% CI)</th><th>Impact ratio (95% CI)</th><th>p-value</th><th>Status</th></tr>")
        for g in d.groups:
            irci = _ratio(g.impact_ratio)
            if g.impact_ratio_ci:
                irci += f" ({g.impact_ratio_ci[0]:.2f}–{g.impact_ratio_ci[1]:.2f})"
            parts.append(
                f"<tr><td>{e(g.category)}</td><td>{_count(g.n, suppress_below)}</td><td>{_count(g.positives, suppress_below)}</td>"
                f"<td>{g.rate:.1%} ({g.rate_ci[0]:.1%}–{g.rate_ci[1]:.1%})</td><td>{irci}</td><td>{_pval(g.p_value)}</td>"
                f"<td><span class='pill' style='background:{_color(g)}'>{e(g.status)}</span></td></tr>"
            )
        parts.append(f"</table><p class='muted'>Unknown / not disclosed: {_count(d.unknown, suppress_below)}</p></section>")

    if result.timeline:
        parts.append(f"<section class='card'><h2>Drift over time</h2>{timeline_svg(result)}</section>")
    if result.warnings:
        parts.append("<section class='card'><h2>Warnings</h2><ul>" + "".join(f"<li>{e(w)}</li>" for w in result.warnings) + "</ul></section>")
    parts.append(
        "<section class='card'><h2>Method</h2><ul>"
        f"<li><b>{rw}</b>: share of a category receiving a favourable outcome"
        + (f" (score above the sample median of {result.median_score:g})" if result.median_score is not None else "")
        + ".</li><li><b>Impact ratio</b>: category rate ÷ rate of the most-favoured category.</li>"
        f"<li><b>Adverse impact</b>: impact ratio &lt; {result.threshold:g} and two-proportion z-test p &lt; {result.alpha:g}.</li>"
        f"<li>Groups under {result.min_share:.0%} of the sample are excluded from flagging; groups under {result.min_group_size} records are marked insufficient.</li>"
        "<li>Confidence intervals: Wilson (rates) and Katz log method (impact ratios).</li>"
        "<li>A clean audit is necessary, not sufficient, evidence of fairness.</li></ul></section>"
    )
    parts.append("</main></body></html>")
    return "".join(parts)


def to_json(result: AuditResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def write_charts(result: AuditResult, directory: str) -> Dict[str, str]:
    """Write every chart as a standalone SVG file; returns {name: path}."""
    import os
    import re

    os.makedirs(directory, exist_ok=True)
    written = {}
    for d in result.dimensions:
        slug = re.sub(r"[^a-z0-9]+", "-", d.name.lower()).strip("-")
        path = os.path.join(directory, f"impact-{slug}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(impact_ratio_svg(d, result.threshold))
        written[d.name] = path
    if result.timeline:
        path = os.path.join(directory, "drift.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(timeline_svg(result))
        written["drift"] = path
    return written
