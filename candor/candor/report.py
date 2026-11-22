"""Render a Report as terminal text, JSON, Markdown, or a standalone HTML page."""
from __future__ import annotations

import json
from html import escape
from itertools import groupby

from .scanner import Report

ANSI = {"high": "\033[31m", "medium": "\033[33m", "low": "\033[36m",
        "bold": "\033[1m", "dim": "\033[2m", "reset": "\033[0m"}
ICON = {"high": "●", "medium": "◐", "low": "○"}


def _clip(text: str, n: int = 96) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _by_file(report: Report):
    return groupby(report.findings, key=lambda f: f.file)


def render_text(report: Report, color: bool = True) -> str:
    c = ANSI if color else {k: "" for k in ANSI}
    out = []
    for file, items in _by_file(report):
        out.append(f"\n{c['bold']}{file}{c['reset']}")
        for f in items:
            p = f.pattern
            out.append(f"  {c[p.severity]}{ICON[p.severity]} {p.severity:<6}{c['reset']} "
                       f"L{f.line:<4} {c['bold']}{p.name}{c['reset']}  {c['dim']}{p.category}{c['reset']}")
            out.append(f"         {c['dim']}“{_clip(f.excerpt)}”{c['reset']}")
            out.append(f"         → {p.fix}")
    n = report.counts()
    out.append(f"\n{c['bold']}Candor score {report.score}/100 · grade {report.grade}{c['reset']}  "
               f"{c['high']}{n['high']} high{c['reset']} · {c['medium']}{n['medium']} medium{c['reset']} · "
               f"{c['low']}{n['low']} low{c['reset']} across {len(report.files)} file(s)")
    return "\n".join(out)


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def render_markdown(report: Report) -> str:
    n = report.counts()
    out = [f"## Candor report: {report.score}/100 (grade {report.grade})", "",
           f"**{n['high']}** high · **{n['medium']}** medium · **{n['low']}** low across {len(report.files)} file(s)", ""]
    if not report.findings:
        return "\n".join(out + ["No deceptive patterns found. ✨"])
    out += ["| Severity | Pattern | Location | Excerpt | Fix |", "|---|---|---|---|---|"]
    for f in report.findings:
        cell = lambda s: s.replace("|", "\\|")
        out.append(f"| {ICON[f.pattern.severity]} {f.pattern.severity} | {f.pattern.name} | "
                   f"`{f.file}:{f.line}` | {cell(f.excerpt)} | {cell(f.pattern.fix)} |")
    return "\n".join(out)


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1a;--mute:#6b6b66;--line:#e6e5e0;--high:#c2410c;--medium:#b45309;--low:#0e7490;--ok:#15803d}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ededea;--mute:#9a9a93;--line:#2e2e2b;--high:#fb923c;--medium:#fbbf24;--low:#22d3ee;--ok:#4ade80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:880px;margin:0 auto;padding:40px 16px 64px}
header{display:flex;gap:28px;align-items:center;margin-bottom:32px;flex-wrap:wrap}
.ring{--p:0;width:112px;height:112px;border-radius:50%;display:grid;place-items:center;
 background:conic-gradient(var(--tone) calc(var(--p)*1%),var(--line) 0)}
.ring>div{width:88px;height:88px;border-radius:50%;background:var(--bg);display:grid;place-items:center;text-align:center}
.ring b{font-size:30px;line-height:1}.ring small{color:var(--mute);font-size:12px}
h1{margin:0 0 4px;font-size:24px}.sub{color:var(--mute);margin:0}
.pills{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.pill{font-size:12px;font-weight:600;padding:3px 10px;border-radius:99px;border:1px solid currentColor}
.high{color:var(--high)}.medium{color:var(--medium)}.low{color:var(--low)}
h2{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);margin:32px 0 12px;font-weight:600}
h2 span{float:right}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid currentColor;border-radius:10px;padding:14px 18px;margin-bottom:10px}
.card .top{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.card .name{color:var(--ink);font-weight:650}.card .meta{color:var(--mute);font-size:13px;margin-left:auto}
q{display:block;margin:8px 0;color:var(--ink);font-style:italic;quotes:"“" "”"}
.why,.fix,.refs{color:var(--mute);margin:4px 0 0;font-size:14px}.fix{color:var(--ink)}.refs{font-size:12px}
.empty{color:var(--ok);font-weight:600}
"""


def render_html(report: Report) -> str:
    tone = "var(--ok)" if report.score >= 75 else "var(--medium)" if report.score >= 40 else "var(--high)"
    n = report.counts()
    scores = {r.file: r.score for r in report.files}
    body = []
    for file, items in _by_file(report):
        body.append(f"<h2>{escape(file)}<span>{scores[file]}/100</span></h2>")
        for f in items:
            p = f.pattern
            body.append(
                f'<article class="card {p.severity}"><div class="top"><span class="pill">{p.severity}</span>'
                f'<span class="name">{escape(p.name)}</span><span class="meta">{escape(p.category)} · line {f.line}</span></div>'
                f"<q>{escape(f.excerpt)}</q><p class=why>{escape(p.why)}</p>"
                f"<p class=fix>→ {escape(p.fix)}</p><p class=refs>{escape(' · '.join(p.refs))}</p></article>")
    if not report.findings:
        body.append('<p class="empty">No deceptive patterns found. ✨</p>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Candor Report</title><style>{CSS}</style></head>
<body><main><header><div class="ring" style="--p:{report.score};--tone:{tone}"><div><div><b>{report.score}</b><br><small>grade {report.grade}</small></div></div></div>
<div><h1>Candor report</h1><p class="sub">Deceptive-design scan of {len(report.files)} file(s)</p>
<div class="pills"><span class="pill high">{n['high']} high</span><span class="pill medium">{n['medium']} medium</span><span class="pill low">{n['low']} low</span></div></div></header>
{''.join(body)}</main></body></html>"""


RENDERERS = {"text": render_text, "json": render_json, "md": render_markdown, "html": render_html}
