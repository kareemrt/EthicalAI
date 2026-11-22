"""Render a Report as terminal text, JSON, or a self-contained HTML page."""
from __future__ import annotations

import html
import json
import os
import sys

from .analyze import Report

# --------------------------------------------------------------------------
# Terminal
# --------------------------------------------------------------------------

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def _bar(score: int, width: int = 30) -> str:
    n = round(score / 100 * width)
    color = "32" if score >= 80 else "33" if score >= 60 else "31"
    return _c(color, "█" * n) + _c("2", "░" * (width - n))


def to_text(r: Report, limit: int = 8) -> str:
    rd, out = r.readability, []
    out.append(_c("1", f"\n  {r.source}"))
    out.append(f"  {_bar(r.score)}  {_c('1', f'{r.score}/100')}  grade {_c('1', r.grade)}\n")
    level = _c("31" if rd.grade > r.target_grade else "32", f"grade {rd.grade:g}")
    out.append(f"  Reading level   {level}  (target ≤ {r.target_grade:g})")
    out.append(f"  Sentences       {rd.sentences}, avg {rd.avg_sentence:g} words")
    out.append(f"  Findings        {len(r.of('jargon'))} jargon · {len(r.of('passive'))} passive · {len(r.of('long'))} long\n")

    out.append(_c("1", "  Can the reader act on it?"))
    for e in r.essentials:
        mark = _c("32", "✓") if e.ok else _c("31", "✗")
        note = _c("2", f"  “{e.evidence}”") if e.ok and e.evidence else ("" if e.ok else _c("33", f"  → {e.advice}"))
        out.append(f"  {mark} {e.question}{note}")

    if r.of("jargon"):
        out.append(_c("1", "\n  Swap these words"))
        seen = {}
        for f in r.of("jargon"):
            seen.setdefault(f.text.lower(), f.suggestion)
        for word, plain in list(seen.items())[:limit]:
            out.append(f"  {word:<26} → {_c('32', plain)}")
        if len(seen) > limit:
            out.append(_c("2", f"  … and {len(seen) - limit} more"))

    if r.of("long"):
        out.append(_c("1", "\n  Longest sentences"))
        for f in sorted(r.of("long"), key=lambda f: -len(f.text))[:3]:
            snippet = f.text if len(f.text) < 90 else f.text[:87] + "…"
            out.append(f"  {_c('2', f.message.split(' in ')[0])}  {snippet}")

    top = sorted(((v, k) for k, v in r.penalties.items() if v >= 0.5), reverse=True)
    if top:
        out.append(_c("1", "\n  Where the points went"))
        out.append("  " + " · ".join(f"{k} −{v:.0f}" for v, k in top))
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------

