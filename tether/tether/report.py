"""Renderers: coloured terminal text, JSON, and a self-contained HTML page."""
import html
import json
import os
import sys

from .core import SUPPORTED, WEAK, UNSUPPORTED, SKIPPED

ICON = {SUPPORTED: "✔", WEAK: "~", UNSUPPORTED: "✘", SKIPPED: "·"}
ANSI = {SUPPORTED: "32", WEAK: "33", UNSUPPORTED: "31", SKIPPED: "90"}


def _bar(score, width=10):
    full = round(score * width)
    return "█" * full + "░" * (width - full)


def _clip(s, n=110):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def terminal(report, color=None, verbose=False):
    if color is None:
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    paint = (lambda code, s: f"\033[{code}m{s}\033[0m") if color else (lambda code, s: s)
    lines = []
    for i, c in enumerate(report.claims, 1):
        if c.verdict == SKIPPED and not verbose:
            continue
        head = f"{ICON[c.verdict]} {c.verdict.upper():<11}"
        score = "" if c.verdict == SKIPPED else f" {_bar(c.score)} {c.score:.2f}"
        lines.append(f"{paint(ANSI[c.verdict], head)}{paint('90', score)}  #{i} {_clip(c.text, 90)}")
        for f in c.flags:
            lines.append(f"    {paint(ANSI[c.verdict], '!')} {f}")
        if c.verdict in (WEAK, UNSUPPORTED) and c.missing:
            lines.append(paint("90", f"    not in evidence: {', '.join(c.missing[:8])}"))
        if c.evidence and (verbose or c.verdict != SUPPORTED):
            name = report.sources[c.evidence.source].name
            lines.append(paint("90", f"    ↳ [{c.evidence.source + 1}] {name}: “{_clip(c.evidence.text)}”"))
    g = report.groundedness
    tone = SUPPORTED if g >= 0.8 else WEAK if g >= 0.5 else UNSUPPORTED
    lines += ["", paint(ANSI[tone], f"Groundedness {g:.0%}") +
              f"  —  {report.count(SUPPORTED)} supported · {report.count(WEAK)} weak · "
              f"{report.count(UNSUPPORTED)} unsupported  ({len(report.checked)} claims checked "
              f"against {len(report.sources)} source{'s' * (len(report.sources) != 1)})"]
    return "\n".join(lines)


def to_json(report):
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


_CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mute:#6b6b66;--card:#fff;--line:#e6e3dc;
--ok:#1f7a4d;--okbg:#e3f4ea;--warn:#9a6400;--warnbg:#fdf1d8;--bad:#b42318;--badbg:#fde4e1}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#ecebe6;--mute:#9b9a94;--card:#1d1d1b;
--line:#2f2e2b;--ok:#5fd39a;--okbg:#173527;--warn:#f2bb55;--warnbg:#3a2c10;--bad:#ff8a7a;--badbg:#401814}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:40px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:36px 0 12px}
.sub{color:var(--mute);margin:0 0 24px}
.stats{display:flex;gap:12px;flex-wrap:wrap}.stat{flex:1 1 140px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat b{display:block;font-size:26px;line-height:1.2}.stat span{color:var(--mute);font-size:13px}
.meter{height:8px;border-radius:99px;background:var(--line);overflow:hidden;margin-top:16px;display:flex}
.meter i{display:block;height:100%}
.answer{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;white-space:pre-wrap}
.answer a{color:inherit;text-decoration:none;border-radius:4px;padding:1px 2px}
.supported{background:var(--okbg)}.weak{background:var(--warnbg)}.unsupported{background:var(--badbg)}
.answer a.unsupported{text-decoration:underline wavy var(--bad);text-underline-offset:4px}
.claim{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.claim.v-supported{border-left-color:var(--ok)}.claim.v-weak{border-left-color:var(--warn)}.claim.v-unsupported{border-left-color:var(--bad)}
.claim:target{outline:2px solid var(--fg)}
.tag{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em}
.v-supported .tag{color:var(--ok)}.v-weak .tag{color:var(--warn)}.v-unsupported .tag{color:var(--bad)}
.score{float:right;color:var(--mute);font-size:13px;font-variant-numeric:tabular-nums}
.flag{color:var(--bad);font-size:14px;margin:6px 0 0}.v-weak .flag{color:var(--warn)}
.ev{margin:10px 0 0;padding:8px 12px;border-left:2px solid var(--line);color:var(--mute);font-size:14px}
.miss{color:var(--mute);font-size:13px;margin:6px 0 0}
footer{color:var(--mute);font-size:13px;margin-top:40px}
"""


def to_html(report, title="tether report"):
    e = html.escape
    ok, wk, bad = (report.count(v) for v in (SUPPORTED, WEAK, UNSUPPORTED))
    n = max(len(report.checked), 1)
    # Rebuild the answer from claim spans so highlighting lines up exactly.
    parts, cursor, text = [], 0, report.answer
    for i, c in enumerate(report.claims, 1):
        parts.append(e(text[cursor:c.start]))
        body = e(text[c.start:c.end])
        parts.append(body if c.verdict == SKIPPED else
                     f'<a href="#c{i}" class="{c.verdict}" title="{c.verdict} · {c.score:.2f}">{body}</a>')
        cursor = c.end
    parts.append(e(text[cursor:]))
    cards = []
    for i, c in enumerate(report.claims, 1):
        if c.verdict == SKIPPED:
            continue
        flags = "".join(f'<p class="flag">⚠ {e(f)}</p>' for f in c.flags)
        miss = (f'<p class="miss">Not in evidence: {e(", ".join(c.missing[:10]))}</p>'
                if c.missing and c.verdict != SUPPORTED else "")
        ev = ""
        if c.evidence:
            name = report.sources[c.evidence.source].name
            ev = f'<blockquote class="ev">[{c.evidence.source + 1}] <b>{e(name)}</b> — {e(" ".join(c.evidence.text.split()))}</blockquote>'
        cards.append(f'<div class="claim v-{c.verdict}" id="c{i}"><span class="tag">{ICON[c.verdict]} {c.verdict}</span>'
                     f'<span class="score">#{i} · score {c.score:.2f}</span><div>{e(c.text)}</div>{flags}{miss}{ev}</div>')
    sources = "".join(f"<li>[{i}] {e(s.name)}</li>" for i, s in enumerate(report.sources, 1))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><style>{_CSS}</style></head>
<body><main><h1>{e(title)}</h1><p class="sub">Every sentence of the answer, checked against {len(report.sources)} source document(s).</p>
<div class="stats"><div class="stat"><b>{report.groundedness:.0%}</b><span>groundedness</span></div>
<div class="stat"><b style="color:var(--ok)">{ok}</b><span>supported</span></div>
<div class="stat"><b style="color:var(--warn)">{wk}</b><span>weak — review</span></div>
<div class="stat"><b style="color:var(--bad)">{bad}</b><span>unsupported</span></div></div>
<div class="meter"><i style="width:{ok / n:.1%};background:var(--ok)"></i><i style="width:{wk / n:.1%};background:var(--warn)"></i><i style="width:{bad / n:.1%};background:var(--bad)"></i></div>
<h2>Answer</h2><div class="answer">{"".join(parts)}</div>
<h2>Claims</h2>{"".join(cards)}
<h2>Sources</h2><ul>{sources}</ul>
<footer>Generated by tether — a lexical evidence check, not a fact-check. Weak claims need a human look.</footer>
</main></body></html>"""
