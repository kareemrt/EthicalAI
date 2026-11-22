"""Render audits as terminal text, Markdown, JSON or a self-contained HTML page."""

import json
from dataclasses import asdict
from datetime import date
from html import escape

from .metrics import FAIL, WARN, Audit, GroupStats, Policy

ICON = {"pass": "✅", WARN: "⚠️", FAIL: "❌", "info": "ℹ️"}
LABEL = {"pass": "PASS", WARN: "REVIEW", FAIL: "FAIL"}


def _f(x: float | None, fmt: str = ".2f") -> str:
    return "—" if x is None else format(x, fmt)


def _group_status(a: Audit, g: GroupStats) -> str:
    levels = {f.level for f in a.findings if f.group == g.name}
    return FAIL if FAIL in levels else WARN if WARN in levels else "pass"


def overall(audits: list[Audit]) -> str:
    s = {a.status for a in audits}
    return FAIL if FAIL in s else WARN if WARN in s else "pass"


def _rows(a: Audit) -> tuple[list[str], list[list[str]]]:
    has_label = any(g.tpr is not None for g in a.groups)
    head = ["Group", "N", "Selected", "Rate", "95% CI", "Impact", "p"]
    if has_label:
        head += ["TPR", "FPR"]
    rows = []
    for g in a.groups:
        row = [
            g.name + (" (ref)" if g.name == a.reference else ""),
            str(g.n), str(g.selected), _f(g.rate, ".1%"),
            f"{g.ci[0]:.0%}–{g.ci[1]:.0%}", _f(g.impact_ratio),
            "—" if g.p_value is None else "<0.001" if g.p_value < 0.001 else f"{g.p_value:.3f}",
        ]
        if has_label:
            row += [_f(g.tpr, ".0%"), _f(g.fpr, ".0%")]
        rows.append(row)
    return head, rows


# ── text ──────────────────────────────────────────────────────────────

def to_text(audits: list[Audit], color: bool = False) -> str:
    paint = {FAIL: "\033[31m", WARN: "\033[33m", "pass": "\033[32m", "info": "\033[2m"}
    c = (lambda s, k: f"{paint[k]}{s}\033[0m") if color else (lambda s, k: s)
    out = []
    for a in audits:
        out.append(c(f"■ {a.attribute}  [{LABEL[a.status]}]", a.status))
        head, rows = _rows(a)
        widths = [max(len(r[i]) for r in [head, *rows]) for i in range(len(head))]
        line = lambda r: "  " + "  ".join(
            v.ljust(w) if i == 0 else v.rjust(w) for i, (v, w) in enumerate(zip(r, widths)))
        out.append(line(head))
        out.append("  " + "  ".join("─" * w for w in widths))
        out += [line(r) for r in rows]
        for f in a.findings:
            out.append(c(f"  {ICON[f.level]}  {f.message}", f.level))
        out.append("")
    v = overall(audits)
    out.append(c(f"Overall: {LABEL[v]}", v))
    return "\n".join(out)


# ── markdown ──────────────────────────────────────────────────────────

def to_markdown(audits: list[Audit], source: str = "", policy: Policy = Policy()) -> str:
    v = overall(audits)
    out = [
        f"# Parity bias audit {ICON[v]} {LABEL[v]}", "",
        f"Source: `{source}` · {date.today()} · four-fifths threshold "
        f"{policy.threshold:.2f} · α = {policy.alpha}", "",
    ]
    for a in audits:
        head, rows = _rows(a)
        out += [f"## {ICON[a.status]} {a.attribute}", "",
                "| " + " | ".join(head) + " |",
                "|" + "|".join("---" if i == 0 else "--:" for i in range(len(head))) + "|"]
        out += ["| " + " | ".join(r) + " |" for r in rows]
        out.append("")
        out += [f"- {ICON[f.level]} {f.message}" for f in a.findings]
        out.append("")
    return "\n".join(out)


# ── json ──────────────────────────────────────────────────────────────

def to_json(audits: list[Audit], policy: Policy = Policy()) -> str:
    return json.dumps({
        "status": overall(audits),
        "policy": asdict(policy),
        "audits": [{**asdict(a), "status": a.status} for a in audits],
    }, indent=2, ensure_ascii=False)


# ── svg / html ────────────────────────────────────────────────────────

