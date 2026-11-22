"""Renderers: the same audit as Markdown, JSON, or a self-contained HTML page."""

from __future__ import annotations

import html
import json
from dataclasses import asdict
from datetime import date

from .data import Dataset
from .metrics import FOUR_FIFTHS, GroupResult

Audit = list[tuple[str, int, list[GroupResult]]]  # (view name, unknown count, results)

DISCLAIMER = (
    "Impact ratios are a screening signal, not a verdict. A low ratio warrants investigation; "
    "a passing ratio does not prove a process is fair. This report is not legal advice."
)


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _ir(r: GroupResult) -> str:
    return "—" if r.impact_ratio is None else f"{r.impact_ratio:.3f}"


def _p(r: GroupResult) -> str:
    if r.p_value is None:
        return "ref" if r.impact_ratio == 1.0 else "—"
    return "<0.001" if r.p_value < 0.001 else f"{r.p_value:.3f}"


def _meta(ds: Dataset, source: str) -> list[tuple[str, str]]:
    rate = "Selection rate" if ds.mode == "selection" else f"Scoring rate (score > median {ds.threshold:g})"
    return [("Source", source), ("Date", date.today().isoformat()), ("Rows", f"{ds.rows:,}"), ("Metric", rate)]


def flagged(audit: Audit) -> list[tuple[str, GroupResult]]:
    return [(view, r) for view, _, results in audit for r in results if r.flagged]


def _verdict(audit: Audit) -> str:
    hits = flagged(audit)
    if not hits:
        return f"No category fell below the {FOUR_FIFTHS:g} impact-ratio threshold."
    names = ", ".join(f"{r.group} ({r.impact_ratio:.2f})" for _, r in hits)
    return f"{len(hits)} categor{'y' if len(hits) == 1 else 'ies'} below the {FOUR_FIFTHS:g} threshold: {names}."


# ── Markdown ────────────────────────────────────────────────────────────────

def to_markdown(audit: Audit, ds: Dataset, source: str) -> str:
    out = ["# Bias Audit Report", ""]
    out += [f"- **{k}:** {v}" for k, v in _meta(ds, source)]
    out += ["", f"> **{'⚠️' if flagged(audit) else '✅'} {_verdict(audit)}**", ""]
    for view, unknown, results in audit:
        out += [f"## {view}", "", "| Category | Applicants | Selected | Rate | Impact ratio | p-value | Status |",
                "|---|---:|---:|---:|---:|---:|---|"]
        for r in results:
            status = f"**{r.status}**" if r.flagged else r.status
            out.append(f"| {r.group} | {r.total:,} | {r.selected:,} | {_pct(r.rate)} | {_ir(r)} | {_p(r)} | {status} |")
        if unknown:
            out += ["", f"_{unknown:,} applicant(s) with unknown category were excluded from this view._"]
        out.append("")
    out += ["---", f"_{DISCLAIMER}_", ""]
    return "\n".join(out)


# ── JSON ────────────────────────────────────────────────────────────────────

def to_json(audit: Audit, ds: Dataset, source: str) -> str:
    return json.dumps(
        {
            "meta": dict(_meta(ds, source)),
            "threshold": FOUR_FIFTHS,
            "flagged": len(flagged(audit)),
            "views": [
                {"name": v, "unknown": u, "groups": [{**asdict(r), "status": r.status} for r in rs]}
                for v, u, rs in audit
            ],
        },
        indent=2,
    )


# ── HTML ────────────────────────────────────────────────────────────────────

