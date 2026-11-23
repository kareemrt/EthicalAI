"""Renderers: terminal text, Markdown, JSON and a self-contained HTML page."""

from __future__ import annotations

import json
from dataclasses import asdict
from html import escape

from .audit import ADVERSE, EXCLUDED, OK, REFERENCE, WATCH, Audit, Dimension

GLYPH = {ADVERSE: "✖", WATCH: "▲", OK: "✔", REFERENCE: "★", EXCLUDED: "·"}
VERDICT = {
    ADVERSE: "Adverse impact detected",
    WATCH: "Possible adverse impact — gap below threshold but not statistically significant",
    OK: "No adverse impact detected",
    REFERENCE: "No adverse impact detected",
    EXCLUDED: "Not enough data",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _ratio(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def _p(x: float | None) -> str:
    return "—" if x is None else ("<0.001" if x < 0.001 else f"{x:.3f}")


def _rows(dim: Dimension):
    for g in dim.groups:
        yield (f"{GLYPH[g.status]} {g.status}", g.name, str(g.n), _pct(g.share),
               _pct(g.rate), _ratio(g.impact_ratio), _p(g.p_value),
               str(g.shortfall) if g.shortfall and g.status in (ADVERSE, WATCH) else "")


HEADERS = ("Status", "Group", "N", "Share", "Rate", "Impact ratio", "p-value", "Shortfall")


def _summary(a: Audit) -> str:
    basis = (f"selection rate on `{a.outcome}`" if a.mode == "selection"
             else f"scoring rate (share scoring above median {a.cutoff:g}) on `{a.outcome}`")
    return (f"{a.n:,} records · {basis} · threshold {a.threshold:g} · "
            f"α = {a.alpha:g} · groups under {a.min_share:.0%} of records excluded")


# ── Terminal ────────────────────────────────────────────────────────────────
def render_text(a: Audit) -> str:
    out = [f"FairHire audit — {VERDICT[a.status]}", _summary(a).replace("`", ""), ""]
    for dim in a.dimensions:
        rows = [HEADERS, *_rows(dim)]
        widths = [max(len(r[i]) for r in rows) for i in range(len(HEADERS))]
        line = lambda r: "  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip()
        out += [f"▌ {dim.name}", line(HEADERS), "  ".join("─" * w for w in widths)]
        out += [line(r) for r in rows[1:]] + [""]
    out.append(_legend(a).replace("**", ""))
    return "\n".join(out)


def _legend(a: Audit) -> str:
    return (f"Impact ratio = group rate ÷ highest group rate. Below {a.threshold:g} is flagged: "
            f"**adverse** if p < {a.alpha:g}, otherwise **watch**. Shortfall = additional "
            f"selections the group would need to reach the threshold.")


# ── Markdown ────────────────────────────────────────────────────────────────
def render_markdown(a: Audit) -> str:
    out = [f"# FairHire bias audit", "", f"**{GLYPH[a.status]} {VERDICT[a.status]}**", "",
           _summary(a), ""]
    for dim in a.dimensions:
        out += [f"## {dim.name}", "", "| " + " | ".join(HEADERS) + " |",
                "|" + "|".join(["---"] * 2 + ["---:"] * 6) + "|"]
        out += ["| " + " | ".join(r) + " |" for r in _rows(dim)] + [""]
    out += [f"> {_legend(a)}", ""]
    return "\n".join(out)


# ── JSON ────────────────────────────────────────────────────────────────────
def render_json(a: Audit) -> str:
    data = asdict(a) | {"status": a.status}
    for d, dim in zip(data["dimensions"], a.dimensions):
        d["status"] = dim.status
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── HTML ────────────────────────────────────────────────────────────────────
def svg_chart(dim: Dimension, threshold: float) -> str:
    """Horizontal bar chart of impact ratios with a threshold line."""
    groups = [g for g in dim.groups if g.impact_ratio is not None]
    if not groups:
        return ""
    label_w, bar_w, row_h, pad = 190, 360, 30, 24
    scale = 1.25  # fixed, so the threshold line sits in the same place on every chart
    x = lambda v: label_w + bar_w * min(v, scale) / scale
    h = pad + row_h * len(groups) + 8
    parts = [f'<svg class="chart" viewBox="0 0 {label_w + bar_w + 70} {h}" role="img" '
             f'aria-label="Impact ratios for {escape(dim.name)}">']
    for i, g in enumerate(groups):
        y = pad + i * row_h
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 18}" text-anchor="end" class="lbl">{escape(g.name)}</text>'
            f'<rect x="{label_w}" y="{y + 5}" width="{x(g.impact_ratio) - label_w:.1f}" height="18" '
            f'rx="3" class="bar {g.status}"><title>{escape(g.name)}: {g.impact_ratio:.2f}</title></rect>'
            f'<text x="{x(g.impact_ratio) + 6:.1f}" y="{y + 18}" class="val">{g.impact_ratio:.2f}</text>')
    tx = x(threshold)
    parts.append(f'<line x1="{tx:.1f}" x2="{tx:.1f}" y1="14" y2="{h - 4}" class="thr"/>'
                 f'<text x="{tx:.1f}" y="10" text-anchor="middle" class="thr-lbl">{threshold:g}</text></svg>')
    return "".join(parts)


