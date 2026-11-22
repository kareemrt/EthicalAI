"""Render audits as terminal text, Markdown or JSON."""
from __future__ import annotations

import json
import sys

from .metrics import Audit, GroupStats


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _p(x: float | None) -> str:
    return "ref" if x is None else ("<0.001" if x < 0.001 else f"{x:.3f}")


def verdict(audits: list[Audit]) -> str:
    flagged = [(a, g) for a in audits for g in a.flagged]
    if not flagged:
        return "PASS — no group falls below the impact-ratio threshold."
    sig = sum("significant" in g.flags for _, g in flagged)
    return (f"REVIEW — {len(flagged)} group(s) below threshold"
            f" ({sig} statistically significant at p<0.05).")


def _row(g: GroupStats, labels: bool) -> list[str]:
    lo, hi = g.ci
    cells = [g.name, str(g.n), str(g.selected), _pct(g.rate), f"{lo:.1%}–{hi:.1%}",
             "—" if g.impact_ratio is None else f"{g.impact_ratio:.2f}", _p(g.p_value)]
    if labels:
        cells += [_pct(g.tpr), _pct(g.fpr)]
    return cells + [", ".join(g.flags) or "ok"]


def _headers(labels: bool) -> list[str]:
    h = ["Group", "N", "Selected", "Rate", "95% CI", "Impact ratio", "p-value"]
    return h + (["TPR", "FPR"] if labels else []) + ["Flags"]


# ── terminal ────────────────────────────────────────────────────────────────
def to_text(audits: list[Audit], rows_seen: int, color: bool | None = None) -> str:
    color = sys.stdout.isatty() if color is None else color
    red, green, bold, dim, end = (("\033[31m", "\033[32m", "\033[1m", "\033[2m", "\033[0m")
                                  if color else ("",) * 5)
    out = [f"{bold}fairlens audit{end} {dim}· {rows_seen} rows{end}", ""]
    for a in audits:
        table = [_headers(a.has_labels)] + [_row(g, a.has_labels) for g in a.groups]
        widths = [max(len(r[i]) for r in table) for i in range(len(table[0]))]
        out.append(f"{bold}{a.attribute.replace('*', ' × ')}{end} {dim}(reference: {a.reference}){end}")
        for i, r in enumerate(table):
            line = "  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip()
            if i == 0:
                line = dim + line + end
            elif "adverse-impact" in r[-1]:
                line = red + line + end
            out.append("  " + line)
        if a.has_labels:
            out.append(f"  {dim}TPR gap {_pct(a.gap('tpr'))} · FPR gap {_pct(a.gap('fpr'))}{end}")
        out.append("")
    v = verdict(audits)
    out.append((green if v.startswith("PASS") else red) + bold + v + end)
    return "\n".join(out)


# ── markdown ────────────────────────────────────────────────────────────────
def to_markdown(audits: list[Audit], rows_seen: int, source: str, chart: str | None = None) -> str:
    md = [f"# Bias audit — `{source}`", "",
          f"> **{verdict(audits)}**", "",
          f"Rows analysed: **{rows_seen}** · Threshold: impact ratio **≥ {audits[0].threshold:g}** "
          "(EEOC four-fifths rule / NYC LL144 impact ratio)", ""]
    if chart:
        md += [f"![Impact ratio by group]({chart})", ""]
    for a in audits:
        md += [f"## {a.attribute.replace('*', ' × ')}", "",
               f"Reference group (highest selection rate): **{a.reference}**", ""]
        h = _headers(a.has_labels)
        md += ["| " + " | ".join(h) + " |", "|" + "|".join("---" for _ in h) + "|"]
        md += ["| " + " | ".join(_row(g, a.has_labels)) + " |" for g in a.groups]
        if a.has_labels:
            md += ["", f"Equal-opportunity (TPR) gap: **{_pct(a.gap('tpr'))}** · "
                       f"False-positive-rate gap: **{_pct(a.gap('fpr'))}**"]
        md.append("")
    md += ["## How to read this", "",
           "- **Impact ratio** — a group's selection rate divided by the most-selected group's rate. "
           "Below the threshold suggests adverse impact.",
           "- **p-value** — two-proportion z-test against the reference group. Small samples "
           "can show large gaps by chance; large samples can make tiny gaps significant.",
           "- **TPR / FPR** — among people the ground-truth label marks qualified (TPR) or not (FPR), "
           "the share selected. Gaps indicate unequal error rates.",
           "- Flags: `adverse-impact`, `significant` (p<0.05), `small-sample` (n<30), "
           "`under-2%` (LL144 allows excluding these from the ratio calculation).",
           "",
           "_A statistical screen, not a legal determination. Investigate causes before acting._", ""]
    return "\n".join(md)


# ── json ────────────────────────────────────────────────────────────────────
def to_json(audits: list[Audit], rows_seen: int) -> str:
    def group(g: GroupStats) -> dict:
        d = {"group": g.name, "n": g.n, "selected": g.selected, "rate": g.rate,
             "ci95": list(g.ci), "impact_ratio": g.impact_ratio, "p_value": g.p_value, "flags": g.flags}
        if g.tp + g.fp + g.fn + g.tn:
            d.update(tpr=g.tpr, fpr=g.fpr)
        return d
    return json.dumps({
        "rows": rows_seen, "verdict": verdict(audits),
        "attributes": [{"attribute": a.attribute, "reference": a.reference, "threshold": a.threshold,
                        "min_impact_ratio": a.min_ratio, "tpr_gap": a.gap("tpr"), "fpr_gap": a.gap("fpr"),
                        "groups": [group(g) for g in a.groups]} for a in audits],
    }, indent=2)
