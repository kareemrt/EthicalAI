"""Render an Audit as terminal text, Markdown, JSON, or a self-contained HTML page."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from html import escape

from .charts import impact_chart
from .metrics import ALPHA, Audit, DimensionResult, GroupStat

pct = lambda v: "—" if v is None else f"{v:.1%}"    # noqa: E731
num = lambda v: "—" if v is None else f"{v:.2f}"    # noqa: E731


def _p(g: GroupStat) -> str:
    if g.p_value is None:
        return "—"
    return "<0.001" if g.p_value < 0.001 else f"{g.p_value:.3f}"


def _status(g: GroupStat, ref: str) -> str:
    if g.excluded:
        return "insufficient data"
    if g.name == ref:
        return "reference"
    if g.adverse:
        return "ADVERSE IMPACT" if g.significant else "below threshold (not significant)"
    return "ok"


def verdict(audit: Audit) -> list[str]:
    """Plain-English findings, most severe first."""
    lines = []
    for d in audit.dimensions:
        for g in d.flagged:
            sig = "statistically significant" if g.significant else "not statistically significant — collect more data"
            lines.append(
                f"{g.name} applicants ({d.name}) are selected at {g.impact_ratio:.0%} the rate of "
                f"{d.reference} applicants ({pct(g.rate)} vs {pct(g.rate / g.impact_ratio)}); {sig}."
            )
    excluded = sorted({f"{g.name} ({d.name})" for d in audit.dimensions for g in d.groups if g.excluded})
    if excluded:
        lines.append(
            f"{len(excluded)} group(s) were too small to assess and are NOT cleared: " + ", ".join(excluded) + "."
        )
    if audit.has_labels:
        for d in audit.dimensions:
            if d.tpr_gap is not None and d.tpr_gap > 0.1:
                lines.append(
                    f"Qualified applicants are missed unevenly across {d.name}: true-positive rates differ by "
                    f"{d.tpr_gap * 100:.0f} percentage points (equal-opportunity gap)."
                )
    return lines


# ── terminal ────────────────────────────────────────────────────────────────

def to_text(audit: Audit) -> str:
    out = [
        f"fairhire audit · {audit.n:,} applicants · overall selection rate {pct(audit.overall_rate)} "
        f"· threshold {audit.threshold:.2f}",
        "",
    ]
    for d in audit.dimensions:
        out.append(f"■ {d.name}")
        w = max(len(g.name) for g in d.groups)
        out.append(f"  {'group':<{w}}  {'n':>6}  {'rate':>6}  {'ratio':>5}  {'p':>6}  status")
        for g in d.groups:
            mark = "✗" if g.adverse else ("·" if g.excluded else "✓")
            out.append(
                f"{mark} {g.name:<{w}}  {g.n:>6,}  {pct(g.rate):>6}  {num(g.impact_ratio):>5}  {_p(g):>6}  "
                f"{_status(g, d.reference)}"
            )
        out.append("")
    out.append("RESULT: " + ("PASS — no group below threshold" if audit.passed else "FAIL — adverse impact found"))
    out += [f"  • {line}" for line in verdict(audit)]
    return "\n".join(out)


# ── markdown ────────────────────────────────────────────────────────────────

def _md_table(d: DimensionResult, labels: bool) -> str:
    head = "| Group | Applicants | Selected | Selection rate | Impact ratio | p-value |" + (" TPR | FPR |" if labels else "") + " Status |"
    sep = "|" + "---|" * (head.count("|") - 1)
    rows = [
        f"| {g.name} | {g.n:,} | {g.selected:,} | {pct(g.rate)} | {num(g.impact_ratio)} | {_p(g)} |"
        + (f" {pct(g.tpr)} | {pct(g.fpr)} |" if labels else "")
        + f" {_status(g, d.reference)} |"
        for g in d.groups
    ]
    return "\n".join([head, sep, *rows])


def to_markdown(audit: Audit) -> str:
    out = [
        f"# Bias audit — {date.today():%B %d, %Y}",
        "",
        f"**{audit.n:,} applicants** · overall selection rate **{pct(audit.overall_rate)}** · "
        f"impact-ratio threshold **{audit.threshold:.2f}** · result **{'PASS' if audit.passed else 'FAIL'}**",
        "",
        "## Findings",
        "",
        *([f"- {line}" for line in verdict(audit)] or ["- No group falls below the threshold."]),
    ]
    for d in audit.dimensions:
        out += ["", f"## {d.name}", "", _md_table(d, audit.has_labels)]
    out += ["", _METHOD_MD]
    return "\n".join(out)


_METHOD_MD = f"""## Method