def chart_svg(a: Audit, threshold: float = 0.8, width: int = 640) -> str:
    """Horizontal bar chart of selection rates with CI whiskers and the
    four-fifths line. Colours come from CSS variables so it themes."""
    bar_h, gap, left, right, top = 22, 10, 170, 56, 26
    plot = width - left - right
    h = top + len(a.groups) * (bar_h + gap) + 8
    ref_rate = next(g.rate for g in a.groups if g.name == a.reference)
    # Zoom the axis to the data (rounded up to a 20% step) so gaps stay visible.
    xmax = min(1.0, max(0.2, -(-max(g.ci[1] for g in a.groups) // 0.2) * 0.2))
    x = lambda v: left + v / xmax * plot
    line_x = x(threshold * ref_rate)

    parts = [
        f'<svg viewBox="0 0 {width} {h}" width="100%" role="img" '
        f'aria-label="Selection rate by {escape(a.attribute)}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui,sans-serif" font-size="12">',
    ]
    for t in (xmax * i / 4 for i in range(5)):
        parts.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 6}" y2="{h - 8}" '
                     f'stroke="var(--grid,#e5e7eb)"/>'
                     f'<text x="{x(t):.1f}" y="{top - 10}" text-anchor="middle" '
                     f'fill="var(--muted,#6b7280)">{t:.0%}</text>')
    for i, g in enumerate(a.groups):
        y = top + i * (bar_h + gap)
        st = _group_status(a, g)
        fill = {"pass": "var(--ok,#3b82f6)", WARN: "var(--warn,#f59e0b)",
                FAIL: "var(--bad,#ef4444)"}[st]
        cy = y + bar_h / 2
        parts.append(
            f'<text x="{left - 10}" y="{cy + 4:.1f}" text-anchor="end" '
            f'fill="var(--fg,#111827)">{escape(g.name[:26])}</text>'
            f'<rect x="{left}" y="{y}" width="{max(x(g.rate) - left, 1):.1f}" height="{bar_h}" '
            f'rx="3" fill="{fill}"><title>{escape(g.name)}: {g.rate:.1%} of {g.n}</title></rect>'
            f'<line x1="{x(g.ci[0]):.1f}" x2="{x(g.ci[1]):.1f}" y1="{cy}" y2="{cy}" '
            f'stroke="var(--fg,#111827)" stroke-width="1.5" opacity=".55"/>'
            f'<text x="{width - right + 8}" y="{cy + 4:.1f}" fill="var(--fg,#111827)" '
            f'font-weight="600">{g.rate:.0%}</text>'
        )
    parts.append(
        f'<line x1="{line_x:.1f}" x2="{line_x:.1f}" y1="{top - 6}" y2="{h - 8}" '
        f'stroke="var(--bad,#ef4444)" stroke-dasharray="4 3" stroke-width="1.5"/>'
        f'</svg>'
    )
    return "".join(parts)


CSS = """
:root{--bg:#f8fafc;--card:#fff;--fg:#0f172a;--muted:#64748b;--grid:#e2e8f0;
--ok:#3b82f6;--warn:#f59e0b;--bad:#ef4444;--good:#16a34a}
@media (prefers-color-scheme:dark){:root{--bg:#0b1120;--card:#111827;--fg:#e5e7eb;
--muted:#94a3b8;--grid:#1f2937;--ok:#60a5fa;--warn:#fbbf24;--bad:#f87171;--good:#4ade80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:0 0 12px;display:flex;gap:10px;align-items:center}
.meta{color:var(--muted);margin:0 0 24px;font-size:13px}
.card{background:var(--card);border:1px solid var(--grid);border-radius:12px;padding:20px;margin:0 0 20px}
.pill{font-size:12px;font-weight:700;padding:2px 10px;border-radius:99px;color:#fff;letter-spacing:.03em}
.pass{background:var(--good)}.warn{background:var(--warn)}.fail{background:var(--bad)}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;margin-top:12px}
th,td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--grid);white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600}
ul{padding-left:0;list-style:none;margin:14px 0 0}li{margin:6px 0}
.legend{font-size:12px;color:var(--muted);margin-top:4px}
.legend i{display:inline-block;width:14px;border-top:2px dashed var(--bad);vertical-align:middle;margin-right:4px}
footer{color:var(--muted);font-size:12px;margin-top:32px}
"""


def to_html(audits: list[Audit], source: str = "", policy: Policy = Policy()) -> str:
    v = overall(audits)
    cards = []
    for a in audits:
        head, rows = _rows(a)
        table = ("<table><thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in head)
                 + "</tr></thead><tbody>"
                 + "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in r) + "</tr>"
                           for r in rows)
                 + "</tbody></table>")
        findings = "".join(f"<li>{ICON[f.level]} {escape(f.message)}</li>" for f in a.findings) \
            or "<li>✅ No disparities above policy thresholds.</li>"
        cards.append(
            f'<section class="card"><h2>{escape(a.attribute)}'
            f'<span class="pill {a.status}">{LABEL[a.status]}</span></h2>'
            f'{chart_svg(a, policy.threshold)}'
            f'<div class="legend"><i></i>four-fifths line ({policy.threshold:.0%} of '
            f'{escape(a.reference)}\'s rate) · whiskers = 95% CI</div>'
            f'<div class="tbl">{table}</div><ul>{findings}</ul></section>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Parity bias audit</title><style>{CSS}</style></head><body><main>'
        f'<h1>Bias audit <span class="pill {v}">{LABEL[v]}</span></h1>'
        f'<p class="meta">{escape(source)} · {date.today()} · threshold '
        f'{policy.threshold:.2f} · α {policy.alpha} · min n {policy.min_n} · '
        f'max TPR/FPR gap {policy.max_gap:.0%}</p>'
        + "".join(cards) +
        '<footer>Generated by Parity. Statistical evidence of disparity is a prompt '
        'for human review, not a legal conclusion.</footer></main></body></html>'
    )
