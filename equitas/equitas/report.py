"""Render a Report as plain text, Markdown, JSON or a self-contained HTML page."""
from __future__ import annotations

import json
from datetime import date
from html import escape

from .metrics import EXCLUDED, FAIL, OK, WARN, AttributeAudit, Report

LABEL = {OK: "OK", WARN: "REVIEW", FAIL: "ADVERSE IMPACT", EXCLUDED: "EXCLUDED"}
ICON = {OK: "✓", WARN: "!", FAIL: "✗", EXCLUDED: "·"}
COLOR = {OK: "#12a37f", WARN: "#e0a100", FAIL: "#e5484d", EXCLUDED: "#9aa0a6"}
VERDICT = {
    OK: "No adverse impact detected at the configured thresholds.",
    WARN: "Some groups fall below the four-fifths threshold, but the gap is not statistically significant. Review before relying on this system.",
    FAIL: "Statistically significant adverse impact detected. This system disadvantages at least one group.",
}


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def num(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def pval(p: float | None) -> str:
    return "—" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")


def _rows(a: AttributeAudit, labels: bool) -> tuple[list[str], list[list[str]]]:
    head = ["Group", "n", "Share", "Selected", "Rate", "95% CI", "Impact ratio", "p"]
    if labels:
        head += ["TPR", "FPR"]
    head.append("Status")
    rows = []
    for g in a.groups:
        row = [g.name, str(g.n), pct(g.share), str(g.selected), pct(g.rate),
               f"{pct(g.ci[0])}–{pct(g.ci[1])}", num(g.impact_ratio), pval(g.p_value)]
        if labels:
            row += [pct(g.tpr), pct(g.fpr)]
        row.append(f"{ICON[g.status]} {LABEL[g.status]}")
        rows.append(row)
    return head, rows


def _gaps(a: AttributeAudit) -> str:
    parts = [f"parity gap {pct(a.parity_gap)}"]
    if a.tpr_gap is not None:
        parts.append(f"equal-opportunity gap {pct(a.tpr_gap)}")
    if a.fpr_gap is not None:
        parts.append(f"false-positive gap {pct(a.fpr_gap)}")
    return " · ".join(parts)


# ── text ─────────────────────────────────────────────────────────────────────

def to_text(r: Report) -> str:
    out = [
        f"Equitas bias audit — {r.source}",
        f"{r.n:,} decisions · favourable when {r.outcome} · overall rate {pct(r.rate)}",
        "",
    ]
    for a in r.audits:
        head, rows = _rows(a, r.has_labels)
        widths = [max(len(x) for x in col) for col in zip(head, *rows)]
        line = lambda cells: "  ".join(c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths)))
        out += [f"▌ {a.attribute}  (reference: {a.reference})", line(head), line(["─" * w for w in widths])]
        out += [line(row) for row in rows]
        out += [f"  {_gaps(a)}", ""]
    out.append(f"{ICON[r.status]} {LABEL[r.status]}: {VERDICT[r.status]}")
    return "\n".join(out)


# ── markdown ─────────────────────────────────────────────────────────────────

def to_markdown(r: Report) -> str:
    out = [
        f"# Bias audit: `{r.source}`", "",
        f"**{ICON[r.status]} {LABEL[r.status]}** — {VERDICT[r.status]}", "",
        f"- Decisions: **{r.n:,}**, favourable when `{r.outcome}`",
        f"- Overall selection rate: **{pct(r.rate)}**",
        f"- Thresholds: impact ratio < {r.config.ratio}, p < {r.config.alpha}, groups under {pct(r.config.min_share)} excluded",
        "",
    ]
    for a in r.audits:
        head, rows = _rows(a, r.has_labels)
        out += [f"## {a.attribute}", "", f"Reference group: **{a.reference}** · {_gaps(a)}", ""]
        out += ["| " + " | ".join(head) + " |", "|" + "|".join([":--"] + ["--:"] * (len(head) - 1)) + "|"]
        out += ["| " + " | ".join(row) + " |" for row in rows]
        out.append("")
    return "\n".join(out)


# ── json ─────────────────────────────────────────────────────────────────────

def to_json(r: Report) -> str:
    return json.dumps(r.to_dict(), indent=2, ensure_ascii=False)


# ── svg / html ───────────────────────────────────────────────────────────────

