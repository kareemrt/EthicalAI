"""Render scan reports as terminal text, Markdown, JSON or a standalone HTML page."""
from __future__ import annotations

import json
from html import escape

from . import __version__
from .rules import SEVERITIES
from .scanner import Report

ICON = {"high": "●", "medium": "◐", "low": "○"}
ANSI = {"high": "\033[31m", "medium": "\033[33m", "low": "\033[36m",
        "dim": "\033[2m", "bold": "\033[1m", "off": "\033[0m"}


def _summary(r: Report) -> str:
    return " · ".join(f"{r.count(s)} {s}" for s in SEVERITIES)


# --- terminal -----------------------------------------------------------------
def text(reports: list[Report], color: bool = False) -> str:
    c = ANSI if color else dict.fromkeys(ANSI, "")
    out = []
    for r in reports:
        out.append(f"{c['bold']}{r.source}{c['off']}  score {r.score}/100 ({r.grade})  "
                   f"{c['dim']}{_summary(r)}{c['off']}")
        for f in r.findings:
            sev = f.rule.severity
            out.append(f"  {c[sev]}{ICON[sev]} {f.rule.id} {f.rule.name}{c['off']}"
                       f"  {c['dim']}line {f.line} · {f.where}{c['off']}")
            out.append(f"      “{f.evidence}”")
            out.append(f"      {c['dim']}fix: {f.rule.fix}{c['off']}")
        if not r.findings:
            out.append("  ✓ no deceptive patterns found")
        out.append("")
    return "\n".join(out)


# --- markdown -----------------------------------------------------------------
def markdown(reports: list[Report]) -> str:
    out = ["# Candor report", ""]
    for r in reports:
        out += [f"## `{r.source}`", "",
                f"**Score {r.score}/100 · Grade {r.grade}** — {_summary(r)}", ""]
        if not r.findings:
            out += ["✓ No deceptive patterns found.", ""]
            continue
        out += ["| Severity | Rule | Where | Evidence |", "|---|---|---|---|"]
        for f in r.findings:
            ev = f.evidence.replace("|", "\\|")
            out.append(f"| {ICON[f.rule.severity]} {f.rule.severity} | **{f.rule.id}** {f.rule.name} "
                       f"| L{f.line} `{f.where}` | {ev} |")
        out += ["", "### How to fix", ""]
        for rule in {f.rule.id: f.rule for f in r.findings}.values():
            out.append(f"- **{rule.name}** — {rule.fix} _({'; '.join(rule.refs)})_")
        out.append("")
    return "\n".join(out)


# --- json ---------------------------------------------------------------------
def as_json(reports: list[Report]) -> str:
    return json.dumps({"tool": "candor", "version": __version__,
                       "reports": [r.as_dict() for r in reports]}, indent=2, ensure_ascii=False)


# --- html ---------------------------------------------------------------------
CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e6e6e3;
--high:#c62828;--medium:#b26a00;--low:#1f6f8b;--good:#2e7d32;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d20;--ink:#ececec;
--mute:#9a9aa0;--line:#2c2c30;--high:#ef6b6b;--medium:#e0a040;--low:#5fb4d1;--good:#6cc070}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:880px;margin:0 auto;padding:40px 16px}
header h1{font-size:28px;margin:0}header p{color:var(--mute);margin:4px 0 32px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px;margin-bottom:24px}
.top{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.ring{--p:0;width:96px;height:96px;border-radius:50%;display:grid;place-items:center;flex:none;
background:conic-gradient(var(--c) calc(var(--p)*1%),var(--line) 0)}
.ring b{width:76px;height:76px;border-radius:50%;background:var(--card);display:grid;place-items:center;font-size:26px}
.src{font-weight:600;word-break:break-all}.mute{color:var(--mute)}
.pills{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.pill{border:1px solid var(--line);border-radius:99px;padding:2px 10px;font-size:13px;display:flex;gap:6px;align-items:center}
.pill .dot{width:8px;height:8px;margin:0}
.f{border-top:1px solid var(--line);padding:16px 0 4px;display:grid;grid-template-columns:12px 1fr;gap:0 14px}
.dot{width:10px;height:10px;border-radius:50%;margin-top:7px}
.high .dot{background:var(--high)}.medium .dot{background:var(--medium)}.low .dot{background:var(--low)}
.f h3{margin:0;font-size:16px}.f h3 small{color:var(--mute);font-weight:400;margin-left:6px}
blockquote{margin:8px 0;padding:8px 12px;border-left:3px solid var(--line);color:var(--ink);font-style:italic}
.f p{margin:4px 0}.refs{font-size:13px;color:var(--mute)}
.ok{color:var(--good);font-weight:600}footer{color:var(--mute);font-size:13px;text-align:center}
"""


def html(reports: list[Report]) -> str:
    cards = []
    for r in reports:
        color = "var(--good)" if r.score >= 75 else "var(--medium)" if r.score >= 40 else "var(--high)"
        pills = "".join(f'<span class="pill {s}"><i class="dot"></i>{r.count(s)} {s}</span>' for s in SEVERITIES)
        items = "".join(
            f'<div class="f {f.rule.severity}"><span class="dot"></span><div>'
            f'<h3>{escape(f.rule.name)}<small>{f.rule.id} · {f.rule.category} · line {f.line} · '
            f'<code>{escape(f.where)}</code></small></h3>'
            f'<blockquote>{escape(f.evidence)}</blockquote>'
            f'<p><b>Why it matters.</b> {escape(f.rule.why)}</p>'
            f'<p><b>Fix.</b> {escape(f.rule.fix)}</p>'
            f'<p class="refs">{escape(" · ".join(f.rule.refs))}</p></div></div>'
            for f in r.findings) or '<p class="ok">✓ No deceptive patterns found.</p>'
        cards.append(
            f'<section class="card"><div class="top">'
            f'<div class="ring" style="--p:{r.score};--c:{color}"><b>{r.grade}</b></div>'
            f'<div><div class="src">{escape(r.title or r.source)}</div>'
            f'<div class="mute">{escape(r.source)} · score {r.score}/100</div>'
            f'<div class="pills">{pills}</div></div></div>{items}</section>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Candor report</title><style>{CSS}</style></head><body><main>'
            f'<header><h1>Candor report</h1><p>Deceptive design scan · {len(reports)} page(s)</p></header>'
            f'{"".join(cards)}<footer>Generated by Candor {__version__} · heuristic findings, '
            f'review each one in context</footer></main></body></html>')


FORMATS = {"text": text, "md": markdown, "json": as_json, "html": html}
