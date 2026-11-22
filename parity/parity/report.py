"""Render an audit as Markdown, JSON or a self-contained HTML page with SVG charts."""

import html
import json
from datetime import date

STATUS_ICON = {"reference": "★", "pass": "✓", "watch": "△", "fail": "✗", "excluded": "–"}


def _pct(x):
    return "—" if x is None else f"{x:.1%}"


def _num(x, fmt=".2f"):
    return "—" if x is None else format(x, fmt)


def _p(p):
    return "—" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")


def verdict(audit: dict) -> str:
    statuses = {g["status"] for sec in audit["sections"] for g in sec["groups"]}
    return "fail" if "fail" in statuses else "watch" if "watch" in statuses else "pass"


# ── Markdown ─────────────────────────────────────────────────────────────────

def to_markdown(audit: dict) -> str:
    out = [f"# Bias audit — {audit['title']}", "",
           f"*{audit['records']:,} records · {audit['measure']} · "
           f"threshold {audit['threshold']:.0%} · generated {audit['date']}*", "",
           f"**Overall verdict: {verdict(audit).upper()}**", ""]
    for sec in audit["sections"]:
        out += [f"## {sec['attribute']}", "",
                "| | Group | n | Selected | Rate | Impact ratio | p-value |",
                "|---|---|--:|--:|--:|--:|--:|"]
        rated, note = _split(sec["groups"])
        for g in rated:
            out.append(f"| {STATUS_ICON[g['status']]} | {g['group']} | {g['n']:,} | {g['selected']:,} | "
                       f"{_pct(g['rate'])} | {_num(g['impact_ratio'])} | {_p(g['p_value'])} |")
        out += ["", f"*{note}*", ""] if note else [""]
    if audit["proxies"]:
        out += ["## Proxy features", "",
                "Features that encode a protected attribute can reintroduce bias even when that attribute is removed.", "",
                "| Feature | Encodes | Cramér's V | Level |", "|---|---|--:|---|"]
        out += [f"| {p['feature']} | {p['attribute']} | {p['v']:.2f} | {p['level']} |"
                for p in audit["proxies"]]
        out.append("")
    out += ["---", "★ reference · ✓ pass · △ below threshold, not significant · "
            "✗ below threshold and significant"]
    return "\n".join(out) + "\n"


def to_json(audit: dict) -> str:
    return json.dumps({**audit, "verdict": verdict(audit)}, indent=2)


# ── HTML ─────────────────────────────────────────────────────────────────────

def bar_chart(groups: list[dict], threshold: float, width: int = 640) -> str:
    """Horizontal impact-ratio bars with a dashed line at the threshold."""
    rated = [g for g in groups if g["impact_ratio"] is not None]
    label_w, row_h, pad = 190, 30, 24
    plot_w = width - label_w - 60
    height = len(rated) * row_h + pad * 2
    x = lambda v: label_w + min(v, 1.2) / 1.2 * plot_w
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Impact ratios" class="chart">']
    for i, g in enumerate(rated):
        y = pad + i * row_h
        ir = g["impact_ratio"]
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 19}" text-anchor="end" class="lbl">{html.escape(g["group"])}</text>'
            f'<rect x="{label_w}" y="{y + 6}" width="{x(ir) - label_w:.1f}" height="18" rx="3" class="bar {g["status"]}"/>'
            f'<text x="{x(ir) + 6:.1f}" y="{y + 19}" class="val">{ir:.2f}</text>')
    tx = x(threshold)
    parts.append(f'<line x1="{tx:.1f}" x2="{tx:.1f}" y1="{pad - 8}" y2="{height - pad + 8}" class="thr"/>'
                 f'<text x="{tx:.1f}" y="{pad - 12}" text-anchor="middle" class="thr-lbl">{threshold:.0%} rule</text>'
                 "</svg>")
    return "".join(parts)


