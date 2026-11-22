"""Render audit results as Markdown, JSON, SVG charts and a terminal table."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from .metrics import FOUR_FIFTHS, GroupStat

BADGE = {"adverse-impact": "⚠️ adverse impact", "significant": "📉 significant",
         "small-sample": "· <2% sample", "opportunity-gap": "🎯 opportunity gap"}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------- SVG chart
def svg_chart(title: str, stats: list[GroupStat]) -> str:
    """Horizontal impact-ratio bars with the four-fifths threshold marked."""
    label_w, bar_w, row_h, top = 190, 360, 26, 44
    width, height = label_w + bar_w + 70, top + row_h * len(stats) + 30
    x = lambda ratio: label_w + bar_w * min(ratio, 1.0)
    rows = []
    for i, st in enumerate(stats):
        y = top + i * row_h
        cls = "bad" if "adverse-impact" in st.flags else "muted" if "small-sample" in st.flags else "ok"
        rows.append(
            f'<text x="{label_w - 10}" y="{y + 16}" class="lbl" text-anchor="end">{escape(st.group)}</text>'
            f'<rect x="{label_w}" y="{y + 4}" width="{x(st.impact_ratio) - label_w:.1f}" height="16" rx="3" class="{cls}"/>'
            f'<text x="{x(st.impact_ratio) + 6:.1f}" y="{y + 16}" class="val">{st.impact_ratio:.2f}</text>')
    tx = x(FOUR_FIFTHS)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="system-ui,-apple-system,Segoe UI,sans-serif">
<style>
 .t{{font-size:15px;font-weight:600;fill:#1f2328}} .lbl,.val,.ax{{font-size:12px;fill:#59636e}}
 .ok{{fill:#4c72b0}} .bad{{fill:#d1495b}} .muted{{fill:#b8bec6}} .th{{stroke:#d1495b;stroke-dasharray:4 3}}
 @media (prefers-color-scheme:dark){{.t{{fill:#e6edf3}} .lbl,.val,.ax{{fill:#9198a1}} .ok{{fill:#6f9ce0}} .muted{{fill:#545d68}}}}
</style>
<text x="12" y="24" class="t">{escape(title)} — impact ratio</text>
{''.join(rows)}
<line x1="{tx}" y1="{top - 4}" x2="{tx}" y2="{height - 22}" class="th"/>
<text x="{tx - 6}" y="{height - 8}" class="ax" text-anchor="end">four-fifths line 0.80</text>
<text x="{label_w + bar_w}" y="{height - 8}" class="ax" text-anchor="middle">1.00</text>
<text x="{label_w}" y="{height - 8}" class="ax" text-anchor="middle">0</text>
</svg>
"""


# ---------------------------------------------------------------- Markdown
def _table(stats: list[GroupStat], has_tpr: bool) -> str:
    head = "| Category | N | Selected | Selection rate | Impact ratio | p-value |" + (" TPR |" if has_tpr else "") + " Flags |"
    sep = "|---|--:|--:|--:|--:|--:|" + ("--:|" if has_tpr else "") + "---|"
    lines = [head, sep]
    for st in stats:
        tpr = f" {st.tpr:.1%} |" if has_tpr and st.tpr is not None else (" — |" if has_tpr else "")
        flags = ", ".join(BADGE[f] for f in st.flags) or "✅"
        lines.append(f"| {st.group} | {st.n:,} | {st.selected:,} | {st.rate:.1%} | "
                     f"**{st.impact_ratio:.2f}** | {st.p_value:.3g} |{tpr} {flags} |")
    return "\n".join(lines)


def markdown(source: str, outcome: str, results: dict[str, list[GroupStat]], note: str = "") -> str:
    flagged = [(dim, st) for dim, stats in results.items() for st in stats if "adverse-impact" in st.flags]
    verdict = (f"**{len(flagged)} categor{'y' if len(flagged) == 1 else 'ies'} fall below the four-fifths "
               f"threshold.**" if flagged else "**No category falls below the four-fifths threshold.**")
    out = [f"# Bias audit — `{source}`", "",
           f"Outcome audited: **{outcome}**. {note}".rstrip(), "", "## Summary", "", verdict, ""]
    out += [f"- {dim}: **{st.group}** — impact ratio {st.impact_ratio:.2f} (p = {st.p_value:.3g})"
            for dim, st in flagged]
    for dim, stats in results.items():
        has_tpr = any(st.tpr is not None for st in stats)
        out += ["", f"## {dim}", "", f"![{dim}](chart-{slug(dim)}.svg)", "", _table(stats, has_tpr)]
    out += ["", "## How to read this", "",
            "- **Selection rate** — share of the category the tool selected (or scored above the overall median).",
            "- **Impact ratio** — selection rate ÷ the most-selected category's rate. Below **0.80** is evidence of "
            "adverse impact under the EEOC four-fifths rule; NYC Local Law 144 requires publishing this number.",
            "- **p-value** — two-proportion z-test vs. the most-selected category. Small p means the gap is "
            "unlikely to be chance.",
            "- **TPR** — selection rate among people who were actually qualified (equal opportunity).",
            "- Categories under 2% of the data are shown but not used as the reference, as LL144 permits.", "",
            "> An impact ratio is a screening signal, not a legal conclusion. Investigate flagged gaps with "
            "domain experts and the people affected.", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- terminal
def terminal(results: dict[str, list[GroupStat]], color: bool = True) -> str:
    red, dim_, bold, reset = ("\033[31m", "\033[2m", "\033[1m", "\033[0m") if color else ("",) * 4
    lines = []
    for dim, stats in results.items():
        lines.append(f"\n{bold}{dim}{reset}")
        for st in stats:
            bar = "█" * round(min(st.impact_ratio, 1) * 20)
            tint = red if "adverse-impact" in st.flags else dim_ if "small-sample" in st.flags else ""
            mark = "  ⚠ " + ", ".join(st.flags) if st.flags else ""
            lines.append(f"  {st.group[:28]:<28} {tint}{bar:<20}{reset} {st.impact_ratio:4.2f}  "
                         f"{dim_}n={st.n:<6} rate={st.rate:5.1%}{reset}{mark}")
    return "\n".join(lines)


def write(out_dir: str | Path, source: str, outcome: str,
          results: dict[str, list[GroupStat]], note: str = "") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for dim, stats in results.items():
        (out / f"chart-{slug(dim)}.svg").write_text(svg_chart(dim, stats), encoding="utf-8")
    (out / "report.md").write_text(markdown(source, outcome, results, note), encoding="utf-8")
    (out / "report.json").write_text(json.dumps(
        {"source": source, "outcome": outcome, "threshold": FOUR_FIFTHS,
         "results": {d: [s.to_dict() for s in ss] for d, ss in results.items()}}, indent=2), encoding="utf-8")
    return out / "report.md"