CSS = """
:root{--bg:#fafaf9;--card:#fff;--fg:#1c1917;--muted:#78716c;--line:#e7e5e4;
--ok:#4d7c0f;--ref:#0369a1;--watch:#b45309;--adverse:#b91c1c;--ex:#a8a29e}
@media (prefers-color-scheme:dark){:root{--bg:#0c0a09;--card:#1c1917;--fg:#f5f5f4;--muted:#a8a29e;
--line:#292524;--ok:#84cc16;--ref:#38bdf8;--watch:#f59e0b;--adverse:#f87171;--ex:#57534e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}
.muted{color:var(--muted);font-size:13px}
.verdict{display:inline-block;margin:16px 0 24px;padding:8px 14px;border-radius:8px;font-weight:600;
border:1px solid currentColor}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:0 0 18px}
.chart{width:100%;height:auto;margin-bottom:12px}
.lbl,.val{font-size:12px;fill:var(--fg)}.val{fill:var(--muted)}
.thr{stroke:var(--fg);stroke-dasharray:4 3;opacity:.6}.thr-lbl{font-size:11px;fill:var(--muted)}
.bar.ok{fill:var(--ok)}.bar.reference{fill:var(--ref)}.bar.watch{fill:var(--watch)}
.bar.adverse{fill:var(--adverse)}.bar.excluded{fill:var(--ex)}
.adverse{color:var(--adverse)}.watch{color:var(--watch)}.ok{color:var(--ok)}
.reference{color:var(--ref)}.excluded{color:var(--ex)}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;
font-variant-numeric:tabular-nums}th,td{padding:6px 8px;border-bottom:1px solid var(--line);
text-align:right;white-space:nowrap}th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
th{color:var(--muted);font-weight:500}
"""


def render_html(a: Audit) -> str:
    cards = []
    for dim in a.dimensions:
        rows = "".join(
            "<tr>" + "".join(
                f'<td class="{g.status}">{escape(c)}</td>' if i == 0 else f"<td>{escape(c)}</td>"
                for i, c in enumerate(r)) + "</tr>"
            for g, r in zip(dim.groups, _rows(dim)))
        head = "".join(f"<th>{h}</th>" for h in HEADERS)
        cards.append(
            f'<section class="card"><h2>{escape(dim.name)} '
            f'<span class="{dim.status}">{GLYPH[dim.status]}</span></h2>'
            f'{svg_chart(dim, a.threshold)}'
            f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></section>')
    legend = escape(_legend(a).replace("**", ""))
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>FairHire Audit</title><style>{CSS}</style></head><body><main>'
            f'<h1>FairHire bias audit</h1><div class="muted">{escape(_summary(a).replace("`", ""))}</div>'
            f'<div class="verdict {a.status}">{GLYPH[a.status]} {VERDICT[a.status]}</div>'
            f'{"".join(cards)}<p class="muted">{legend}</p></main></body></html>')