def svg_chart(a: AttributeAudit, cfg_ratio: float, width: int = 640) -> str:
    """Horizontal bar chart of selection rates with 95% CIs and the 4/5 line."""
    groups = a.groups
    ref_rate = next((g.rate for g in groups if g.name == a.reference), 0.0)
    row, top, left, right = 30, 26, 190, 70
    height = top + row * len(groups) + 10
    scale_max = min(1.0, max([g.ci[1] for g in groups] + [ref_rate, 0.05]) * 1.12)
    x = lambda v: left + (width - left - right) * v / scale_max
    ink = "#6b7280"

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
             f'font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="12" role="img" '
             f'aria-label="Selection rate by {escape(a.attribute)}">']
    t = x(ref_rate * cfg_ratio)
    parts.append(f'<line x1="{t:.1f}" y1="{top - 8}" x2="{t:.1f}" y2="{height - 6}" stroke="{COLOR[FAIL]}" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{t + 4:.1f}" y="{top - 12}" fill="{COLOR[FAIL]}">four-fifths line ({pct(ref_rate * cfg_ratio)})</text>')
    for i, g in enumerate(groups):
        y = top + i * row
        c = COLOR[g.status]
        name = g.name if len(g.name) <= 28 else g.name[:27] + "…"
        parts.append(f'<text x="{left - 10}" y="{y + 15}" text-anchor="end" fill="{ink}">{escape(name)}</text>')
        parts.append(f'<rect x="{left}" y="{y + 4}" width="{max(1.0, x(g.rate) - left):.1f}" height="16" rx="3" fill="{c}" fill-opacity="0.85"/>')
        lo, hi = x(g.ci[0]), x(g.ci[1])
        parts.append(f'<path d="M{lo:.1f} {y + 12}H{hi:.1f}M{lo:.1f} {y + 8}V{y + 16}M{hi:.1f} {y + 8}V{y + 16}" stroke="{ink}" stroke-width="1.2"/>')
        parts.append(f'<text x="{hi + 6:.1f}" y="{y + 16}" fill="{ink}">{pct(g.rate)}</text>')
    parts.append("</svg>")
    return "".join(parts)


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1f23;--muted:#6b7280;--line:#e6e6e3;--accent:#12a37f}
@media (prefers-color-scheme:dark){:root{--bg:#111315;--card:#1a1d20;--ink:#e8eaed;--muted:#9aa0a6;--line:#2b2f33}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:40px 16px 64px}
h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}h2{font-size:18px;margin:0 0 4px}
.muted{color:var(--muted)}.verdict{margin:24px 0;padding:16px 20px;border-radius:12px;border-left:5px solid var(--c);background:var(--card)}
.verdict b{color:var(--c)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:0 0 28px}
.card,section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 20px}
.card .v{font-size:24px;font-weight:650;letter-spacing:-.02em}section{margin:0 0 20px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums;margin-top:12px}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:550}.pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:600;color:#fff;background:var(--c)}
.head{display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap}footer{font-size:13px}footer li{margin:4px 0}
"""


def to_html(r: Report) -> str:
    c = r.config
    flagged = sum(1 for a in r.audits for g in a.groups if g.status in (WARN, FAIL))
    cards = [("Decisions", f"{r.n:,}"), ("Overall rate", pct(r.rate)),
             ("Attributes audited", str(len(r.audits))), ("Groups flagged", str(flagged))]
    html = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>Bias audit · {escape(r.source)}</title><style>{CSS}</style></head><body><main>",
        f"<h1>Bias audit</h1><div class='muted'>{escape(r.source)} · favourable when <code>{escape(r.outcome)}</code> · {date.today():%d %b %Y}</div>",
        f"<div class='verdict' style='--c:{COLOR[r.status]}'><b>{ICON[r.status]} {LABEL[r.status]}</b> — {VERDICT[r.status]}</div>",
        "<div class='cards'>" + "".join(f"<div class='card'><div class='muted'>{k}</div><div class='v'>{v}</div></div>" for k, v in cards) + "</div>",
    ]
    for a in r.audits:
        head, rows = _rows(a, r.has_labels)
        html.append(f"<section><div class='head'><h2>{escape(a.attribute)}</h2>"
                    f"<span class='pill' style='--c:{COLOR[a.status]}'>{LABEL[a.status]}</span></div>")
        html.append(f"<div class='muted'>Reference group: <b>{escape(str(a.reference))}</b> · {_gaps(a)}</div>")
        html.append(svg_chart(a, c.ratio))
        html.append("<div class='scroll'><table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>")
        for g, row in zip(a.groups, rows):
            cells = "".join(f"<td>{escape(v)}</td>" for v in row[:-1])
            html.append(f"<tr>{cells}<td><span class='pill' style='--c:{COLOR[g.status]}'>{LABEL[g.status]}</span></td></tr>")
        html.append("</table></div></section>")
    html.append(f"""<footer class='muted'><h2>How to read this</h2><ul>
<li><b>Impact ratio</b> = group selection rate ÷ the highest group's rate. Below <b>{c.ratio}</b> (the EEOC four-fifths rule, also used by NYC Local Law 144) indicates potential adverse impact.</li>
<li><b>ADVERSE IMPACT</b> means the ratio is below {c.ratio} <i>and</i> the gap is statistically significant (two-proportion z-test, p &lt; {c.alpha}). <b>REVIEW</b> means below {c.ratio} but not significant — often a small-sample signal worth investigating.</li>
<li>Groups under {pct(c.min_share)} of the data, and records with an unknown category, are shown but <b>excluded</b> from ratios.</li>
<li>When ground-truth labels are supplied, <b>TPR</b> (share of qualified people who were selected) and <b>FPR</b> (share of unqualified people selected) reveal whether errors fall unevenly across groups.</li>
<li>A passing audit is evidence, not proof, of fairness. Pair it with domain review, data provenance checks and the voices of affected people.</li>
</ul><p>Generated by Equitas.</p></footer></main></body></html>""")
    return "\n".join(html)


RENDERERS = {"text": to_text, "md": to_markdown, "json": to_json, "html": to_html}