def to_json(reports: list[Report]) -> str:
    data = [r.to_dict() for r in reports]
    return json.dumps(data[0] if len(data) == 1 else data, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

def _highlight(r: Report) -> str:
    """Wrap long sentences, then jargon/passive spans inside them, without overlap."""
    text = r.text
    inline = [f for f in r.findings if f.kind != "long"]
    longs = r.of("long")
    # Drop inline spans that overlap an earlier one.
    clean, last = [], -1
    for f in sorted(inline, key=lambda f: f.start):
        if f.start >= last:
            clean.append(f)
            last = f.end

    events = []  # (pos, order, html)
    for f in longs:
        events.append((f.start, 0, f'<span class="long" title="{html.escape(f.message)}">'))
        events.append((f.end, 3, "</span>"))
    for f in clean:
        tip = html.escape(f"{f.message} Try: {f.suggestion}" if f.suggestion else f.message)
        events.append((f.start, 1, f'<mark class="{f.kind}" title="{tip}">'))
        events.append((f.end, 2, "</mark>"))
    events.sort(key=lambda e: (e[0], -e[1] if e[1] >= 2 else e[1]))

    out, pos = [], 0
    for at, _, tag in events:
        out.append(html.escape(text[pos:at]))
        out.append(tag)
        pos = at
    out.append(html.escape(text[pos:]))
    return "".join(out)


def to_html(r: Report) -> str:
    rd, e = r.readability, html.escape
    tone = "good" if r.score >= 80 else "warn" if r.score >= 60 else "bad"
    checklist = "".join(
        f'<li class="{"ok" if x.ok else "no"}"><b>{"✓" if x.ok else "✗"}</b>'
        f'<span>{e(x.question)}<small>{e(x.evidence if x.ok else x.advice)}</small></span></li>'
        for x in r.essentials
    )
    swaps, seen = [], set()
    for f in r.of("jargon"):
        if f.text.lower() not in seen:
            seen.add(f.text.lower())
            swaps.append(f"<tr><td>{e(f.text.lower())}</td><td>{e(f.suggestion)}</td></tr>")
    penalties = "".join(
        f"<tr><td>{e(k)}</td><td>−{v:.0f}</td></tr>" for k, v in r.penalties.items() if v >= 0.5
    ) or "<tr><td>No deductions</td><td></td></tr>"
    lens = rd.lengths or [0]
    peak = max(max(lens), 26)
    bars = "".join(
        f'<i style="height:{max(4, n / peak * 100):.0f}%" class="{"over" if n > 25 else ""}" title="{n} words"></i>'
        for n in lens
    )
    return _PAGE.format(
        title=e(r.source), score=r.score, letter=r.grade, tone=tone,
        level=f"{rd.grade:g}", target=f"{r.target_grade:g}", ease=f"{rd.ease:g}",
        words=rd.words, sents=rd.sentences, avg=f"{rd.avg_sentence:g}",
        nj=len(r.of("jargon")), np=len(r.of("passive")), nl=len(r.of("long")),
        checklist=checklist, swaps="".join(swaps) or "<tr><td>None found</td><td></td></tr>",
        penalties=penalties, bars=bars, body=_highlight(r),
        cap=(1 - 25 / peak) * 100,
    )


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>plainspeak · {title}</title>
<style>
:root{{--bg:#f7f6f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e6e4dd;
--good:#1f8a5b;--warn:#b7791f;--bad:#c2410c;--jargon:#fde68a;--passive:#bfdbfe;--long:#fecaca}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151517;--card:#1e1e21;--ink:#ececee;--mute:#9a9aa1;
--line:#2e2e33;--jargon:#6b5310;--passive:#1e3a5f;--long:#5b1f1f}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}}
.wrap{{max-width:1120px;margin:0 auto;padding:32px 16px;display:grid;gap:20px;grid-template-columns:320px 1fr}}
@media (max-width:820px){{.wrap{{grid-template-columns:1fr}}}}
header{{grid-column:1/-1;display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}}
h1{{font-size:20px;margin:0}}h1 span{{color:var(--mute);font-weight:400}}
h2{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:0 0 10px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}}
aside{{display:grid;gap:16px;align-content:start}}
.score{{display:flex;align-items:center;gap:16px}}
.ring{{--p:{score};width:92px;height:92px;border-radius:50%;display:grid;place-items:center;
background:conic-gradient(var(--{tone}) calc(var(--p)*1%),var(--line) 0)}}
.ring b{{width:74px;height:74px;border-radius:50%;background:var(--card);display:grid;place-items:center;font-size:26px}}
.score p{{margin:0;color:var(--mute)}}.score strong{{display:block;font-size:22px;color:var(--{tone})}}
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.stats div{{border:1px solid var(--line);border-radius:10px;padding:8px 10px}}
.stats b{{display:block;font-size:18px}}.stats small{{color:var(--mute)}}
ul{{list-style:none;margin:0;padding:0;display:grid;gap:10px}}
li{{display:flex;gap:10px}}li b{{width:22px;height:22px;flex:none;border-radius:50%;display:grid;place-items:center;font-size:12px;color:#fff}}
li.ok b{{background:var(--good)}}li.no b{{background:var(--bad)}}
li small{{display:block;color:var(--mute)}}
table{{width:100%;border-collapse:collapse;font-size:14px}}td{{padding:5px 0;border-bottom:1px solid var(--line)}}
td+td{{text-align:right;color:var(--good)}}
.hist{{display:flex;align-items:flex-end;gap:2px;height:60px;position:relative;margin-top:6px}}
.hist i{{flex:1;background:var(--mute);opacity:.45;border-radius:2px 2px 0 0}}.hist i.over{{background:var(--bad);opacity:.9}}
.hist::after{{content:"25 words";position:absolute;left:0;right:0;top:{cap:.0f}%;border-top:1px dashed var(--bad);font-size:10px;color:var(--bad);text-align:right}}
.doc{{white-space:pre-wrap;font:16px/1.75 ui-serif,Georgia,serif;overflow-wrap:anywhere}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;color:var(--mute);margin-bottom:12px}}
.legend span::before{{content:"";display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;background:var(--k)}}
mark{{color:inherit;border-radius:3px;padding:0 2px;cursor:help}}mark.jargon{{background:var(--jargon)}}
mark.passive{{background:var(--passive)}}.long{{background:linear-gradient(transparent 62%,var(--long) 0)}}
footer{{grid-column:1/-1;color:var(--mute);font-size:13px;text-align:center}}
</style></head><body><div class="wrap">
<header><h1>plainspeak <span>· {title}</span></h1><span style="color:var(--mute)">Hover a highlight to see the suggestion</span></header>
<aside>
<section class="card"><div class="score"><div class="ring"><b>{letter}</b></div>
<p><strong>{score}/100</strong>Grade {level} reading level<br>target ≤ {target}</p></div></section>
<section class="card stats">
<div><b>{words}</b><small>words</small></div><div><b>{avg}</b><small>words / sentence</small></div>
<div><b>{nj}</b><small>jargon terms</small></div><div><b>{np}</b><small>passive phrases</small></div>
<div><b>{nl}</b><small>long sentences</small></div><div><b>{ease}</b><small>reading ease</small></div></section>
<section class="card"><h2>Can the reader act on it?</h2><ul>{checklist}</ul></section>
<section class="card"><h2>Sentence lengths</h2><div class="hist">{bars}</div></section>
<section class="card"><h2>Swap these words</h2><table>{swaps}</table></section>
<section class="card"><h2>Where the points went</h2><table>{penalties}</table></section>
</aside>
<main class="card"><h2>The notice</h2>
<div class="legend"><span style="--k:var(--jargon)">jargon</span><span style="--k:var(--passive)">passive voice</span><span style="--k:var(--long)">long sentence</span></div>
<div class="doc">{body}</div></main>
<footer>Generated by plainspeak. Scores are a guide; test notices with real readers.</footer>
</div></body></html>
"""
