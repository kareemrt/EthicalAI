"""Render an Audit as a Markdown report, a JSON document, or a terminal summary."""

import json
from dataclasses import asdict
from datetime import date

from .audit import Audit


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def verdict(audit: Audit) -> str:
    sig = audit.adverse(significant_only=True)
    if sig:
        return "ADVERSE IMPACT (statistically significant)"
    if audit.adverse():
        return "POSSIBLE ADVERSE IMPACT (below threshold, not significant)"
    return "NO ADVERSE IMPACT DETECTED"


def to_markdown(audit: Audit) -> str:
    has_truth = any(g.tpr is not None for d in audit.dimensions for g in d.groups)
    what = ("selection rate" if audit.mode == "binary"
            else f"scoring rate (share scoring above {audit.cutoff:g})")

    out = [
        f"# Bias audit — `{audit.outcome}`",
        "",
        f"**Verdict: {verdict(audit)}**",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Records audited: {audit.total:,}",
        f"- Metric: {what}",
        f"- Adverse-impact threshold: impact ratio < {audit.threshold:g}; "
        f"significance level α = {audit.alpha:g}",
        "",
        "![Impact ratios](impact_ratios.svg)",
        "",
    ]

    for dim in audit.dimensions:
        out += [f"## {dim.name}", "", f"Reference group (highest rate): **{dim.reference}**", ""]
        head = "| Group | N | Share | Selected | Rate | Impact ratio | p-value | Status |"
        rule = "|---|---:|---:|---:|---:|---:|---:|---|"
        if has_truth:
            head += " TPR | FPR |"
            rule += "---:|---:|"
        out += [head, rule]
        for g in dim.groups:
            line = (f"| {g.group} | {g.n:,} | {_pct(g.share)} | {g.selected:,} | {_pct(g.rate)} | "
                    f"{g.impact_ratio:.3f} | {g.p_value:.3g} | {audit.status(g)} |")
            if has_truth:
                line += f" {_pct(g.tpr)} | {_pct(g.fpr)} |"
            out.append(line)
        gap = dim.tpr_gap()
        if gap is not None:
            out += ["", f"Equal-opportunity gap (max − min TPR among qualified candidates): **{gap:.1%}**"]
        out.append("")

    if audit.warnings:
        out += ["## Warnings", "", *[f"- {w}" for w in audit.warnings], ""]

    out += [
        "## How to read this",
        "",
        "- **Impact ratio** = group rate ÷ reference group rate. Below 0.8 fails the EEOC "
        "four-fifths rule of thumb and is the figure NYC Local Law 144 requires in published audits.",
        "- **p-value** tests whether the gap could be chance (two-proportion z-test vs. the reference group). "
        "`adverse*` = below threshold *and* significant.",
        "- **TPR / FPR** (only with ground truth): among truly qualified people, how often each group was "
        "selected — and among unqualified, how often they slipped through.",
        "",
        "> This report is a screening tool, not a legal determination. A low ratio is a signal to "
        "investigate features, data, and process — not proof of intent. Consult counsel for compliance.",
        "",
    ]
    return "\n".join(out)


def to_json(audit: Audit) -> str:
    data = asdict(audit)
    data["verdict"] = verdict(audit)
    for dim, raw in zip(audit.dimensions, data["dimensions"]):
        for g, rg in zip(dim.groups, raw["groups"]):
            rg["status"] = audit.status(g)
    return json.dumps(data, indent=2)


def to_terminal(audit: Audit) -> str:
    lines = [f"FairCheck · {audit.outcome} · {audit.total:,} records", ""]
    w = max(len(g.group) for d in audit.dimensions for g in d.groups)
    for dim in audit.dimensions:
        lines.append(dim.name)
        for g in dim.groups:
            bar = "█" * round(min(g.impact_ratio, 1) * 20)
            lines.append(f"  {g.group:<{w}} {bar:<20} {g.impact_ratio:5.2f}  {audit.status(g)}")
        lines.append("")
    lines.append(f"Verdict: {verdict(audit)}")
    return "\n".join(lines)
