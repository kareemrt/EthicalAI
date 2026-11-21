"""Renderers: terminal text, Markdown, JSON, self-contained HTML and SVG charts."""

import json
from dataclasses import asdict
from datetime import date
from html import escape

STATUS_TEXT = {"reference": "reference", "ok": "ok", "review": "review", "flag": "FLAG"}
STATUS_ICON = {"reference": "◆", "ok": "✓", "review": "?", "flag": "✗"}
ANSI = {"reference": "\033[2m", "ok": "\033[32m", "review": "\033[33m",
        "flag": "\033[1;31m", "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m"}


def fmt_p(p):
    if p is None:
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def fmt_ratio(r):
    return "—" if r is None else f"{r:.2f}"


def rate_name(a):
    return "selection rate" if a.mode == "selection" else "scoring rate"


def verdict(audits):
    flags = sum(len(a.flagged) for a in audits)
    reviews = sum(len(a.review) for a in audits)
    if flags:
        return "fail", f"{flags} group(s) show statistically significant adverse impact"
    if reviews:
        return "review", f"{reviews} group(s) below the threshold but not conclusive — investigate"
    return "pass", "no group fell below the impact-ratio threshold"


def _notes(a):
    notes = [f"{a.total:,} records · {a.unknown:,} with unknown category (excluded from rates, reported per LL144)"]
    if a.mode == "scoring":
        notes.append(f"scoring rate = share scoring above the sample median ({a.median_score:g})")
    if a.skipped:
        notes.append(f"{a.skipped:,} rows skipped: score not numeric")
    if any(g.small for g in a.groups):
        notes.append("* group is under 2% of records — not used as reference, never auto-flagged")
    return notes


# ── terminal ────────────────────────────────────────────────────────────────

def _bar(ratio, threshold, width=20):
    if ratio is None:
        return " " * (width + 1)
    filled = min(ratio, 1.0) * width
    full, part = int(filled), filled - int(filled)
    cells = list("█" * full + ("▌" if part >= 0.5 else "") )
    cells += [" "] * (width - len(cells))
    mark = round(threshold * width)
    if cells[mark - 1] == " ":
        cells[mark - 1] = "┊"
    return "".join(cells[:width]) + " "


def render_text(audits, source="", color=False):
    c = (lambda k: ANSI[k]) if color else (lambda k: "")
    out = []
    a0 = audits[0]
    out.append(f"{c('bold')}Parity bias audit{c('reset')}  {c('dim')}{source} · "
               f"{a0.mode} mode · threshold {a0.threshold} · α={a0.alpha}{c('reset')}")
    for a in audits:
        out.append("")
        out.append(f"{c('bold')}▸ {a.attribute}{c('reset')}")
        w = max([len(g.group) + (1 if g.small else 0) for g in a.groups] + [5])
        out.append(f"{c('dim')}  {'group':<{w}}  {'n':>6}  {'rate':>6}  "
                   f"{'impact ratio':<26}  {'p':>6}  status{c('reset')}")
        for g in a.groups:
            name = g.group + ("*" if g.small else "")
            out.append(f"  {name:<{w}}  {g.n:>6,}  {g.rate:>6.1%}  "
                       f"{fmt_ratio(g.ratio):>4} {_bar(g.ratio, a.threshold)}  {fmt_p(g.p_value):>6}  "
                       f"{c(g.status)}{STATUS_ICON[g.status]} {STATUS_TEXT[g.status]}{c('reset')}")
        for note in _notes(a):
            out.append(f"  {c('dim')}{note}{c('reset')}")
    state, msg = verdict(audits)
    tone = {"fail": "flag", "review": "review", "pass": "ok"}[state]
    out.append("")
    out.append(f"{c(tone)}{state.upper()}{c('reset')} — {msg}")
    return "\n".join(out)


# ── markdown ────────────────────────────────────────────────────────────────