def _bars(results: list[GroupResult]) -> str:
    """Horizontal impact-ratio bars with the four-fifths line, as inline SVG."""
    row_h, label_w, chart_w = 30, 300, 400
    h = row_h * len(results) + 28
    x = lambda v: label_w + min(v, 1.0) * chart_w  # noqa: E731
    parts = [f'<svg viewBox="0 0 {label_w + chart_w + 70} {h}" role="img" aria-label="Impact ratio by category">']
    for i, r in enumerate(results):
        y = i * row_h + 6
        cls = "na" if r.impact_ratio is None else ("bad" if r.flagged else "ok")
        val = r.impact_ratio or 0
        name = r.group if len(r.group) <= 42 else r.group[:40] + "…"
        parts.append(f'<text x="{label_w - 10}" y="{y + 15}" class="lbl"><title>{html.escape(r.group)}</title>{html.escape(name)}</text>')
        parts.append(f'<rect x="{label_w}" y="{y + 2}" width="{chart_w}" height="18" rx="4" class="track"/>')
        parts.append(f'<rect x="{label_w}" y="{y + 2}" width="{x(val) - label_w:.1f}" height="18" rx="4" class="{cls}"/>')
        parts.append(f'<text x="{x(1.0) + 8}" y="{y + 15}" class="val">{_ir(r)}</text>')
    lx = x(FOUR_FIFTHS)
    parts.append(f'<line x1="{lx}" x2="{lx}" y1="0" y2="{h - 22}" class="rule"/>')
    parts.append(f'<text x="{lx}" y="{h - 6}" class="rule-lbl">4/5 rule ({FOUR_FIFTHS:g})</text>')
    parts.append("</svg>")
    return "\n".join(parts)


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1e;--mute:#6b6b70;--line:#e4e4e0;--ok:#2f7d5b;--bad:#c4452f;--na:#a9a9a3;--track:#efefeb}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d20;--ink:#ececee;--mute:#9a9aa0;--line:#2e2e33;--ok:#4fae84;--bad:#e8694f;--na:#5d5d62;--track:#29292d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:940px;margin:0 auto;padding:40px 16px 64px}h1{font-size:28px;margin:0 0 4px}h2{font-size:18px;margin:0 0 14px}
.meta{display:flex;flex-wrap:wrap;gap:6px 22px;color:var(--mute);font-size:13px;margin-bottom:24px}.meta b{color:var(--ink);font-weight:600}
.verdict{padding:14px 18px;border-radius:10px;border-left:4px solid var(--ok);background:var(--card);margin-bottom:28px;font-weight:500}
.verdict.warn{border-color:var(--bad)}section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:20px}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{color:var(--mute);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.04em}th:first-child,td:first-child,th:last-child,td:last-child{text-align:left}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;background:var(--track);color:var(--mute)}.pill.bad{background:var(--bad);color:#fff}.pill.ok{color:var(--ok)}
svg{width:100%;height:auto;font-size:12px}.lbl{text-anchor:end;fill:var(--ink)}.val{fill:var(--mute)}.track{fill:var(--track)}.ok{fill:var(--ok)}.bad{fill:var(--bad)}.na{fill:var(--na)}
.rule{stroke:var(--ink);stroke-dasharray:4 3;stroke-width:1.2}.rule-lbl{text-anchor:middle;fill:var(--mute);font-size:11px}
.note{color:var(--mute);font-size:13px;margin:10px 0 0}footer{color:var(--mute);font-size:12.5px;margin-top:28px}
"""


def to_html(audit: Audit, ds: Dataset, source: str) -> str:
    e = html.escape
    warn = bool(flagged(audit))
    meta = "".join(f"<span>{e(k)}: <b>{e(v)}</b></span>" for k, v in _meta(ds, source))
    sections = []
    for view, unknown, results in audit:
        rows = "".join(
            f"<tr><td>{e(r.group)}</td><td>{r.total:,}</td><td>{r.selected:,}</td><td>{_pct(r.rate)}</td>"
            f"<td>{_ir(r)}</td><td>{_p(r)}</td>"
            f'<td><span class="pill {"bad" if r.flagged else "ok" if r.status == "ok" else ""}">{e(r.status)}</span></td></tr>'
            for r in results
        )
        note = f'<p class="note">{unknown:,} applicant(s) with unknown category excluded from this view.</p>' if unknown else ""
        sections.append(
            f"<section><h2>{e(view)}</h2>{_bars(results)}<div class='scroll'><table><thead><tr><th>Category</th>"
            f"<th>Applicants</th><th>Selected</th><th>Rate</th><th>Impact ratio</th><th>p-value</th><th>Status</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>{note}</section>"
        )
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Bias Audit Report</title><style>{CSS}</style></head><body><main>"
        f'<h1>Bias Audit Report</h1><div class="meta">{meta}</div>'
        f'<div class="verdict{" warn" if warn else ""}">{e(_verdict(audit))}</div>{"".join(sections)}'
        f"<footer>{e(DISCLAIMER)} Generated by FairHire.</footer></main></body></html>"
    )


RENDERERS = {"md": to_markdown, "json": to_json, "html": to_html}
