"""Render audits as Markdown, JSON, or a self-contained HTML page."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from html import escape
from math import floor

from .metrics import Audit, GroupStat


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _num(x: float | None) -> str:
    # Truncate rather than round so 0.7996 never displays as a passing 0.800.
    return "—" if x is None else f"{floor(x * 1000) / 1000:.3f}"


def _p(x: float | None) -> str:
    if x is None:
        return "ref"
    return "<0.001" if x < 0.001 else f"{x:.3f}"


def _summary(audits: list[Audit], total: int) -> str:
    flagged = [(a, g) for a in audits for g in a.flagged]
    if not flagged:
        return f"No adverse impact found across {len(audits)} attribute(s) and {total:,} records."
    sig = sum("statistically significant" in g.flags for _, g in flagged)
    names = "; ".join(f"{g.name} ({_num(g.impact_ratio)})" for _, g in flagged)
    return (f"{len(flagged)} group(s) fall below the impact-ratio threshold, "
            f"{sig} of them statistically significant: {names}.")


def _has_tpr(a: Audit) -> bool:
    return any(g.tpr is not None for g in a.groups)


# --- Markdown ------------------------------------------------------------

def to_markdown(audits: list[Audit], total: int, source: str = "") -> str:
    out = [f"# Bias audit — {source or 'decisions'}", "",
           f"_Generated {date.today()} · {total:,} records · threshold {audits[0].threshold:.2f}_", "",
           f"**Summary:** {_summary(audits, total)}", ""]
    for a in audits:
        tpr = _has_tpr(a)
        out += [f"## {a.attribute}", "", f"Reference group (highest rate): **{a.reference}**", ""]
        head = ["Group", "N", "Share", "Selected", "Rate", "Impact ratio", "p-value"]
        head += ["TPR", "TPR ratio"] if tpr else []
        head += ["Flags"]
        out += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for g in a.groups:
            row = [g.name, f"{g.n:,}", _pct(g.share), f"{g.selected:,}", _pct(g.rate),
                   _num(g.impact_ratio), _p(g.p_value)]
            row += [_pct(g.tpr), _num(g.tpr_ratio)] if tpr else []
            row += [", ".join(g.flags) or "✓"]
            out.append("| " + " | ".join(row) + " |")
        out.append("")
    out += ["---", "Impact ratio = group rate ÷ reference rate. Below the threshold suggests adverse impact "
            "(EEOC four-fifths rule). Groups under 2% of the sample are reported but not flagged.", ""]
    return "\n".join(out)


# --- JSON ----------------------------------------------------------------

def to_json(audits: list[Audit], total: int, source: str = "") -> str:
    return json.dumps({
        "source": source,
        "records": total,
        "summary": _summary(audits, total),
        "audits": [asdict(a) for a in audits],
    }, indent=2, ensure_ascii=False)


# --- HTML ----------------------------------------------------------------

def _chart(a: Audit) -> str:
    """Horizontal bars of impact ratio with a dashed threshold line."""
    row, label_w, bar_w = 30, 190, 420
    h = row * len(a.groups) + 28
    top = max([1.0] + [g.impact_ratio or 0 for g in a.groups])
    x = lambda v: label_w + v / top * bar_w
    tx = x(a.threshold)
    parts = [f'<svg viewBox="0 0 {label_w + bar_w + 60} {h}" role="img" '
             f'aria-label="Impact ratios for {escape(a.attribute)}">',
             f'<line x1="{tx:.1f}" x2="{tx:.1f}" y1="0" y2="{h - 22}" class="thr"/>'
             f'<text x="{tx:.1f}" y="{h - 6}" text-anchor="middle" class="val">{a.threshold:.2f}</text>']
    for i, g in enumerate(a.groups):
        y = i * row + 6
        ir = g.impact_ratio or 0
        cls = "bad" if "adverse impact" in g.flags else ("muted" if not g.eligible else "ok")
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 15}" text-anchor="end">{escape(g.name)}</text>'
            f'<rect class="{cls}" x="{label_w}" y="{y}" width="{max(x(ir) - label_w, 1):.1f}" height="20" rx="3"/>'
            f'<text x="{x(ir) + 6:.1f}" y="{y + 15}" class="val">{_num(ir)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def _table(a: Audit) -> str:
    tpr = _has_tpr(a)
    head = ["Group", "N", "Share", "Selected", "Rate", "Impact ratio", "p-value"]
    head += ["TPR", "TPR ratio"] if tpr else []
    head += ["Flags"]
    rows = []
    for g in a.groups:
        cells = [escape(g.name), f"{g.n:,}", _pct(g.share), f"{g.selected:,}", _pct(g.rate),
                 _num(g.impact_ratio), _p(g.p_value)]
        cells += [_pct(g.tpr), _num(g.tpr_ratio)] if tpr else []
        cells.append(" ".join(f'<span class="tag">{escape(f)}</span>' for f in g.flags) or "✓")
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return ("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--sub:#6b6b70;--line:#e4e2dc;--ok:#3a7d6b;--bad:#c2452d;--muted:#b9b6ad;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececee;--sub:#9a9aa1;--line:#2c2c30;--ok:#5fb39b;--bad:#ef7a5f;--muted:#55555b;--card:#1c1c1f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 16px 64px}h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:0 0 4px}
.sub{color:var(--sub);margin:0}.summary{border-left:4px solid var(--accent,var(--ok));padding:12px 16px;background:var(--card);margin:24px 0;border-radius:4px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;margin:20px 0;overflow-x:auto}
svg{width:100%;max-width:670px;margin:14px 0;font-size:13px}svg text{fill:var(--fg)}svg .val{fill:var(--sub);font-size:12px;paint-order:stroke;stroke:var(--card);stroke-width:3px}
.ok{fill:var(--ok)}.bad{fill:var(--bad)}.muted{fill:var(--muted)}.thr{stroke:var(--fg);stroke-dasharray:4 3;stroke-width:1.2}
table{border-collapse:collapse;width:100%;font-size:13.5px;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}td:last-child{white-space:normal;min-width:180px}
th{color:var(--sub);font-weight:600}.tag{display:inline-block;padding:1px 7px;border-radius:9px;background:color-mix(in srgb,var(--bad) 15%,transparent);color:var(--bad);font-size:12px;margin-right:4px}
footer{color:var(--sub);font-size:13px;margin-top:32px}
"""


def to_html(audits: list[Audit], total: int, source: str = "") -> str:
    accent = "var(--bad)" if any(a.flagged for a in audits) else "var(--ok)"
    sections = "".join(
        f'<section><h2>{escape(a.attribute)}</h2><p class="sub">Reference group: {escape(a.reference)}</p>'
        f"{_chart(a)}{_table(a)}</section>" for a in audits)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bias audit</title><style>{CSS}</style></head>
<body><main><h1>Bias audit</h1><p class="sub">{escape(source)} · {total:,} records · generated {date.today()}</p>
<div class="summary" style="--accent:{accent}">{escape(_summary(audits, total))}</div>{sections}
<footer>Impact ratio = group selection rate ÷ reference group rate. Bars left of the dashed line
({audits[0].threshold:.2f}) indicate potential adverse impact under the EEOC four-fifths rule.
Grey bars are groups under 2% of the sample or of unknown category; they are reported but not flagged.
p-values use Fisher's exact test when any cell is below 5, otherwise a two-proportion z-test.</footer>
</main></body></html>"""


RENDERERS = {"md": to_markdown, "json": to_json, "html": to_html}
