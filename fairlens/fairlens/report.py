"""Render audits as a terminal table, Markdown, JSON or a standalone SVG chart."""
from __future__ import annotations

import json
from html import escape
from typing import Optional

from .metrics import EXCLUDED, FAIL, OK, WARN, Audit

ICON = {OK: "✅ OK", WARN: "⚠️ WARN", FAIL: "❌ FAIL", EXCLUDED: "➖ EXCLUDED"}
COLOR = {OK: "#2a9d8f", WARN: "#e9a23b", FAIL: "#d1495b", EXCLUDED: "#9aa0a6"}


def pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.1%}"


def pval(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _rows(a: Audit) -> list[list[str]]:
    rows = []
    for g in a.groups:
        ref = g.name == a.reference
        row = [g.name, str(g.n), pct(g.share), pct(g.rate),
               f"{g.impact_ratio:.2f}" if g.status != EXCLUDED else "—",
               "ref" if ref else pval(g.p_value) if g.status != EXCLUDED else "—"]
        if a.has_labels:
            row += [pct(g.tpr), pct(g.fpr)]
        rows.append(row + [g.status])
    return rows


def _header(a: Audit) -> list[str]:
    return (["group", "n", "share", "sel. rate", "impact", "p-value"]
            + (["TPR", "FPR"] if a.has_labels else []) + ["status"])


def verdict(a: Audit) -> str:
    if a.failed:
        return (f"{len(a.failed)} group(s) fall below the {a.threshold:.2f} impact-ratio "
                f"threshold with a statistically significant gap (p < {a.alpha}).")
    if a.warned:
        return (f"{len(a.warned)} group(s) fall below {a.threshold:.2f}, but the samples are "
                "too small to rule out chance. Collect more data before concluding.")
    return f"Every group's selection rate is at least {a.threshold:.0%} of the highest group's."


def _gaps(a: Audit) -> list[str]:
    out = []
    for metric, name in (("tpr", "Equal-opportunity gap (TPR)"), ("fpr", "False-positive gap (FPR)")):
        if (gap := a.gap(metric)) is not None:
            out.append(f"{name}: {gap * 100:.1f} pts")
    return out


# ── terminal ────────────────────────────────────────────────────────────────

def text(audits: list[Audit]) -> str:
    out = []
    for a in audits:
        header, rows = _header(a), _rows(a)
        widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]
        line = lambda cells: "  ".join(  # noqa: E731
            c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths)))
        out += [f"\n■ {a.attribute}   reference group: {a.reference}",
                line(header), line(["─" * w for w in widths]), *map(line, rows),
                f"→ {a.status}: {verdict(a)}"]
        out += [f"  {g}" for g in _gaps(a)]
    return "\n".join(out) + "\n"


# ── markdown ────────────────────────────────────────────────────────────────

METHOD = """\
## Method

| Metric | Meaning |
|---|---|
| **Selection rate** | Share of the group that received the positive decision. |
| **Impact ratio** | Group's selection rate ÷ the highest group's rate. Below **{t:.2f}** is evidence of adverse impact under the EEOC *four-fifths rule* and is the figure NYC Local Law 144 bias audits must publish. |
| **p-value** | Two-proportion z-test against the reference group. Small values mean the gap is unlikely to be chance. |
| **TPR / FPR** | Among people who truly qualified (TPR) or did not (FPR), the share selected. Large gaps mean the model's *mistakes* fall unevenly (equalized odds). |

**Status** — `FAIL`: below threshold and significant (p < {alpha}). `WARN`: below threshold, sample too small to be sure. `EXCLUDED`: group is under the minimum share of data and is reported but not scored.

> A passing audit is not proof of fairness. It shows outcome parity on the data provided, for the
> attributes provided. Check data quality, proxies for protected traits, and the human process around
> the model too.
"""


