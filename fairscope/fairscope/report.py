"""Render audits as terminal text, Markdown, JSON or a self-contained HTML page."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from html import escape

from .metrics import Audit, worst

ICON = {"PASS": "✅", "REVIEW": "⚠️", "FAIL": "❌"}


def _pct(x):
    return "—" if x is None else f"{x:.1%}"


# ── terminal ────────────────────────────────────────────────────────────────
def text(audits: list[Audit], source: str) -> str:
    out = [f"fairscope · {source} · overall verdict: {worst(a.verdict for a in audits)}", ""]
    for a in audits:
        out.append(f"■ {a.attribute}  [{a.verdict}]  n={a.total:,}  overall selection {a.overall_rate:.1%}")
        width = max(len(g.name) for g in a.groups)
        for g in a.groups:
            bar = "█" * round(g.impact_ratio * 20)
            mark = " ◂" if g.flags else ""
            out.append(f"  {g.name:<{width}}  {g.rate:6.1%}  IR {g.impact_ratio:5.3f} {bar:<20}{mark}"
                       f"{'  ' + ', '.join(g.flags) if g.flags else ''}")
        out += [f"  • {f}" for f in a.findings] + [""]
    return "\n".join(out)


# ── markdown ────────────────────────────────────────────────────────────────
def markdown(audits: list[Audit], source: str) -> str:
    out = [f"# Bias audit — `{source}`", "",
           f"**Overall verdict: {ICON[worst(a.verdict for a in audits)]} {worst(a.verdict for a in audits)}**"
           f" · generated {date.today()} by fairscope", ""]
    for a in audits:
        labelled = a.tpr_gap is not None
        out += [f"## {a.attribute} — {ICON[a.verdict]} {a.verdict}", "",
                f"{a.total:,} records · overall selection rate {a.overall_rate:.1%} · threshold {a.threshold:.2f}", "",
                "| Group | n | Share | Selected | Rate | Impact ratio | p-value |"
                + (" TPR | FPR |" if labelled else "") + " Flags |",
                "|---|---:|---:|---:|---:|---:|---:|" + ("---:|---:|" if labelled else "") + "---|"]
        for g in a.groups:
            ir = f"**{g.impact_ratio:.3f}**" if g.impact_ratio < a.threshold and not g.excluded else f"{g.impact_ratio:.3f}"
            row = f"| {g.name} | {g.n:,} | {g.share:.1%} | {g.selected:,} | {g.rate:.1%} | {ir} | {g.p_value:.3g} |"
            if labelled:
                row += f" {_pct(g.tpr)} | {_pct(g.fpr)} |"
            out.append(row + f" {', '.join(g.flags)} |")
        out += [""] + [f"- {f}" for f in a.findings] + [""]
    return "\n".join(out)


# ── json ────────────────────────────────────────────────────────────────────
def as_json(audits: list[Audit], source: str) -> str:
    return json.dumps({"source": source, "verdict": worst(a.verdict for a in audits),
                       "audits": [asdict(a) for a in audits]}, indent=2)


# ── html ────────────────────────────────────────────────────────────────────
def _chart(a: Audit) -> str:
    """Horizontal bar chart of impact ratios with the threshold drawn as a dashed rule."""
    row, label_w, plot_w, pad = 30, 190, 420, 46
    h = len(a.groups) * row + pad
    x = lambda v: label_w + min(v, 1.0) * plot_w
    parts = [f'<svg viewBox="0 0 {label_w + plot_w + 70} {h}" role="img" '
             f'aria-label="Impact ratio by {escape(a.attribute)}">']
    tx, bottom = x(a.threshold), len(a.groups) * row + 8
    parts += [f'<line x1="{tx:.1f}" x2="{tx:.1f}" y1="0" y2="{bottom}" class="rule"/>',
              f'<text x="{tx:.1f}" y="{bottom + 22}" text-anchor="middle" class="val">{a.threshold:.2f} threshold</text>']
    for i, g in enumerate(a.groups):
        y = i * row + 8
        cls = "muted" if g.excluded else ("bad" if g.impact_ratio < a.threshold else "ok")
        parts += [f'<text x="{label_w - 10}" y="{y + 15}" text-anchor="end" class="lbl">{escape(g.name)}</text>',
                  f'<rect x="{label_w}" y="{y}" width="{max(x(g.impact_ratio) - label_w, 2):.1f}" height="20" rx="4" class="{cls}"/>',
                  f'<text x="{x(g.impact_ratio) + 6:.1f}" y="{y + 15}" class="val">{g.impact_ratio:.3f}</text>']
    return "".join(parts) + "</svg>"


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1b1d21;--sub:#5d6470;--line:#e3e4e8;--ok:#2f7d6d;--bad:#c2410c;--muted:#b6bac2;
--warn:#a16207;--pass:#e3f3ee;--review:#fdf1d8;--fail:#fde4d8}
@media (prefers-color-scheme:dark){:root{--bg:#111316;--card:#1a1d21;--ink:#eceef1;--sub:#9aa1ad;--line:#2a2e34;
--ok:#4fb39d;--bad:#f07a47;--warn:#e0b04a;--muted:#4a4f57;--pass:#173a31;--review:#3d3215;--fail:#45231a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 16px 64px}h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--sub);margin:0 0 28px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin:0 0 20px}
h2{font-size:18px;margin:0;display:flex;gap:10px;align-items:center}.pill{font-size:12px;font-weight:700;padding:3px 10px;border-radius:99px;letter-spacing:.04em}
.PASS{background:var(--pass);color:var(--ok)}.REVIEW{background:var(--review);color:var(--warn)}.FAIL{background:var(--fail);color:var(--bad)}
svg{width:100%;height:auto;margin:14px 0 6px}.lbl{font-size:13px;fill:var(--ink)}.val{font-size:12px;fill:var(--sub);font-variant-numeric:tabular-nums;paint-order:stroke;stroke:var(--card);stroke-width:5px}
.ok{fill:var(--ok)}.bad{fill:var(--bad)}.muted{fill:var(--muted)}.rule{stroke:var(--ink);stroke-dasharray:4 4;opacity:.55}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th{color:var(--sub);font-weight:600}
th:first-child,td:first-child,td:last-child,th:last-child{text-align:left}td.warn{color:var(--bad);font-weight:700}
ul{margin:14px 0 0;padding-left:20px}li{margin:3px 0}footer{color:var(--sub);font-size:12.5px;margin-top:28px}
"""


