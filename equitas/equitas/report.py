"""Render an :class:`Audit` as terminal text, Markdown, JSON, or a self-contained HTML page."""
from __future__ import annotations

import json
from html import escape

from .metrics import ADVERSE, EXCLUDED, OK, REFERENCE, REVIEW, Attribute, Audit, Group

ICON = {ADVERSE: "✖ adverse", REVIEW: "▲ review", OK: "✔ ok", REFERENCE: "● reference", EXCLUDED: "· excluded"}
ANSI = {ADVERSE: "\033[31m", REVIEW: "\033[33m", OK: "\033[32m", REFERENCE: "\033[36m", EXCLUDED: "\033[90m"}
CAVEAT = ("Equitas is a statistical screen, not a legal determination. A flag means the gap is large "
          "and unlikely to be chance — investigate the job-relatedness of the criteria before drawing conclusions.")


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _num(x: float | None, digits: int = 2) -> str:
    return "—" if x is None else f"{x:.{digits}f}"


def _p(p: float | None) -> str:
    return "—" if p is None else "<0.001" if p < 0.001 else f"{p:.3f}"


def explain(attr: Attribute, g: Group, kind: str | None = None) -> str:
    """One plain-language sentence describing a flagged group."""
    ref = next(x for x in attr.groups if x.category == attr.reference)
    why = ("below the four-fifths threshold and unlikely to be chance" if g.status == ADVERSE
           else "statistically significant" if g.impact_ratio >= 0.8
           else "below the four-fifths threshold, but the sample is too small to rule out chance")
    note = {"hidden": " Hidden bias: not visible on any single attribute.",
            "compounded": " Compounded: far worse than any single attribute shows."}.get(kind, "")
    return (f"{g.category} ({attr.name}) selected at {_pct(g.rate)} vs {_pct(ref.rate)} for {ref.category} — "
            f"impact ratio {g.impact_ratio:.2f}, p {_p(g.p_value)}: {why}.{note}")


def headline(a: Audit) -> tuple[list[tuple[Attribute, Group]], int]:
    """Headline findings (adverse first) and how many intersectional flags merely inherit them."""
    top = a.headline(ADVERSE) + a.headline(REVIEW)
    return top, len(a.findings(ADVERSE)) + len(a.findings(REVIEW)) - len(top)


def _inherited_note(n: int) -> str:
    return f"{n} more intersectional group{'s' * (n != 1)} inherit{'s' * (n == 1)} the gaps above." if n else ""


# ── text ─────────────────────────────────────────────────────────────────────

def to_text(a: Audit, color: bool = False) -> str:
    c = (lambda s, t: f"{ANSI[s]}{t}\033[0m") if color else (lambda s, t: t)
    bold = (lambda t: f"\033[1m{t}\033[0m") if color else (lambda t: t)
    s = a.settings
    out = [bold(f"equitas · {a.n:,} decisions · {_pct(a.rate)} selected"),
           f"flag rule: impact ratio < {s['ratio']:.2f} and p < {s['alpha']}", ""]
    for attr in a.attributes:
        width = max(12, *(len(g.category) for g in attr.groups))
        out.append(bold(attr.name) + (f"   equal-opportunity gap {_pct(attr.tpr_gap)}" if attr.tpr_gap is not None else ""))
        out.append(f"  {'group':<{width}}  {'n':>6}  {'rate':>6}  {'impact':<17}  {'p':>6}  status")
        for g in attr.groups:
            ir = g.impact_ratio
            bar = "─" * 12 if ir is None else ("█" * round(min(ir, 1) * 12)).ljust(12, "░")
            out.append(f"  {g.category:<{width}}  {g.n:>6,}  {_pct(g.rate):>6}  {bar} {_num(ir):>4}  "
                       f"{_p(g.p_value):>6}  {c(g.status, ICON[g.status])}")
        out.append("")
    top, inherited = headline(a)
    out.append(bold(f"{len(a.findings(ADVERSE))} adverse · {len(a.findings(REVIEW))} to review"))
    out += [c(g.status, "  ✖ " if g.status == ADVERSE else "  ▲ ") + explain(at, g, a.kind(at, g)) for at, g in top]
    if inherited:
        out.append(c(EXCLUDED, "  " + _inherited_note(inherited)))
    return "\n".join(out)


