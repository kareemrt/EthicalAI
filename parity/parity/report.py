"""Render an :class:`~parity.audit.Audit` as text, Markdown, JSON, SVG or a standalone HTML page."""

from __future__ import annotations

import html
import json

from .audit import ADVERSE, FOUR_FIFTHS, LOW_DATA, NOT_ASSESSED, OK, REVIEW, Audit, Dimension

ICON = {OK: "✓", REVIEW: "!", ADVERSE: "✗", LOW_DATA: "·", NOT_ASSESSED: "–"}
ANSI = {OK: "32", REVIEW: "33", ADVERSE: "31", LOW_DATA: "90", NOT_ASSESSED: "90"}
HEADLINE = {
    OK: "No adverse impact detected",
    REVIEW: "Disparities worth reviewing",
    ADVERSE: "Adverse impact detected",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _num(x: float | None, digits: int = 2) -> str:
    return "—" if x is None else f"{x:.{digits}f}"


def _p(x: float | None) -> str:
    return "—" if x is None else "<0.001" if x < 0.001 else f"{x:.3f}"


def _columns(audit: Audit) -> list[str]:
    cols = ["Group", "n", "Selected", "Rate", "95% CI", "Impact ratio", "p-value"]
    return cols + (["TPR", "FPR"] if audit.has_labels else []) + ["Verdict"]


def _cells(audit: Audit, g) -> list[str]:
    row = [g.name, str(g.n), str(g.selected), _pct(g.rate),
           f"{g.ci[0]:.0%}–{g.ci[1]:.0%}", _num(g.impact_ratio, 3), _p(g.p_value)]
    if audit.has_labels:
        row += [_pct(g.tpr), _pct(g.fpr)]
    return row + [f"{ICON[g.verdict]} {g.verdict}"]


def _summary(audit: Audit) -> str:
    basis = (f"score > {audit.cutoff:g} ({'median' if audit.mode == 'score' else 'cut-off'})"
             if audit.mode == "score" else "recorded decisions")
    return (f"{audit.total:,} records · {audit.selected:,} selected ({audit.rate:.1%}) · "
            f"outcome = {basis}")


# ── text ─────────────────────────────────────────────────────────────────────

def to_text(audit: Audit, color: bool = False) -> str:
    paint = (lambda s, v: f"\033[{ANSI[v]}m{s}\033[0m") if color else (lambda s, v: s)
    out = [paint(f"{ICON[audit.verdict]} {HEADLINE[audit.verdict]}", audit.verdict), _summary(audit)]
    cols = _columns(audit)
    for dim in audit.dimensions:
        rows = [_cells(audit, g) for g in dim.groups]
        widths = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
        line = lambda cells: "  ".join(  # noqa: E731 - tiny local formatter
            c.ljust(w) if i == 0 or i == len(cells) - 1 else c.rjust(w)
            for i, (c, w) in enumerate(zip(cells, widths))
        )
        out += ["", f"── {dim.name} (reference: {dim.reference or 'n/a'})", line(cols).rstrip()]
        out += [paint(line(r).rstrip(), g.verdict) for r, g in zip(rows, dim.groups)]
    out += ["", _legend()]
    return "\n".join(out)


def _legend() -> str:
    return (f"Impact ratio = group rate ÷ reference rate. ✗ adverse: < {FOUR_FIFTHS:.2f} and p < 0.05 · "
            "! review: gap worth a closer look · · low data: too few records to judge")


# ── markdown / json ──────────────────────────────────────────────────────────

def to_markdown(audit: Audit) -> str:
    cols = _columns(audit)
    out = [f"## {ICON[audit.verdict]} {HEADLINE[audit.verdict]}", "", _summary(audit)]
    for dim in audit.dimensions:
        out += ["", f"### {dim.name}", "", f"Reference group: **{dim.reference or 'n/a'}**", "",
                "| " + " | ".join(cols) + " |",
                "|" + "|".join(":---" if i == 0 else "---:" for i in range(len(cols))) + "|"]
        out += ["| " + " | ".join(_cells(audit, g)) + " |" for g in dim.groups]
    out += ["", f"_{_legend()}_"]
    return "\n".join(out)


def to_json(audit: Audit) -> str:
    return json.dumps(audit.to_dict(), indent=2)


# ── svg ──────────────────────────────────────────────────────────────────────

def to_svg(dim: Dimension, width: int = 640, title: bool = True) -> str:
    """Horizontal bar chart of impact ratios with the four-fifths line marked."""
    groups = [g for g in dim.groups if g.impact_ratio is not None]
    bar, gap, label_w, top = 22, 10, 170, 36 if title else 12
    plot_w = width - label_w - 60
    height = top + len(groups) * (bar + gap) + 30
    scale = min(1.3, max([1.05] + [g.impact_ratio for g in groups]))
    x = lambda v: label_w + min(v, scale) / scale * plot_w  # noqa: E731
    fill = {OK: "var(--ok)", REVIEW: "var(--review)", ADVERSE: "var(--adverse)",
            LOW_DATA: "var(--muted)", NOT_ASSESSED: "var(--muted)"}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="13" role="img" '
        f'aria-label="Impact ratios by {html.escape(dim.name)}">',
        "<style>svg{--ink:#1f2328;--muted:#8c959f;--ok:#2da44e;--review:#d4a72c;--adverse:#cf222e}"
        "@media (prefers-color-scheme:dark){svg{--ink:#e6edf3;--muted:#6e7681}}"
        "text{fill:var(--ink)}</style>",
    ]
    if title:
        parts.append(f'<text x="0" y="18" font-weight="600" font-size="15">'
                     f'Impact ratio · {html.escape(dim.name)}</text>')
    for i, g in enumerate(groups):
        y = top + i * (bar + gap)
        parts.append(f'<text x="{label_w - 10}" y="{y + bar * 0.7:.0f}" text-anchor="end">{html.escape(g.name)}</text>')
        parts.append(f'<rect x="{label_w}" y="{y}" width="{x(g.impact_ratio) - label_w:.1f}" height="{bar}" '
                     f'rx="4" fill="{fill[g.verdict]}"/>')
        parts.append(f'<text x="{width - 4}" y="{y + bar * 0.7:.0f}" text-anchor="end" '
                     f'font-variant-numeric="tabular-nums">{g.impact_ratio:.3f}</text>')
    y_end = top + len(groups) * (bar + gap) - gap
    for v, label in ((FOUR_FIFTHS, "0.80 rule"), (1.0, "parity")):
        parts.append(f'<line x1="{x(v):.1f}" y1="{top - 6}" x2="{x(v):.1f}" y2="{y_end + 6}" '
                     f'stroke="var(--ink)" stroke-dasharray="{"4 3" if v < 1 else "1 3"}" stroke-width="1.2"/>')
        parts.append(f'<text x="{x(v):.1f}" y="{y_end + 22}" text-anchor="middle" font-size="11">{label}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── html ─────────────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#fff;--ink:#1f2328;--muted:#656d76;--line:#d0d7de;--card:#f6f8fa;
--ok:#2da44e;--review:#d4a72c;--adverse:#cf222e}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--ink:#e6edf3;--muted:#8d96a0;
--line:#30363d;--card:#161b22}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 ui-sans-serif,system-ui,-apple-system,sans-serif}
main{max-width:960px;margin:0 auto;padding:32px 16px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:40px 0 4px}
.muted{color:var(--muted)}.banner{padding:16px 20px;border-radius:10px;margin:20px 0;
border-left:6px solid var(--c);background:var(--card);font-weight:600}
.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:500}
.v{font-weight:600}.ok{color:var(--ok)}.review{color:var(--review)}.adverse{color:var(--adverse)}
.low,.not{color:var(--muted)}main svg{width:100%;max-width:640px;height:auto;margin:12px 0 4px}
footer{margin-top:48px;font-size:13px}
"""

VERDICT_CLASS = {OK: "ok", REVIEW: "review", ADVERSE: "adverse", LOW_DATA: "low", NOT_ASSESSED: "not"}


def to_html(audit: Audit, title: str = "Bias audit") -> str:
    e = html.escape
    cols = _columns(audit)
    body = [f"<h1>{e(title)}</h1><p class='muted'>{e(_summary(audit))}</p>",
            f"<div class='banner' style='--c:var(--{audit.verdict})'>"
            f"{ICON[audit.verdict]} {HEADLINE[audit.verdict]}</div>"]
    for dim in audit.dimensions:
        head = "".join(f"<th>{e(c)}</th>" for c in cols)
        rows = "".join(
            "<tr>" + "".join(f"<td>{e(c)}</td>" for c in _cells(audit, g)[:-1])
            + f"<td class='v {VERDICT_CLASS[g.verdict]}'>{e(_cells(audit, g)[-1])}</td></tr>"
            for g in dim.groups
        )
        body.append(f"<h2>{e(dim.name)}</h2><p class='muted'>Reference group: {e(dim.reference or 'n/a')}</p>"
                    f"{to_svg(dim, title=False)}<div class='table'><table><thead><tr>{head}</tr></thead>"
                    f"<tbody>{rows}</tbody></table></div>")
    body.append(f"<footer class='muted'>{e(_legend())} Generated by Parity. "
                "This report is a statistical screen, not a legal determination.</footer>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(title)}</title><style>{CSS}</style></head><body><main>{''.join(body)}</main></body></html>")


RENDERERS = {"text": to_text, "md": to_markdown, "json": to_json, "html": to_html}
