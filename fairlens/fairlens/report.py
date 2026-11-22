"""Render an Audit as plain-English findings, a terminal table, Markdown, JSON or HTML."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from html import escape

from .metrics import ALPHA, FOUR_FIFTHS, MIN_SHARE, Audit, AttributeAudit, GroupStat

ICON = {"pass": "✓", "warn": "!", "fail": "✗", "n/a": "–"}
VERDICT = {
    "pass": "No adverse impact detected",
    "warn": "Possible adverse impact — gaps below 4/5ths, not statistically significant",
    "fail": "Adverse impact detected",
    "n/a": "Not enough data to judge",
}


def pct(x: float | None, digits: int = 1) -> str:
    return "—" if x is None else f"{x * 100:.{digits}f}%"


def num(x: float | None, digits: int = 2) -> str:
    return "—" if x is None else f"{x:.{digits}f}"


def pval(p: float | None) -> str:
    return "—" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")


# ── plain-English findings ───────────────────────────────────────────────────

def findings(audit: Audit) -> list[str]:
    """One sentence per problem, written for a non-statistician."""
    verb = "selected" if audit.mode == "selection" else "scored above the median"
    out = []
    for attr in audit.attributes:
        ref_rate = next((g.rate for g in attr.groups if g.group == attr.reference), 0)
        for g in attr.groups:
            if g.status in ("fail", "warn"):
                sig = (f"statistically significant (p {pval(g.p_value)})" if g.status == "fail"
                       else f"not statistically significant (p {pval(g.p_value)}) — collect more data")
                out.append(f"[{attr.attribute}] {g.group} candidates are {verb} at "
                           f"{num(g.impact_ratio)}× the rate of {attr.reference} "
                           f"({pct(g.rate)} vs {pct(ref_rate)}); {sig}.")
        if attr.tpr_gap is not None and attr.tpr_gap >= 0.10:
            out.append(f"[{attr.attribute}] Among genuinely qualified people, selection rates "
                       f"differ by {pct(attr.tpr_gap)} between groups (equal-opportunity gap).")
        small = [g.group for g in attr.groups if g.excluded and g.group != "Unknown"]
        if small:
            out.append(f"[{attr.attribute}] Excluded for small size (<{MIN_SHARE:.0%} of data): "
                       f"{', '.join(small)}. Their outcomes are still shown but not judged.")
    return out


# ── terminal ─────────────────────────────────────────────────────────────────

def terminal(audit: Audit, color: bool = True) -> str:
    paint = {"pass": "32", "warn": "33", "fail": "31", "n/a": "90"}

    def c(text: str, status: str) -> str:
        return f"\033[{paint[status]}m{text}\033[0m" if color else text

    lines = [
        "",
        f"  FairLens bias audit · {audit.rows:,} decisions · overall "
        f"{'selection' if audit.mode == 'selection' else 'scoring'} rate {pct(audit.overall_rate)}",
        f"  Verdict: {c(ICON[audit.status] + ' ' + VERDICT[audit.status], audit.status)}",
    ]
    for attr in audit.attributes:
        width = max(12, *(len(g.group) for g in attr.groups))
        head = f"  {'Group':<{width}}  {'n':>6}  {'Rate':>7}  {'Impact':>6}  {'p':>6}"
        if audit.has_labels:
            head += f"  {'TPR':>6}  {'FPR':>6}"
        lines += ["", f"  ▌{attr.attribute.upper()}", head, "  " + "─" * (len(head) - 2)]
        for g in attr.groups:
            row = (f"  {g.group:<{width}}  {g.n:>6,}  {pct(g.rate):>7}  "
                   f"{num(g.impact_ratio):>6}  {pval(g.p_value):>6}")
            if audit.has_labels:
                row += f"  {pct(g.tpr, 0):>6}  {pct(g.fpr, 0):>6}"
            lines.append(row + "  " + c(ICON[g.status] + " " + g.status, g.status))
    notes = findings(audit)
    if notes:
        lines += ["", "  Findings"] + [f"  • {n}" for n in notes]
    lines.append("")
    return "\n".join(lines)


# ── markdown ─────────────────────────────────────────────────────────────────

def markdown(audit: Audit, title: str = "Bias audit") -> str:
    md = [f"# {title}", "",
          f"**Verdict:** {ICON[audit.status]} {VERDICT[audit.status]}  ",
          f"**Decisions analysed:** {audit.rows:,} · **Overall rate:** {pct(audit.overall_rate)}"
          f" · **Date:** {date.today().isoformat()}", ""]
    for attr in audit.attributes:
        cols = ["Group", "n", "Share", "Rate", "Impact ratio", "p-value"]
        if audit.has_labels:
            cols += ["TPR", "FPR"]
        md += [f"## {attr.attribute}", "", "| " + " | ".join(cols + ["Status"]) + " |",
               "|" + "---|" * (len(cols) + 1)]
        for g in attr.groups:
            cells = [g.group, f"{g.n:,}", pct(g.share), pct(g.rate),
                     num(g.impact_ratio), pval(g.p_value)]
            if audit.has_labels:
                cells += [pct(g.tpr), pct(g.fpr)]
            md.append("| " + " | ".join(cells + [f"{ICON[g.status]} {g.status}"]) + " |")
        md.append("")
    if notes := findings(audit):
        md += ["## Findings", ""] + [f"- {n}" for n in notes] + [""]
    md += [_METHOD_MD, ""]
    return "\n".join(md)


_METHOD_MD = (
    "## Method\n\n"
    f"- **Impact ratio** = group rate ÷ highest group rate. Below **{FOUR_FIFTHS}** fails the "
    "EEOC four-fifths rule and is how NYC Local Law 144 audits report results.\n"
    f"- **p-value**: two-proportion z-test against the highest group; **fail** requires p < {ALPHA}.\n"
    f"- Groups under {MIN_SHARE:.0%} of the data and unknown values are shown but not judged.\n"
    "- A passing audit is evidence, not proof, of fairness. Review job-relatedness and data quality too."
)


# ── json ─────────────────────────────────────────────────────────────────────

def to_json(audit: Audit) -> str:
    data = asdict(audit)
    data["status"] = audit.status
    for attr_obj, attr in zip(audit.attributes, data["attributes"]):
        attr["status"] = attr_obj.status
        attr["min_impact_ratio"] = attr_obj.min_ratio
        for g_obj, g in zip(attr_obj.groups, attr["groups"]):
            g["status"] = g_obj.status
    data["findings"] = findings(audit)
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── html (single self-contained file, no JS, no external assets) ─────────────

def _chart(attr: AttributeAudit) -> str:
    """Horizontal bar chart of impact ratios with the 0.8 threshold drawn in."""
    rows = [g for g in attr.groups if g.impact_ratio is not None]
    if not rows:
        return ""
    label_w, bar_w, row_h = 190, 360, 30
    h = row_h * len(rows) + 28
    x = lambda v: label_w + min(v, 1.2) / 1.2 * bar_w  # noqa: E731
    parts = [f'<svg viewBox="0 0 {label_w + bar_w + 60} {h}" role="img" '
             f'aria-label="Impact ratios for {escape(attr.attribute)}">']
    for i, g in enumerate(rows):
        y = i * row_h + 6
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 15}" text-anchor="end" class="lbl">{escape(g.group)}</text>'
            f'<rect x="{label_w}" y="{y}" width="{x(g.impact_ratio) - label_w:.1f}" height="20" rx="4" '
            f'class="bar {g.status.replace("/", "")}"/>'
            f'<text x="{x(g.impact_ratio) + 6:.1f}" y="{y + 15}" class="val">{num(g.impact_ratio)}</text>')
    for v, cls in ((FOUR_FIFTHS, "thr"), (1.0, "ref")):
        parts.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="0" y2="{h - 20}" class="{cls}"/>'
                     f'<text x="{x(v):.1f}" y="{h - 6}" text-anchor="middle" class="axis">{v:.1f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _table(attr: AttributeAudit, labels: bool) -> str:
    head = "<th>Group</th><th>n</th><th>Share</th><th>Rate (95% CI)</th><th>Impact</th><th>p</th>"
    head += "<th>TPR</th><th>FPR</th>" if labels else ""
    body = []
    for g in attr.groups:
        cells = (f"<td>{escape(g.group)}</td><td>{g.n:,}</td><td>{pct(g.share)}</td>"
                 f"<td>{pct(g.rate)} <span class=ci>({pct(g.ci[0], 0)}–{pct(g.ci[1], 0)})</span></td>"
                 f"<td>{num(g.impact_ratio)}</td><td>{pval(g.p_value)}</td>")
        if labels:
            cells += f"<td>{pct(g.tpr)}</td><td>{pct(g.fpr)}</td>"
        body.append(f"<tr>{cells}<td><span class='pill {g.status.replace('/', '')}'>"
                    f"{ICON[g.status]} {g.status}</span></td></tr>")
    return f"<table><thead><tr>{head}<th></th></tr></thead><tbody>{''.join(body)}</tbody></table>"


def html(audit: Audit, title: str = "Bias audit") -> str:
    sections = []
    for attr in audit.attributes:
        gaps = ""
        if attr.tpr_gap is not None:
            gaps = (f"<p class=meta>Equal-opportunity gap (TPR): <b>{pct(attr.tpr_gap)}</b> · "
                    f"False-positive gap (FPR): <b>{pct(attr.fpr_gap)}</b></p>")
        sections.append(
            f"<section><h2>{escape(attr.attribute)} <span class='pill {attr.status.replace('/', '')}'>"
            f"{ICON[attr.status]} {attr.status}</span></h2>"
            f"<p class=meta>Reference group: <b>{escape(attr.reference or '—')}</b> · "
            f"Lowest impact ratio: <b>{num(attr.min_ratio)}</b></p>{gaps}"
            f"{_chart(attr)}{_table(attr, audit.has_labels)}</section>")
    notes = "".join(f"<li>{escape(n)}</li>" for n in findings(audit))
    method = "".join(f"<li>{escape(line[2:]).replace('**', '')}</li>"
                     for line in _METHOD_MD.splitlines() if line.startswith("- "))
    mode = ("Selection rate" if audit.mode == "selection"
            else f"Scoring rate (score &gt; median {num(audit.threshold)})")
    return _HTML.format(
        title=escape(title), status=audit.status.replace("/", ""), icon=ICON[audit.status],
        verdict=VERDICT[audit.status], rows=f"{audit.rows:,}", rate=pct(audit.overall_rate),
        mode=mode, today=date.today().isoformat(), sections="".join(sections),
        findings=f"<section><h2>Findings</h2><ul>{notes}</ul></section>" if notes else "",
        method=method)


_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--mute:#6e6e73;--line:#e3e3e0;
--pass:#1f9d55;--warn:#d98e04;--fail:#d64545;--na:#9a9a9f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111113;--card:#1c1c1f;--ink:#f2f2f2;
--mute:#9a9aa0;--line:#2e2e33}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:880px;margin:0 auto;padding:40px 16px}}
header h1{{margin:0;font-size:28px;letter-spacing:-.02em}}
.meta{{color:var(--mute);margin:4px 0 12px}}
.verdict{{display:flex;gap:14px;align-items:center;padding:18px 20px;border-radius:14px;
background:var(--card);border:1px solid var(--line);margin:20px 0}}
.verdict .big{{font-size:30px;width:52px;height:52px;border-radius:50%;display:grid;
place-items:center;color:#fff}}
.verdict b{{font-size:18px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:20px;margin:16px 0;overflow-x:auto}}
h2{{margin:0 0 4px;font-size:18px;display:flex;gap:10px;align-items:center}}
table{{width:100%;border-collapse:collapse;margin-top:12px;font-variant-numeric:tabular-nums}}
th,td{{text-align:right;padding:7px 8px;border-bottom:1px solid var(--line);white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}th{{color:var(--mute);font-weight:500;font-size:13px}}
.ci{{color:var(--mute);font-size:12px}}
.pill{{font-size:12px;font-weight:600;padding:2px 9px;border-radius:99px;color:#fff}}
.pass{{background:var(--pass);fill:var(--pass)}}.warn{{background:var(--warn);fill:var(--warn)}}
.fail{{background:var(--fail);fill:var(--fail)}}.na{{background:var(--na);fill:var(--na)}}
svg{{width:100%;max-width:640px;display:block;margin:8px 0}}
svg text{{fill:var(--ink);font-size:12px}}svg .axis{{fill:var(--mute);font-size:11px}}
svg .thr{{stroke:var(--fail);stroke-dasharray:4 3;stroke-width:1.5}}
svg .ref{{stroke:var(--mute);stroke-width:1}}
li{{margin:6px 0}}footer{{color:var(--mute);font-size:13px;margin-top:24px}}
</style></head><body><main>
<header><h1>{title}</h1>
<p class=meta>{rows} decisions · {mode}: {rate} overall · generated {today} by FairLens</p></header>
<div class=verdict><div class="big {status}">{icon}</div><div><b>{verdict}</b>
<div class=meta>Dashed red line marks the 0.8 four-fifths threshold.</div></div></div>
{findings}{sections}
<section><h2>Method</h2><ul>{method}</ul></section>
<footer>FairLens is a screening tool. It does not constitute legal advice.</footer>
</main></body></html>"""