CSS = """
:root{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--card:#fff;--line:#e7e5e4;
--ref:#64748b;--pass:#16a34a;--watch:#d97706;--fail:#dc2626;--excl:#a8a29e}
@media (prefers-color-scheme:dark){:root{--bg:#0c0a09;--fg:#f5f5f4;--muted:#a8a29e;
--card:#1c1917;--line:#292524;--ref:#94a3b8;--pass:#4ade80;--watch:#fbbf24;--fail:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:40px 16px 80px}
h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}h2{font-size:19px;margin:0 0 12px}
.meta{color:var(--muted);margin:0 0 24px}section .meta{margin:12px 0 0;font-size:13px}
.verdict{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:600;color:var(--bg);margin-bottom:28px}
.verdict.pass{background:var(--pass)}.verdict.watch{background:var(--watch)}.verdict.fail{background:var(--fail)}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:20px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;margin-top:12px}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}th{color:var(--muted);font-weight:500;font-size:13px}
.chart{width:100%;height:auto}.lbl,.val{font-size:12px;fill:var(--fg)}.thr{stroke:var(--fg);stroke-dasharray:4 4;opacity:.6}
.thr-lbl{font-size:11px;fill:var(--muted)}
.bar.reference{fill:var(--ref)}.bar.pass{fill:var(--pass)}.bar.watch{fill:var(--watch)}.bar.fail{fill:var(--fail)}
.s{font-weight:700}.s.reference{color:var(--ref)}.s.pass{color:var(--pass)}.s.watch{color:var(--watch)}
.s.fail{color:var(--fail)}.s.excluded{color:var(--excl)}
.lvl-strong{color:var(--fail);font-weight:600}.lvl-moderate{color:var(--watch)}.lvl-weak{color:var(--muted)}
footer{color:var(--muted);font-size:13px}
"""


def to_html(audit: dict) -> str:
    e = html.escape
    v = verdict(audit)
    body = [f"<h1>Bias audit — {e(audit['title'])}</h1>",
            f"<div class='meta'>{audit['records']:,} records · {e(audit['measure'])} · "
            f"threshold {audit['threshold']:.0%} · generated {audit['date']}</div>",
            f"<div class='verdict {v}'>Overall: {v.upper()}</div>"]
    for sec in audit["sections"]:
        rated, note = _split(sec["groups"])
        note = f"<p class='meta'>{e(note)}</p>" if note else ""
        rows = "".join(
            f"<tr><td class='s {g['status']}' title='{g['status']}'>{STATUS_ICON[g['status']]}</td>"
            f"<td>{e(g['group'])}</td><td>{g['n']:,}</td><td>{g['selected']:,}</td><td>{_pct(g['rate'])}</td>"
            f"<td>{_num(g['impact_ratio'])}</td><td>{_p(g['p_value'])}</td></tr>" for g in rated)
        body.append(f"<section><h2>{e(sec['attribute'])}</h2>{bar_chart(sec['groups'], audit['threshold'])}"
                    "<table><tr><th></th><th>Group</th><th>n</th><th>Selected</th><th>Rate</th>"
                    f"<th>Impact ratio</th><th>p-value</th></tr>{rows}</table>{note}</section>")
    if audit["proxies"]:
        rows = "".join(f"<tr><td>{e(p['feature'])}</td><td>{e(p['attribute'])}</td><td>{p['v']:.2f}</td>"
                       f"<td class='lvl-{p['level']}'>{p['level']}</td></tr>" for p in audit["proxies"])
        body.append("<section><h2>Proxy features</h2><p class='meta'>Features that encode a protected "
                    "attribute can reintroduce bias even when that attribute is removed.</p>"
                    "<table><tr><th>Feature</th><th>Encodes</th><th>Cramér's V</th><th>Level</th></tr>"
                    f"{rows}</table></section>")
    body.append("<footer>★ reference · ✓ pass · △ below threshold, not significant · "
                "✗ below threshold and significant. "
                "Generated by Parity. A statistical screen, not a legal determination.</footer>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Bias audit — {e(audit['title'])}</title><style>{CSS}</style></head>"
            f"<body><main>{''.join(body)}</main></body></html>")


def build(title, records, measure, threshold, min_share, sections, proxies) -> dict:
    return {"title": title, "date": date.today().isoformat(), "records": records, "measure": measure,
            "threshold": threshold, "min_share": min_share, "sections": sections, "proxies": proxies}


def _split(groups):
    """Rated groups, plus a one-line note summarising the excluded ones."""
    rated = [g for g in groups if g["status"] != "excluded"]
    small = [g for g in groups if g["status"] == "excluded"]
    note = (f"{len(small)} group(s) under the minimum share were excluded: "
            + ", ".join(f"{g['group']} (n={g['n']})" for g in small)) if small else ""
    return rated, note