- **Selection rate** — share of a group's applicants the tool advanced.
- **Impact ratio** — a group's selection rate divided by the highest group's rate. Below 0.80 is the EEOC
  "four-fifths rule" signal of adverse impact; NYC Local Law 144 requires these ratios to be published.
- **p-value** — two-proportion z-test against the reference group; below {ALPHA} means the gap is unlikely to be chance.
- **TPR / FPR** — when ground-truth qualification is known: the share of qualified (TPR) and unqualified (FPR)
  applicants who were advanced. Unequal TPR means qualified people in some groups are being missed.
- Groups under the minimum share of the data are reported but not scored. *Not scored is not the same as fair.*

This report is a statistical screen, not a legal determination."""


# ── JSON ────────────────────────────────────────────────────────────────────

def to_json(audit: Audit) -> str:
    data = asdict(audit)
    data["passed"] = audit.passed
    data["findings"] = verdict(audit)
    return json.dumps(data, indent=2)


# ── HTML ────────────────────────────────────────────────────────────────────

def to_html(audit: Audit) -> str:
    sections = []
    for d in audit.dimensions:
        rows = "".join(
            f"<tr class='{'bad' if g.adverse else ('na' if g.excluded else '')}'><td>{escape(g.name)}</td>"
            f"<td>{g.n:,}</td><td>{pct(g.rate)}</td><td>{num(g.impact_ratio)}</td><td>{_p(g)}</td>"
            + (f"<td>{pct(g.tpr)}</td><td>{pct(g.fpr)}</td>" if audit.has_labels else "")
            + f"<td>{_status(g, d.reference)}</td></tr>"
            for g in d.groups
        )
        extra = "<th>TPR</th><th>FPR</th>" if audit.has_labels else ""
        sections.append(
            f"<section><h2>{escape(d.name)}</h2>{impact_chart(d, audit.threshold)}"
            f"<div class='scroll'><table><thead><tr><th>Group</th><th>Applicants</th><th>Rate</th>"
            f"<th>Impact ratio</th><th>p</th>{extra}<th>Status</th></tr></thead><tbody>{rows}</tbody></table></div></section>"
        )
    findings = "".join(f"<li>{escape(l)}</li>" for l in verdict(audit)) or "<li>No group falls below the threshold.</li>"
    badge = "pass" if audit.passed else "fail"
    method = escape(_METHOD_MD.split("\n", 2)[2]).replace("\n- ", "</li><li>").replace("\n", " ")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bias Audit Report</title>
<style>
:root{{--bg:#fff;--fg:#1f2328;--mute:#59636e;--line:#d0d7de;--bad:#d1495b;--ok:#2f8f5b;--card:#f6f8fa}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1117;--fg:#e6edf3;--mute:#9198a1;--line:#3d444d;--card:#161b22}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;margin:0}}
main{{max-width:820px;margin:auto;padding:32px 16px 64px}}
h1{{margin:0 0 4px;font-size:26px}} h2{{margin:40px 0 12px;font-size:19px}}
.meta{{color:var(--mute)}} .badge{{display:inline-block;padding:2px 10px;border-radius:99px;color:#fff;font-weight:600;font-size:13px}}
.pass{{background:var(--ok)}} .fail{{background:var(--bad)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 20px;margin-top:20px}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;margin-top:12px;font-variant-numeric:tabular-nums}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}} th{{color:var(--mute);font-weight:500}}
tr.bad td{{color:var(--bad)}} tr.na td{{color:var(--mute)}} footer{{color:var(--mute);font-size:13px;margin-top:40px}}
</style></head><body><main>
<h1>Bias audit report</h1>
<div class="meta">{date.today():%B %d, %Y} · {audit.n:,} applicants · selection rate {pct(audit.overall_rate)} ·
threshold {audit.threshold:.2f} · <span class="badge {badge}">{badge.upper()}</span></div>
<div class="card"><h3>Findings</h3><ul>{findings}</ul></div>
{''.join(sections)}
<footer><h3>Method</h3><ul><li>{method.lstrip('- ')}</li></ul></footer>
</main></body></html>"""