def markdown(audits: list[Audit], source: str = "", chart: str = "") -> str:
    worst = FAIL if any(a.failed for a in audits) else WARN if any(a.warned for a in audits) else OK
    md = ["# FairLens bias audit", ""]
    if source:
        md += [f"Data: `{source}` · {sum(g.n for g in audits[0].groups):,} records", ""]
    md += [f"**Overall: {ICON[worst]}**", ""]
    md += ["| Attribute | Reference group | Status | Finding |", "|---|---|---|---|"]
    md += [f"| {a.attribute} | {a.reference} | {ICON[a.status]} | {verdict(a)} |" for a in audits]
    if chart:
        md += ["", f"![Impact ratios]({chart})"]
    for a in audits:
        header = _header(a)
        md += ["", f"## {a.attribute}", "",
               "| " + " | ".join(header) + " |",
               "|" + "|".join(["---"] + ["---:"] * (len(header) - 2) + [":---:"]) + "|"]
        md += ["| " + " | ".join(r[:-1] + [ICON[r[-1]]]) + " |" for r in _rows(a)]
        md += [""] + [f"- {g}" for g in _gaps(a)]
    md += ["", METHOD.format(t=audits[0].threshold, alpha=audits[0].alpha)]
    return "\n".join(md)


# ── json ────────────────────────────────────────────────────────────────────

def to_json(audits: list[Audit]) -> str:
    return json.dumps([{
        "attribute": a.attribute, "reference": a.reference, "status": a.status,
        "threshold": a.threshold, "alpha": a.alpha,
        "tpr_gap": a.gap("tpr"), "fpr_gap": a.gap("fpr"),
        "groups": [{
            "group": g.name, "n": g.n, "share": round(g.share, 4),
            "selection_rate": round(g.rate, 4), "impact_ratio": round(g.impact_ratio, 4),
            "p_value": g.p_value, "tpr": g.tpr, "fpr": g.fpr, "status": g.status,
        } for g in a.groups],
    } for a in audits], indent=2)


# ── svg ─────────────────────────────────────────────────────────────────────

def svg(audits: list[Audit], width: int = 720) -> str:
    """Horizontal bar chart of impact ratios with the threshold marked. No dependencies."""
    label_w, pad, bar_h, gap, head = 190, 24, 22, 8, 34
    plot_w = width - label_w - pad * 2 - 50
    x = lambda v: label_w + pad + min(v, 1.0) * plot_w  # noqa: E731

    parts, y = [], pad
    for a in audits:
        parts.append(f'<text class="h" x="{pad}" y="{y + 16}">{escape(a.attribute)}</text>')
        y += head
        top = y
        for g in a.groups:
            v = g.impact_ratio if g.status != EXCLUDED else 0
            parts += [
                f'<text class="l" x="{label_w + pad - 10}" y="{y + 15}" text-anchor="end">{escape(g.name)}</text>',
                f'<rect x="{x(0)}" y="{y}" width="{plot_w}" height="{bar_h}" rx="4" class="track"/>',
                f'<rect x="{x(0)}" y="{y}" width="{x(v) - x(0):.1f}" height="{bar_h}" rx="4" fill="{COLOR[g.status]}"/>',
                f'<text class="v" x="{x(v) + 6:.1f}" y="{y + 15}">'
                f'{"excluded" if g.status == EXCLUDED else f"{v:.2f}"}</text>',
            ]
            y += bar_h + gap
        t = x(a.threshold)
        parts.append(f'<line x1="{t:.1f}" x2="{t:.1f}" y1="{top - 6}" y2="{y - gap + 6}" class="thr"/>')
        parts.append(f'<text class="s" x="{t:.1f}" y="{top - 10}" text-anchor="middle">{a.threshold:.2f}</text>')
        y += pad

    legend = "".join(
        f'<rect x="{pad + i * 120}" y="{y}" width="12" height="12" rx="2" fill="{COLOR[s]}"/>'
        f'<text class="s" x="{pad + i * 120 + 18}" y="{y + 11}">{s}</text>'
        for i, s in enumerate((OK, WARN, FAIL, EXCLUDED)))
    height = y + 28
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="system-ui, -apple-system, Segoe UI, sans-serif">
<style>
  .h {{ font-size: 15px; font-weight: 600; fill: #1f2328 }}
  .l, .v {{ font-size: 13px; fill: #1f2328 }}
  .s {{ font-size: 11px; fill: #59636e }}
  .track {{ fill: #eef0f2 }}
  .thr {{ stroke: #1f2328; stroke-width: 1.5; stroke-dasharray: 4 3 }}
  @media (prefers-color-scheme: dark) {{
    .h, .l, .v {{ fill: #e6edf3 }} .s {{ fill: #9198a1 }}
    .track {{ fill: #262c36 }} .thr {{ stroke: #e6edf3 }}
  }}
</style>
{chr(10).join(parts)}
{legend}
</svg>
"""
