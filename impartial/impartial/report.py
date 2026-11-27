"""Render audit results as text, Markdown, JSON, SVG or a standalone HTML page."""

from __future__ import annotations

import json
from datetime import date
from html import escape

from .metrics import DimensionResult, to_dict

COLORS = {"PASS": "#2f9e6e", "REVIEW": "#d9a21b", "FAIL": "#d6455d", "EXCLUDED": "#9aa0a6"}
ANSI = {"PASS": "\033[32m", "REVIEW": "\033[33m", "FAIL": "\033[31m", "EXCLUDED": "\033[90m"}
ICON = {"PASS": "✅", "REVIEW": "⚠️", "FAIL": "❌", "EXCLUDED": "➖"}


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _ratio(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def _p(x: float | None) -> str:
    return "—" if x is None else ("<0.001" if x < 0.001 else f"{x:.3f}")


def overall(results: list[DimensionResult]) -> str:
    verdicts = {r.verdict for r in results}
    return "FAIL" if "FAIL" in verdicts else "REVIEW" if "REVIEW" in verdicts else "PASS"


# --------------------------------------------------------------------------- text
def to_text(results: list[DimensionResult], meta: dict, color: bool = False) -> str:
    def paint(status: str, s: str) -> str:
        return f"{ANSI[status]}{s}\033[0m" if color else s

    out = [f"Impartial bias audit · {meta['source']} · {meta['rows']} rows", ""]
    for r in results:
        out.append(f"■ {r.dimension}  →  {paint(r.verdict, r.verdict)}   (reference: {r.reference}, unknown: {r.unknown})")
        width = max([len(g.group) for g in r.groups] + [5])
        out.append(f"  {'group':<{width}}  {'n':>6}  {'rate':>7}  {'ratio':>6}  {'p':>7}  status")
        for g in r.groups:
            out.append(
                f"  {g.group:<{width}}  {g.total:>6}  {_pct(g.rate):>7}  {_ratio(g.ratio):>6}  {_p(g.p_value):>7}  "
                + paint(g.status, g.status + (" (low n)" if g.low_power and g.status == "REVIEW" else ""))
            )
        out.append("")
    out.append(f"Overall: {paint(overall(results), overall(results))}")
    return "\n".join(out)


# ----------------------------------------------------------------------- markdown
def to_markdown(results: list[DimensionResult], meta: dict, threshold: float) -> str:
    out = [
        "# Bias Audit Report",
        "",
        f"**Source:** `{meta['source']}` · **Rows:** {meta['rows']} · **Date:** {date.today()} · "
        f"**Overall:** {ICON[overall(results)]} {overall(results)}",
        "",
    ]
    if meta.get("mode") == "score":
        out += [f"> Score mode: favourable outcome = score above sample median ({meta['threshold']:g}).", ""]
    for r in results:
        out += [
            f"## {r.dimension} — {ICON[r.verdict]} {r.verdict}",
            "",
            f"Reference group: **{r.reference}** · Unknown/missing: {r.unknown}",
            "",
            "| Group | Applicants | Selected | Rate (95% CI) | Impact ratio | p-value | Status |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for g in r.groups:
            out.append(
                f"| {g.group} | {g.total} | {g.selected} | {_pct(g.rate)} ({_pct(g.ci[0])}–{_pct(g.ci[1])}) "
                f"| {_ratio(g.ratio)} | {_p(g.p_value)} | {ICON[g.status]} {g.status} |"
            )
        out.append("")
    out.append(f"_Impact ratios below {threshold:.2f} indicate potential adverse impact (four-fifths rule)._")
    return "\n".join(out)


# ---------------------------------------------------------------------------- svg
def to_svg(result: DimensionResult, threshold: float = 0.8, width: int = 640) -> str:
    """Horizontal bar chart of impact ratios with the threshold marked."""
    row, top, label_w = 28, 34, 190
    plot_w = width - label_w - 70
    height = top + row * len(result.groups) + 30
    scale = lambda v: label_w + plot_w * min(v, 1.2) / 1.2  # noqa: E731
    font = "font-family='system-ui,-apple-system,Segoe UI,sans-serif'"

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' width='{width}' height='{height}' {font} role='img' "
        f"aria-label='Impact ratios by {escape(result.dimension)}'>",
        f"<rect width='100%' height='100%' fill='#ffffff' rx='10'/>",
        f"<text x='16' y='22' font-size='14' font-weight='600' fill='#1f2328'>Impact ratio · {escape(result.dimension)}</text>",
    ]
    for tick in (0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2):
        x = scale(tick)
        parts.append(f"<line x1='{x:.1f}' y1='{top - 6}' x2='{x:.1f}' y2='{height - 26}' stroke='#eaeef2'/>")
        parts.append(f"<text x='{x:.1f}' y='{height - 10}' font-size='11' fill='#6e7781' text-anchor='middle'>{tick:.1f}</text>")
    for i, g in enumerate(result.groups):
        y = top + i * row
        ratio = g.ratio or 0
        parts.append(f"<text x='{label_w - 10}' y='{y + 17}' font-size='12' fill='#1f2328' text-anchor='end'>{escape(g.group)}</text>")
        parts.append(
            f"<rect x='{label_w}' y='{y + 5}' width='{max(scale(ratio) - label_w, 1):.1f}' height='{row - 10}' rx='4' fill='{COLORS[g.status]}'>"
            f"<title>{escape(g.group)}: ratio {_ratio(g.ratio)}, rate {_pct(g.rate)}, n={g.total}</title></rect>"
        )
        parts.append(f"<text x='{scale(ratio) + 6:.1f}' y='{y + 17}' font-size='11' fill='#57606a' stroke='#fff' stroke-width='3' paint-order='stroke'>{_ratio(g.ratio)}</text>")
    tx = scale(threshold)
    parts.append(f"<line x1='{tx:.1f}' y1='{top - 8}' x2='{tx:.1f}' y2='{height - 26}' stroke='#d6455d' stroke-width='1.5' stroke-dasharray='4 3'/>")
    parts.append(f"<text x='{tx + 4:.1f}' y='{top - 10}' font-size='10' fill='#d6455d'>{threshold:.2f} threshold</text>")
    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------------------- html
_CSS = """
:root{--bg:#f6f8fa;--card:#fff;--ink:#1f2328;--mute:#57606a;--line:#d0d7de}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#161b22;--ink:#e6edf3;--mute:#8b949e;--line:#30363d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:900px;margin:0 auto;padding:32px 16px}h1{margin:0 0 4px;font-size:26px}.mute{color:var(--mute)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:18px 0;overflow-x:auto}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;color:#fff;font-weight:600;font-size:12px}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:12px}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child,td:last-child,th:last-child{text-align:left}svg{max-width:100%;height:auto;border-radius:10px}
footer{font-size:12px;margin-top:28px}
"""


def _pill(status: str) -> str:
    return f"<span class='pill' style='background:{COLORS[status]}'>{status}</span>"


def to_html(results: list[DimensionResult], meta: dict, threshold: float) -> str:
    sections = []
    for r in results:
        rows = "".join(
            f"<tr><td>{escape(g.group)}</td><td>{g.total}</td><td>{g.selected}</td>"
            f"<td>{_pct(g.rate)} <span class='mute'>({_pct(g.ci[0])}–{_pct(g.ci[1])})</span></td>"
            f"<td>{_ratio(g.ratio)}</td><td>{_p(g.p_value)}</td><td>{_pill(g.status)}{' <span class=mute>low n</span>' if g.low_power and g.status == 'REVIEW' else ''}</td></tr>"
            for g in r.groups
        )
        sections.append(
            f"<section class='card'><h2 style='margin:0 0 4px'>{escape(r.dimension)} {_pill(r.verdict)}</h2>"
            f"<div class='mute'>Reference group: <b>{escape(str(r.reference))}</b> · Unknown/missing: {r.unknown}</div>"
            f"<div style='margin-top:12px'>{to_svg(r, threshold)}</div>"
            "<table><tr><th>Group</th><th>Applicants</th><th>Selected</th><th>Rate (95% CI)</th><th>Impact ratio</th><th>p-value</th><th>Status</th></tr>"
            f"{rows}</table></section>"
        )
    mode = (
        f" · score mode (above median {meta['threshold']:g})" if meta.get("mode") == "score" else ""
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bias Audit Report</title><style>{_CSS}</style></head>
<body><main><h1>Bias Audit Report {_pill(overall(results))}</h1>
<div class="mute">{escape(meta['source'])} · {meta['rows']} rows · {date.today()}{mode}</div>
{''.join(sections)}
<footer class="mute"><b>How to read this:</b> impact ratio = group selection rate ÷ highest group's rate. Below {threshold:.2f} signals potential adverse impact
(EEOC four-fifths rule, NYC Local Law 144). <b>FAIL</b> = gap is statistically significant; <b>REVIEW</b> = gap exists but evidence is not conclusive;
<b>EXCLUDED</b> = group is too small a share of the data to score. This report is a screening tool, not legal advice. Generated by Impartial.</footer>
</main></body></html>"""


# --------------------------------------------------------------------------- json
def to_json(results: list[DimensionResult], meta: dict) -> str:
    return json.dumps({"meta": meta, "overall": overall(results), "dimensions": to_dict(results)}, indent=2)