def html(audits: list[Audit], source: str) -> str:
    overall = worst(a.verdict for a in audits)
    cards = []
    for a in audits:
        labelled = a.tpr_gap is not None
        head = "<tr><th>Group</th><th>n</th><th>Rate</th><th>Impact ratio</th><th>p-value</th>" + \
               ("<th>TPR</th><th>FPR</th>" if labelled else "") + "<th>Flags</th></tr>"
        rows = "".join(
            f"<tr><td>{escape(g.name)}</td><td>{g.n:,}</td><td>{g.rate:.1%}</td>"
            f"<td class=\"{'warn' if g.impact_ratio < a.threshold and not g.excluded else ''}\">{g.impact_ratio:.3f}</td>"
            f"<td>{g.p_value:.3g}</td>" + (f"<td>{_pct(g.tpr)}</td><td>{_pct(g.fpr)}</td>" if labelled else "") +
            f"<td>{escape(', '.join(g.flags))}</td></tr>" for g in a.groups)
        notes = "".join(f"<li>{escape(f)}</li>" for f in a.findings) or "<li>No issues found.</li>"
        cards.append(
            f'<section class="card"><h2>{escape(a.attribute)} <span class="pill {a.verdict}">{a.verdict}</span></h2>'
            f'<p class="sub" style="margin:4px 0 0">{a.total:,} records · overall selection {a.overall_rate:.1%}</p>'
            f'{_chart(a)}<div class="tbl"><table>{head}{rows}</table></div><ul>{notes}</ul></section>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bias audit · {escape(source)}</title>'
            f'<style>{CSS}</style></head><body><main><h1>Bias audit <span class="pill {overall}">{overall}</span></h1>'
            f'<p class="sub">{escape(source)} · generated {date.today()} by fairscope</p>{"".join(cards)}'
            f'<footer>Impact ratio = group selection rate ÷ highest group selection rate. Ratios below the threshold '
            f'(EEOC four-fifths rule) with p &lt; 0.05 are reported as adverse impact. Groups under 2% of records are '
            f'shown but excluded from the verdict. A statistical screen is a starting point for investigation, not a '
            f'legal determination.</footer></main></body></html>')


RENDERERS = {"text": text, "md": markdown, "json": as_json, "html": html}
