"""Turn an Audit into something people can read: plain text, Markdown, HTML, JSON, SVG."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from html import escape

from .metrics import Audit, Dimension, Group

CAVEATS = (
    "The four-fifths rule is a screening heuristic, not proof of discrimination "
    "or of its absence. Significance uses a two-proportion z-test against the "
    "reference group. Results marked fragile flip if a single person's outcome "
    "changes; groups with fewer than 30 people are marked low-n. This tool does "
    "not replace an independent auditor or legal advice."
)


# ── helpers ──────────────────────────────────────────────────────────────────

def fmt_p(p: float | None) -> str:
    if p is None:
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def p_phrase(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def fmt_ir(ir: float | None) -> str:
    return "—" if ir is None else f"{ir:.2f}"


def notes(g: Group) -> str:
    tags = []
    if g.fragile:
        tags.append("fragile")
    if g.low_n:
        tags.append("low-n")
    return ", ".join(tags)


def verdict(g: Group) -> str:
    return {"reference": "reference", "ok": "ok", "adverse": "ADVERSE",
            "excluded": "excluded (<min share)"}[g.status]


def findings(a: Audit) -> list[str]:
    """Plain-language sentences a non-statistician can act on."""
    verb = "selected" if a.mode == "selection" else "scored above the median"
    out = []
    for d in a.dimensions:
        ref = d.reference
        for g in d.adverse:
            s = (f"{g.name} ({d.name}) were {verb} at {g.impact_ratio:.0%} the rate of "
                 f"{ref.name} — {g.rate:.1%} vs {ref.rate:.1%}.")
            if g.p_value is not None and g.p_value < 0.05:
                s += f" The gap is statistically significant ({p_phrase(g.p_value)})."
            else:
                s += " The gap is not statistically significant and may be noise."
            if g.fragile:
                s += " Fragile: one different outcome would change this verdict."
            if g.low_n:
                s += f" Only {g.n} people in this group."
            out.append(s)
    if not out:
        out.append(f"No group fell below the {a.threshold:.2f} impact-ratio benchmark.")
    for d in a.dimensions:
        for g in d.groups:
            if g.status == "ok" and g.p_value is not None and g.p_value < 0.05 and g.impact_ratio < 1:
                out.append(f"Watch: {g.name} ({d.name}) pass the benchmark at {g.impact_ratio:.2f}, "
                           f"but the gap to {d.reference.name} is statistically significant "
                           f"({p_phrase(g.p_value)}).")
    return out


def data_notes(a: Audit) -> list[str]:
    """What was left out of the audit, and why. Disclosed, never hidden."""
    out = []
    for d in a.dimensions:
        small = [g.name for g in d.groups if g.status == "excluded"]
        if small:
            out.append(f"{len(small)} {d.name} group(s) under {a.min_share:.0%} of the sample "
                       f"were reported but not flagged: {', '.join(small)}.")
        if d.unknown:
            out.append(f"{d.unknown:,} record(s) had unknown {d.name} and were left out of that dimension.")
    return out


# ── plain text (terminal) ────────────────────────────────────────────────────

def to_text(a: Audit, color: bool = False) -> str:
    red, dim, bold, reset = ("\033[31m", "\033[2m", "\033[1m", "\033[0m") if color else ("",) * 4

    def bar(ir: float | None, width: int = 12) -> str:
        if ir is None:
            return " " * width
        filled = round(min(ir, 1) * width)
        return "█" * filled + "░" * (width - filled)

    lines = [f"{bold}Parity audit{reset} · outcome '{a.outcome}' ({a.mode}) · "
             f"{a.total:,} records · {a.positives / a.total:.1%} favourable · "
             f"threshold {a.threshold:.2f}", ""]
    for d in a.dimensions:
        width = max(12, *(len(g.name) for g in d.groups))
        lines.append(f"{bold}{d.name}{reset}" + (f"{dim}  (unknown: {d.unknown:,}){reset}" if d.unknown else ""))
        lines.append(f"{dim}  {'group':<{width}}  {'n':>6}  {'rate':>6}  {'impact':<17}  {'p':>6}  verdict{reset}")
        for g in d.groups:
            row = (f"  {g.name:<{width}}  {g.n:>6,}  {g.rate:>6.1%}  {bar(g.impact_ratio)} "
                   f"{fmt_ir(g.impact_ratio):>4}  {fmt_p(g.p_value):>6}  {verdict(g)}")
            if notes(g):
                row += f" {dim}[{notes(g)}]{reset}"
            if g.status == "adverse":
                row = red + row + reset
            elif g.status == "excluded":
                row = dim + row + reset
            lines.append(row)
        lines.append("")
    lines.append(f"{bold}Findings{reset}")
    lines += [f"  • {f}" for f in findings(a)]
    if data_notes(a):
        lines += ["", f"{bold}Data notes{reset}"] + [f"{dim}  • {n}{reset}" for n in data_notes(a)]
    return "\n".join(lines)


# ── Markdown ─────────────────────────────────────────────────────────────────

def to_markdown(a: Audit) -> str:
    md = [f"# Parity audit — `{a.outcome}`", "",
          f"| Records | Favourable rate | Mode | Threshold | Verdict |",
          f"|---:|---:|---|---:|---|",
          f"| {a.total:,} | {a.positives / a.total:.1%} | {a.mode} | {a.threshold:.2f} | "
          f"{'⚠️ adverse impact found' if a.has_adverse_impact else '✅ no adverse impact'} |",
          "", "## Findings", ""]
    md += [f"- {f}" for f in findings(a)]
    if data_notes(a):
        md += ["", "### Data notes", ""] + [f"- {n}" for n in data_notes(a)]
    for d in a.dimensions:
        md += ["", f"## {d.name}", "",
               "| Group | n | Rate | Impact ratio | p-value | Verdict | Notes |",
               "|---|---:|---:|---:|---:|---|---|"]
        for g in d.groups:
            v = f"**{verdict(g)}**" if g.status == "adverse" else verdict(g)
            md.append(f"| {g.name} | {g.n:,} | {g.rate:.1%} | {fmt_ir(g.impact_ratio)} | "
                      f"{fmt_p(g.p_value)} | {v} | {notes(g)} |")
        if d.unknown:
            md += ["", f"_Unknown {d.name}: {d.unknown:,} record(s)._"]
    md += ["", "---", f"_{CAVEATS}_", ""]
    return "\n".join(md)


# ── JSON ─────────────────────────────────────────────────────────────────────

def to_json(a: Audit) -> str:
    data = asdict(a)
    data["has_adverse_impact"] = a.has_adverse_impact
    data["findings"] = findings(a)
    data["data_notes"] = data_notes(a)
    return json.dumps(data, indent=2)


# ── SVG chart ────────────────────────────────────────────────────────────────

SVG_STYLE = """
.lbl{font:12px system-ui,sans-serif;fill:var(--ink,#1f2328)}
.val{font:600 11px ui-monospace,monospace;fill:var(--ink,#1f2328);paint-order:stroke;
 stroke:var(--bg,#ffffff);stroke-width:4px;stroke-linejoin:round}
.axis{font:10px ui-monospace,monospace;fill:var(--muted,#6e7781)}
.grid{stroke:var(--line,#d0d7de);stroke-width:1}
.thr{stroke:var(--warn,#cf222e);stroke-width:1.5;stroke-dasharray:4 3}
.b-reference{fill:var(--ref,#0969da)}.b-ok{fill:var(--ok,#54aeff)}
.b-adverse{fill:var(--warn,#cf222e)}.b-excluded{fill:var(--muted,#8c959f);opacity:.55}
@media (prefers-color-scheme:dark){
 .lbl,.val{fill:var(--ink,#e6edf3)}.val{stroke:var(--bg,#0d1117)}.axis{fill:var(--muted,#8b949e)}
 .grid{stroke:var(--line,#30363d)}.thr{stroke:var(--warn,#ff7b72)}
 .b-reference{fill:var(--ref,#58a6ff)}.b-ok{fill:var(--ok,#1f6feb)}
 .b-adverse{fill:var(--warn,#ff7b72)}}
"""


def to_svg(d: Dimension, threshold: float = 0.8, standalone: bool = True) -> str:
    """Horizontal impact-ratio bars with the threshold drawn as a dashed line."""
    label_w = min(300, 20 + 7 * max(len(g.name) for g in d.groups))
    bar_w, row_h, top = 420, 26, 24
    width, height = label_w + bar_w + 60, top + row_h * len(d.groups) + 8
    scale = max(1.0, *(g.impact_ratio or 0 for g in d.groups))
    x = lambda v: label_w + bar_w * v / scale  # noqa: E731

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'width="{width}" role="img" aria-label="Impact ratios by {escape(d.name)}">']
    if standalone:
        parts.append(f"<style>{SVG_STYLE}</style>")
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        parts.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 6}" y2="{height - 6}"/>'
                     f'<text class="axis" x="{x(t):.1f}" y="{top - 10}" text-anchor="middle">{t:g}</text>')
    parts.append(f'<line class="thr" x1="{x(threshold):.1f}" x2="{x(threshold):.1f}" '
                 f'y1="{top - 6}" y2="{height - 6}"><title>threshold {threshold:g}</title></line>')
    for i, g in enumerate(d.groups):
        y = top + i * row_h
        ir = g.impact_ratio or 0
        parts.append(f'<text class="lbl" x="{label_w - 10}" y="{y + 15}" text-anchor="end">{escape(g.name)}</text>'
                     f'<rect class="b-{g.status}" x="{label_w}" y="{y + 4}" width="{max(ir, 0.002) * bar_w / scale:.1f}" '
                     f'height="{row_h - 9}" rx="3"><title>{escape(g.name)}: {fmt_ir(g.impact_ratio)} '
                     f'(n={g.n}, {g.status})</title></rect>'
                     f'<text class="val" x="{x(ir) + 6:.1f}" y="{y + 15}">{fmt_ir(g.impact_ratio)}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── HTML (self-contained, no external requests) ──────────────────────────────

HTML_CSS = """
:root{--bg:#ffffff;--card:#f6f8fa;--ink:#1f2328;--muted:#6e7781;--line:#d0d7de;
 --ref:#0969da;--ok:#54aeff;--warn:#cf222e;--good:#1a7f37}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#161b22;--ink:#e6edf3;
 --muted:#8b949e;--line:#30363d;--ref:#58a6ff;--ok:#1f6feb;--warn:#ff7b72;--good:#3fb950}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:40px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:40px 0 12px}
.sub{color:var(--muted);margin:0 0 28px}code{font:13px ui-monospace,monospace}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat b{display:block;font-size:22px}.stat span{color:var(--muted);font-size:13px}
.bad b{color:var(--warn)}.good b{color:var(--good)}
ul.find{padding-left:20px}ul.find li{margin:6px 0}
.chart{overflow-x:auto;margin:8px 0 12px}.chart svg{max-width:100%;height:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left;white-space:normal}
th{color:var(--muted);font-weight:500}.tbl{overflow-x:auto}
tr.adverse td{color:var(--warn);font-weight:600}tr.excluded td{color:var(--muted)}
.unk{color:var(--muted);font-size:13px}
.notes{color:var(--muted);font-size:13.5px}.notes summary{cursor:pointer}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
"""


def to_html(a: Audit, source: str = "") -> str:
    rate = a.positives / a.total
    bad = a.has_adverse_impact
    n_adverse = sum(len(d.adverse) for d in a.dimensions)
    body = [
        f"<h1>Parity audit</h1><p class='sub'>Outcome <code>{escape(a.outcome)}</code> · {a.mode} mode"
        + (f" · <code>{escape(source)}</code>" if source else "") + f" · {date.today():%d %b %Y}</p>",
        "<div class='stats'>",
        f"<div class='stat'><b>{a.total:,}</b><span>records</span></div>",
        f"<div class='stat'><b>{rate:.1%}</b><span>favourable outcomes</span></div>",
        f"<div class='stat'><b>{a.threshold:.2f}</b><span>impact-ratio threshold</span></div>",
        f"<div class='stat {'bad' if bad else 'good'}'><b>{n_adverse}</b>"
        f"<span>group(s) with adverse impact</span></div></div>",
        "<h2>Findings</h2><ul class='find'>",
        *(f"<li>{escape(f)}</li>" for f in findings(a)),
        "</ul>",
    ]
    if data_notes(a):
        body += ["<details class='notes'><summary>Data notes</summary><ul>",
                 *(f"<li>{escape(n)}</li>" for n in data_notes(a)), "</ul></details>"]
    for d in a.dimensions:
        body.append(f"<h2>{escape(d.name)}</h2><div class='chart'>{to_svg(d, a.threshold, standalone=False)}</div>")
        body.append("<div class='tbl'><table><tr><th>Group</th><th>n</th><th>Rate</th>"
                    "<th>Impact ratio</th><th>p-value</th><th>Verdict</th><th>Notes</th></tr>")
        for g in d.groups:
            body.append(f"<tr class='{g.status}'><td>{escape(g.name)}</td><td>{g.n:,}</td><td>{g.rate:.1%}</td>"
                        f"<td>{fmt_ir(g.impact_ratio)}</td><td>{fmt_p(g.p_value)}</td>"
                        f"<td>{verdict(g)}</td><td>{notes(g)}</td></tr>")
        body.append("</table></div>")
        if d.unknown:
            body.append(f"<p class='unk'>Unknown {escape(d.name)}: {d.unknown:,} record(s), not included above.</p>")
    body.append(f"<footer>{escape(CAVEATS)}</footer>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Parity audit</title><style>{HTML_CSS}{SVG_STYLE}</style></head>"
            f"<body><main>{''.join(body)}</main></body></html>")