# ── markdown ─────────────────────────────────────────────────────────────────

def to_markdown(a: Audit) -> str:
    s = a.settings
    out = ["# Bias audit report", "",
           f"**{a.n:,}** decisions · **{_pct(a.rate)}** selected · "
           f"flag rule: impact ratio < {s['ratio']:.2f} and p < {s['alpha']}", ""]
    top, inherited = headline(a)
    out += ["## Findings", ""]
    out += [f"- {'✖ **Adverse**' if g.status == ADVERSE else '▲ Review'} — {explain(at, g, a.kind(at, g))}" for at, g in top]
    out += [f"- {_inherited_note(inherited)}"] if inherited else []
    if not top:
        out.append("- No groups flagged.")
    labels = s.get("has_labels")
    for attr in a.attributes:
        out += ["", f"## {attr.name}", ""]
        head = "| Group | n | Share | Selected | Rate (95% CI) | Impact ratio | p | Status |"
        out += [head + (" TPR | FPR |" if labels else ""), "|" + "---|" * (8 + 2 * bool(labels))]
        for g in attr.groups:
            row = (f"| {g.category} | {g.n:,} | {_pct(g.share)} | {g.selected:,} | {_pct(g.rate)} "
                   f"({_pct(g.ci[0])}–{_pct(g.ci[1])}) | {_num(g.impact_ratio)} | {_p(g.p_value)} | {ICON[g.status]} |")
            out.append(row + (f" {_pct(g.tpr)} | {_pct(g.fpr)} |" if labels else ""))
        if attr.tpr_gap is not None:
            out += ["", f"Equal-opportunity gap (max − min TPR): **{_pct(attr.tpr_gap)}**"]
    out += ["", f"> {CAVEAT}", ""]
    return "\n".join(out)


# ── json ─────────────────────────────────────────────────────────────────────

def to_json(a: Audit) -> str:
    return json.dumps(a.to_dict(), indent=2)


# ── svg / html ───────────────────────────────────────────────────────────────

SVG_STYLE = """
  .t{font:13px ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;fill:#1f2328}
  .m{fill:#656d76}.h{font-weight:600;font-size:14px}.track{fill:#eaeef2}
  .adverse{fill:#cf222e}.review{fill:#bf8700}.ok{fill:#1a7f37}.reference{fill:#0969da}.excluded{fill:#afb8c1}
  .rule{stroke:#cf222e;stroke-dasharray:4 3;stroke-width:1.5}
  @media (prefers-color-scheme:dark){
    .t{fill:#e6edf3}.m{fill:#8d96a0}.track{fill:#21262d}
    .adverse{fill:#f85149}.review{fill:#d29922}.ok{fill:#3fb950}.reference{fill:#4493f8}.excluded{fill:#484f58}
    .rule{stroke:#f85149}}
"""