def render_markdown(audits, source=""):
    state, msg = verdict(audits)
    a0 = audits[0]
    out = [f"# Bias audit — {source or 'dataset'}", "",
           f"**Result: {state.upper()}** — {msg}.", "",
           f"Mode: `{a0.mode}` · impact-ratio threshold: `{a0.threshold}` · "
           f"significance level: `{a0.alpha}` · generated {date.today().isoformat()} by Parity", ""]
    for a in audits:
        out += [f"## {a.attribute}", "",
                f"| Group | n | Selected | {rate_name(a).capitalize()} | Impact ratio | p-value | Status |",
                "|---|--:|--:|--:|--:|--:|---|"]
        for g in a.groups:
            name = escape(g.group) + ("\\*" if g.small else "")
            out.append(f"| {name} | {g.n:,} | {g.hits:,} | {g.rate:.1%} | {fmt_ratio(g.ratio)} | "
                       f"{fmt_p(g.p_value)} | {STATUS_ICON[g.status]} {STATUS_TEXT[g.status]} |")
        out.append("")
        out += [f"- {n.lstrip('* ')}" for n in _notes(a)]
        out.append("")
    return "\n".join(out)


# ── json ────────────────────────────────────────────────────────────────────

def render_json(audits, source=""):
    state, msg = verdict(audits)
    return json.dumps({"source": source, "result": state, "summary": msg,
                       "audits": [asdict(a) for a in audits]}, indent=2, ensure_ascii=False)


# ── svg ─────────────────────────────────────────────────────────────────────

SVG_STYLE = """
.t{font:13px system-ui,-apple-system,Segoe UI,sans-serif;fill:var(--ink)}
.m{fill:var(--muted);font-size:11px}.b{font-weight:600}
.grid{stroke:var(--line)}.thr{stroke:var(--flag);stroke-dasharray:4 3}
.reference{fill:var(--ref)}.ok{fill:var(--ok)}.review{fill:var(--review)}.flag{fill:var(--flag)}
"""
SVG_TOKENS = """
svg{--ink:#1d2330;--muted:#6b7280;--line:#e5e7eb;--ref:#64748b;--ok:#0f9d7a;--review:#d99a0b;--flag:#d6455d}
@media (prefers-color-scheme:dark){svg{--ink:#e6e9ef;--muted:#9aa3b2;--line:#2b3240;--ref:#94a3b8;--ok:#34d3a6;--review:#f5b83d;--flag:#ff6b81}}
"""


