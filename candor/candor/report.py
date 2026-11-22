"""Render reports as terminal text, JSON, Markdown or a standalone HTML page."""
from __future__ import annotations

import json
import os
import sys
from html import escape

from .rules import RULES
from .scanner import Report

NAMES = {r.id: r.name for r in RULES}
REFS = {r.id: r.reference for r in RULES}
ICON = {"high": "●", "medium": "◐", "low": "○"}


def _color(enabled: bool):
    codes = {"high": "31", "medium": "33", "low": "36", "dim": "2", "bold": "1", "ok": "32"}
    return (lambda s, k: f"\033[{codes[k]}m{s}\033[0m") if enabled else (lambda s, k: s)


def text(reports: list[Report], color: bool | None = None) -> str:
    if color is None:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    c = _color(color)
    out = []
    for r in reports:
        n = r.counts()
        grade_key = "ok" if r.grade in "AB" else "medium" if r.grade == "C" else "high"
        out.append(c(f"\n{r.source}", "bold") + "  " +
                   c(f"{r.grade}  {r.score}/100", grade_key) + "  " +
                   c(f"{n['high']} high · {n['medium']} medium · {n['low']} low", "dim"))
        if not r.findings:
            out.append(c("  ✓ No dark patterns detected.", "ok"))
        for f in r.findings:
            loc = f"L{f.line}" if f.line else "page"
            out.append(f"  {c(ICON[f.severity] + ' ' + f.severity.upper().ljust(6), f.severity)} "
                       f"{c(NAMES[f.rule], 'bold')}  {c(loc, 'dim')}")
            out.append(f"      “{f.evidence}”")
            out.append(c(f"      why: {f.why}", "dim"))
            out.append(c(f"      fix: {f.fix}", "dim"))
    return "\n".join(out) + "\n"


def as_json(reports: list[Report]) -> str:
    return json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False)


def markdown(reports: list[Report]) -> str:
    out = ["# Candor dark-pattern report\n"]
    for r in reports:
        n = r.counts()
        out += [f"## `{r.source}` — grade **{r.grade}** ({r.score}/100)\n",
                f"{n['high']} high · {n['medium']} medium · {n['low']} low\n"]
        if not r.findings:
            out.append("✅ No dark patterns detected.\n")
            continue
        out.append("| Severity | Pattern | Line | Evidence | Fix |\n|---|---|---|---|---|")
        for f in r.findings:
            ev = f.evidence.replace("|", "\\|")
            out.append(f"| {ICON[f.severity]} {f.severity} | {NAMES[f.rule]} | {f.line or '—'} "
                       f"| {ev} | {f.fix} |")
        out.append("")
    return "\n".join(out)


def html(reports: list[Report]) -> str:
    cards = []
    for r in reports:
        n = r.counts()
        items = "".join(f"""
      <li class="f {f.severity}">
        <div class="h"><span class="sev">{f.severity}</span><b>{escape(NAMES[f.rule])}</b>
          <span class="ln">{'line ' + str(f.line) if f.line else 'page-wide'}</span></div>
        <q>{escape(f.evidence)}</q>
        <p><span>Why</span>{escape(f.why)}</p>
        <p><span>Fix</span>{escape(f.fix)}</p>
        <small>{escape(REFS[f.rule])}</small>
      </li>""" for f in r.findings) or '<li class="ok">✓ No dark patterns detected.</li>'
        cards.append(f"""
  <section>
    <header>
      <div class="grade g{r.grade}">{r.grade}</div>
      <div><h2>{escape(r.source)}</h2>
        <div class="meter"><i style="width:{r.score}%"></i></div>
        <p class="sum">{r.score}/100 · <b class="high">{n['high']}</b> high ·
          <b class="medium">{n['medium']}</b> medium · <b class="low">{n['low']}</b> low</p></div>
    </header>
    <ul>{items}</ul>
  </section>""")
    return _PAGE.replace("{{BODY}}", "".join(cards))


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candor report</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1e;--mute:#6b6b70;--line:#e6e6e3;
--high:#c62f2f;--medium:#b7791f;--low:#2b7a9b;--ok:#2f855a}
@media (prefers-color-scheme:dark){:root{--bg:#111113;--card:#1b1b1f;--ink:#ececf0;--mute:#9a9aa3;
--line:#2c2c31;--high:#ef6b6b;--medium:#e0a84a;--low:#5fb3d3;--ok:#5cc28a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;padding:32px 16px}
main{max-width:820px;margin:auto}h1{font-size:22px;margin:0 0 4px}.lede{color:var(--mute);margin:0 0 24px}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:20px}
header{display:flex;gap:16px;align-items:center}h2{font-size:15px;margin:0;word-break:break-all}
.grade{flex:none;width:56px;height:56px;border-radius:12px;display:grid;place-items:center;
font-size:28px;font-weight:700;color:#fff}.gA,.gB{background:var(--ok)}.gC{background:var(--medium)}
.gD,.gF{background:var(--high)}header>div:last-child{flex:1;min-width:0}
.meter{height:6px;background:var(--line);border-radius:3px;margin:8px 0 4px;overflow:hidden}
.meter i{display:block;height:100%;background:var(--ink)}.sum{margin:0;color:var(--mute);font-size:13px}
b.high{color:var(--high)}b.medium{color:var(--medium)}b.low{color:var(--low)}
ul{list-style:none;padding:0;margin:16px 0 0}.f{border-left:3px solid;padding:10px 14px;margin-top:10px;
border-radius:0 8px 8px 0;background:color-mix(in srgb,currentColor 5%,transparent)}
.f.high{color:var(--high)}.f.medium{color:var(--medium)}.f.low{color:var(--low)}
.f>*{color:var(--ink)}.h{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.sev{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:inherit!important}
.f .sev{color:currentColor}.ln{margin-left:auto;color:var(--mute);font-size:12px}
q{display:block;margin:6px 0;font-style:italic}p{margin:2px 0;font-size:14px}
p span{display:inline-block;width:34px;color:var(--mute);font-size:12px}
small{display:block;margin-top:6px;color:var(--mute)!important;font-size:12px}.ok{color:var(--ok);padding:8px 0}
</style></head><body><main>
<h1>Candor report</h1><p class="lede">Dark-pattern scan. Heuristic findings: each one is evidence for a human to review.</p>
{{BODY}}
</main></body></html>
"""