def chart_svg(attrs: list[Attribute], ratio: float = 0.8, width: int = 720, headers: bool = True) -> str:
    """Horizontal impact-ratio bars with the four-fifths line drawn in."""
    longest = max(len(g.category) for at in attrs for g in at.groups if g.impact_ratio is not None)
    label_w, value_w, row_h, head_h = max(90, 7 * longest + 16), 120, 26, 34
    bar_w = width - label_w - value_w
    x0 = label_w
    rows, y = [], 8
    for attr in attrs:
        if headers:
            rows.append(f'<text class="t h" x="0" y="{y + 20}">{escape(attr.name)}</text>')
            y += head_h
        scored = [g for g in attr.groups if g.impact_ratio is not None]
        for g in scored:
            ir = g.impact_ratio
            w = bar_w * min(ir, 1)
            value = f"{ir:.2f} · {g.status}"
            rows.append(
                f'<text class="t" x="{label_w - 12}" y="{y + 15}" text-anchor="end">{escape(g.category)}</text>'
                f'<rect class="track" x="{x0}" y="{y + 3}" width="{bar_w}" height="16" rx="4"/>'
                f'<rect class="{g.status}" x="{x0}" y="{y + 3}" width="{w:.1f}" height="16" rx="4"/>'
                f'<text class="t m" x="{x0 + bar_w + 10}" y="{y + 15}">{value}</text>')
            y += row_h
        if skipped := len(attr.groups) - len(scored):
            rows.append(f'<text class="t m" x="{x0}" y="{y + 13}">'
                        f'+ {skipped} small or unknown group{"s" * (skipped != 1)} (not scored)</text>')
            y += row_h - 4
        y += 6
    rx = x0 + bar_w * ratio
    height = y + 22
    rows.append(f'<line class="rule" x1="{rx}" y1="4" x2="{rx}" y2="{y}"/>'
                f'<text class="t m" x="{rx}" y="{y + 16}" text-anchor="middle">four-fifths line ({ratio:.2f})</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'role="img" aria-label="Impact ratio by group"><style>{SVG_STYLE}</style>{"".join(rows)}</svg>')


HTML_STYLE = """
:root{--bg:#fff;--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--card:#f6f8fa;--bad:#cf222e;--warn:#bf8700;--good:#1a7f37}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8d96a0;--line:#30363d;--card:#161b22;--bad:#f85149;--warn:#d29922;--good:#3fb950}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:40px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:40px 0 12px}
.muted{color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.card b{display:block;font-size:24px}
.bad b{color:var(--bad)}.warn b{color:var(--warn)}ul.f{padding:0;list-style:none}ul.f li{padding:10px 14px;border-left:3px solid var(--warn);background:var(--card);border-radius:0 8px 8px 0;margin:8px 0}
ul.f li.adverse{border-color:var(--bad)}ul.f li.ok,ul.f li.note{border-color:var(--line);color:var(--muted)}svg{max-width:100%;height:auto}.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}td.adverse{color:var(--bad)}td.review{color:var(--warn)}td.ok{color:var(--good)}
footer{margin-top:48px;font-size:13px}
"""


def to_html(a: Audit, title: str = "Bias audit report") -> str:
    s = a.settings
    adverse, review = a.findings(ADVERSE), a.findings(REVIEW)
    top, inherited = headline(a)
    findings = "".join(f'<li class="{g.status}">{escape(explain(at, g, a.kind(at, g)))}</li>' for at, g in top) \
        or "<li class='ok'>No groups flagged.</li>"
    if inherited:
        findings += f'<li class="note">{_inherited_note(inherited)}</li>'
    labels = s.get("has_labels")
    sections = []
    for attr in a.attributes:
        rows = "".join(
            f"<tr><td>{escape(g.category)}</td><td>{g.n:,}</td><td>{_pct(g.rate)}</td>"
            f"<td>{_pct(g.ci[0])}–{_pct(g.ci[1])}</td><td>{_num(g.impact_ratio)}</td><td>{_p(g.p_value)}</td>"
            + (f"<td>{_pct(g.tpr)}</td><td>{_pct(g.fpr)}</td>" if labels else "")
            + f'<td class="{g.status}">{ICON[g.status]}</td></tr>' for g in attr.groups)
        gap = f'<p class="muted">Equal-opportunity gap: <b>{_pct(attr.tpr_gap)}</b></p>' if attr.tpr_gap is not None else ""
        sections.append(
            f"<h2>{escape(attr.name)}</h2>{chart_svg([attr], s['ratio'], headers=False)}<div class='scroll'><table><tr><th>Group</th><th>n</th>"
            f"<th>Rate</th><th>95% CI</th><th>Impact</th><th>p</th>{'<th>TPR</th><th>FPR</th>' if labels else ''}"
            f"<th>Status</th></tr>{rows}</table></div>{gap}")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{HTML_STYLE}</style></head>
<body><main><h1>{escape(title)}</h1>
<p class="muted">Flag rule: impact ratio &lt; {s['ratio']:.2f} and p &lt; {s['alpha']} · groups under {s['min_share']:.0%} of applicants are reported but not scored</p>
<div class="cards"><div class="card"><span class="muted">Decisions</span><b>{a.n:,}</b></div>
<div class="card"><span class="muted">Selected</span><b>{_pct(a.rate)}</b></div>
<div class="card bad"><span class="muted">Adverse</span><b>{len(adverse)}</b></div>
<div class="card warn"><span class="muted">To review</span><b>{len(review)}</b></div></div>
<h2>Findings</h2><ul class="f">{findings}</ul>{''.join(sections)}
<footer class="muted">{escape(CAVEAT)}<br>Generated by equitas.</footer></main></body></html>"""


RENDERERS = {"text": to_text, "md": to_markdown, "json": to_json, "html": to_html}
