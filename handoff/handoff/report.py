"""Render an Audit as terminal text, Markdown, JSON and SVG charts."""

import json
import os
from typing import Dict

from . import metrics as m
from .audit import Audit
from .svg import line_chart

SLOTS = ["--s1", "--s2", "--s3"]  # max three series per chart stays colour-blind safe


def pct(x: float) -> str:
    return "n/a" if x != x else f"{x * 100:.1f}%"


def charts(a: Audit, preds) -> Dict[str, str]:
    out = {
        "reliability.svg": line_chart(
            "Does confidence match reality?", "Model confidence", "Observed accuracy",
            [("Raw scores", "--s1", [(b.mean_conf, b.accuracy) for b in a.bins]),
             ("Recalibrated", "--s2", [(b.mean_conf, b.accuracy) for b in a.recal_bins])],
            diagonal=True),
    }
    step = max(1, len(a.curve) // 120)
    pts = a.curve[::step] + [a.curve[-1]]
    op = a.operating_point
    out["coverage.svg"] = line_chart(
        "How much can the AI decide alone?", "Share of cases automated", "Accuracy on automated cases",
        [("Accuracy", "--s1", [(p.coverage, p.accuracy) for p in pts]),
         ("95% lower bound", "--s2", [(p.coverage, p.lower) for p in pts])],
        hline=(a.target, f"Target {pct(a.target)}"), dots=False,
        y_min=max(0.0, min(0.5, (min(p.lower for p in pts) * 10 // 1) / 10)),
        marker=(op.coverage, op.accuracy, f"automate {pct(op.coverage)}") if op else None)

    if 1 < len(a.groups) <= len(SLOTS):
        series = []
        for g, var in zip(a.groups, SLOTS):
            bins = m.reliability_bins([p for p in preds if p.group == g.group], n_bins=5)
            series.append((g.group, var, [(b.mean_conf, b.accuracy) for b in bins]))
        out["groups.svg"] = line_chart("Is confidence equally honest for everyone?",
                                       "Model confidence", "Observed accuracy", series, diagonal=True)
    return out


def text(a: Audit) -> str:
    lines = [f"handoff audit  ·  {a.n} predictions  ·  target {pct(a.target)}",
             f"accuracy {pct(a.accuracy)}   mean confidence {pct(a.mean_conf)}   "
             f"ECE {pct(a.ece)}   MCE {pct(a.mce)}   Brier {a.brier:.3f}", ""]
    lines += a.findings
    if len(a.groups) > 1:
        lines += ["", f"{'group':<14}{'n':>7}{'acc':>9}{'conf':>9}{'ECE':>8}{'to human':>10}{'auto acc':>10}"]
        for g in a.groups:
            lines.append(f"{g.group[:13]:<14}{g.n:>7}{pct(g.accuracy):>9}{pct(g.mean_conf):>9}"
                         f"{pct(g.ece):>8}{pct(g.deferred):>10}{pct(g.auto_accuracy):>10}")
    lines += ["", "RESULT: " + ("PASS" if a.passed else "FAIL")]
    return "\n".join(lines)


def markdown(a: Audit, chart_names) -> str:
    md = ["# handoff audit report", "",
          f"**{a.n} predictions** · target accuracy for automated decisions **{pct(a.target)}** · "
          f"result **{'✅ PASS' if a.passed else '❌ FAIL'}**", "",
          "| Accuracy | Mean confidence | ECE | MCE | Brier |", "|---|---|---|---|---|",
          f"| {pct(a.accuracy)} | {pct(a.mean_conf)} | {pct(a.ece)} | {pct(a.mce)} | {a.brier:.3f} |",
          "", "## Findings", ""]
    md += [f"- `{f[:4]}` {f[6:]}" for f in a.findings]
    if len(a.groups) > 1:
        md += ["", "## By group", "",
               "| Group | n | Accuracy | Confidence | ECE | Sent to human | Automated accuracy |",
               "|---|---:|---:|---:|---:|---:|---:|"]
        md += [f"| {g.group} | {g.n} | {pct(g.accuracy)} | {pct(g.mean_conf)} | {pct(g.ece)} | "
               f"{pct(g.deferred)} | {pct(g.auto_accuracy)} |" for g in a.groups]
    md += ["", "## Charts", ""] + [f"![{n}]({n})" for n in chart_names]
    md += ["", "## Reliability table", "", "| Confidence bin | n | Mean confidence | Accuracy | Gap |",
           "|---|---:|---:|---:|---:|"]
    md += [f"| {b.lo:.1f}–{b.hi:.1f} | {b.count} | {pct(b.mean_conf)} | {pct(b.accuracy)} | "
           f"{(b.mean_conf - b.accuracy) * 100:+.1f} pts |" for b in a.bins]
    return "\n".join(md) + "\n"


def write(a: Audit, preds, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    files = charts(a, preds)
    files["report.md"] = markdown(a, [n for n in files if n.endswith(".svg")])
    files["summary.json"] = json.dumps(a.to_dict(), indent=2, default=str)
    for name, body in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(body)