def svg_chart(a, standalone=False, title=True, width=680):
    """Horizontal impact-ratio bars with the threshold drawn as a dashed line."""
    row, left, right = 30, 270, 60
    top = 34 if title else 22
    plot = width - left - right
    height = top + row * len(a.groups) + 28
    domain = max([1.0] + [g.ratio or 0 for g in a.groups])
    x = lambda v: left + plot * v / domain
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'width="100%" role="img" aria-label="Impact ratios by {escape(a.attribute)}">']
    if standalone:
        parts.append(f"<style>{SVG_TOKENS}{SVG_STYLE}</style>")
    if title:
        parts.append(f'<text class="t b" x="0" y="16">Impact ratio by {escape(a.attribute)}</text>')
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{top - 6}" y2="{height - 22}"/>'
                     f'<text class="t m" x="{x(v):.1f}" y="{height - 6}" text-anchor="middle">{v:g}</text>')
    for i, g in enumerate(a.groups):
        y = top + i * row
        label = escape(g.group if len(g.group) <= 36 else g.group[:35] + "…") + ("*" if g.small else "")
        parts.append(f'<text class="t" x="{left - 10}" y="{y + 15}" text-anchor="end">{label}</text>')
        w = max(x(g.ratio or 0) - left, 1.5)
        parts.append(f'<rect class="{g.status}" x="{left}" y="{y + 3}" width="{w:.1f}" height="17" rx="3">'
                     f'<title>{escape(g.group)}: {fmt_ratio(g.ratio)} (n={g.n})</title></rect>')
        parts.append(f'<text class="t m" x="{left + w + 6:.1f}" y="{y + 15}">{fmt_ratio(g.ratio)}</text>')
    tx = x(a.threshold)
    parts.append(f'<line class="thr" x1="{tx:.1f}" x2="{tx:.1f}" y1="{top - 8}" y2="{height - 22}"/>'
                 f'<text class="t m" x="{tx:.1f}" y="{top - 12}" text-anchor="middle">{a.threshold:g} threshold</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── html ────────────────────────────────────────────────────────────────────

HTML_CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1d2330;--muted:#6b7280;--line:#e5e7eb;
--ref:#64748b;--ok:#0f9d7a;--review:#d99a0b;--flag:#d6455d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f131a;--card:#171c25;--ink:#e6e9ef;
--muted:#9aa3b2;--line:#2b3240;--ref:#94a3b8;--ok:#34d3a6;--review:#f5b83d;--flag:#ff6b81}}
:root[data-theme=dark]{--bg:#0f131a;--card:#171c25;--ink:#e6e9ef;--muted:#9aa3b2;--line:#2b3240;
--ref:#94a3b8;--ok:#34d3a6;--review:#f5b83d;--flag:#ff6b81}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}
.sub{color:var(--muted);margin:0 0 24px}
.verdict{border-radius:12px;padding:14px 18px;margin-bottom:24px;font-weight:600;border:1px solid}
.verdict.fail{border-color:var(--flag);color:var(--flag)}
.verdict.review{border-color:var(--review);color:var(--review)}
.verdict.pass{border-color:var(--ok);color:var(--ok)}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:20px}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;margin-top:16px;font-size:14px}
th,td{padding:7px 6px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left;white-space:normal;min-width:120px;max-width:220px}th{color:var(--muted);font-weight:500}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;font-weight:600;color:#fff}
.pill.reference{background:var(--ref)}.pill.ok{background:var(--ok)}
.pill.review{background:var(--review)}.pill.flag{background:var(--flag)}
ul{color:var(--muted);font-size:13px;margin:12px 0 0;padding-left:18px}
footer{color:var(--muted);font-size:13px}
""" + SVG_STYLE


def render_html(audits, source=""):
    state, msg = verdict(audits)
    a0 = audits[0]
    body = [f"<h1>Bias audit</h1><p class=sub>{escape(source)} · {a0.mode} mode · "
            f"threshold {a0.threshold} · α = {a0.alpha} · {date.today().isoformat()}</p>",
            f'<div class="verdict {state}">{state.upper()} — {escape(msg)}</div>']
    for a in audits:
        rows = "".join(
            f"<tr><td>{escape(g.group)}{'*' if g.small else ''}</td><td>{g.n:,}</td><td>{g.hits:,}</td>"
            f"<td>{g.rate:.1%}</td><td>{fmt_ratio(g.ratio)}</td><td>{fmt_p(g.p_value)}</td>"
            f'<td><span class="pill {g.status}">{STATUS_TEXT[g.status]}</span></td></tr>'
            for g in a.groups)
        notes = "".join(f"<li>{escape(n.lstrip('* '))}</li>" for n in _notes(a))
        body.append(f"<section><h2>{escape(a.attribute)}</h2>{svg_chart(a, title=False)}<div class=scroll><table>"
                    f"<tr><th>Group</th><th>n</th><th>Selected</th><th>{rate_name(a).capitalize()}</th>"
                    f"<th>Impact ratio</th><th>p-value</th><th>Status</th></tr>{rows}</table></div>"
                    f"<ul>{notes}</ul></section>")
    body.append("<footer>Generated by Parity. Impact ratio = group rate ÷ highest group rate. "
                "p-values: two-sided Fisher's exact test vs. the reference group.</footer>")
    return (f"<!doctype html><html lang=en><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Bias audit report</title><style>{HTML_CSS}</style><main>{''.join(body)}</main></html>")
