"""Render audits as a terminal table, Markdown, or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from .metrics import Audit, Status

VERDICT = {
    Status.OK: "No adverse impact detected.",
    Status.WATCH: "Ratios pass, but at least one gap is statistically significant — monitor it.",
    Status.REVIEW: "At least one ratio is below the threshold, but the sample is too small to be conclusive — collect more data and review.",
    Status.ADVERSE: "Adverse impact: at least one category falls below the threshold with a statistically significant gap.",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1%}"


def _num(x: float | None, fmt: str = ".3f") -> str:
    return "—" if x is None else format(x, fmt)


def _p(x: float | None) -> str:
    return "—" if x is None else ("<0.001" if x < 0.001 else f"{x:.3f}")


def _rows(a: Audit) -> list[list[str]]:
    return [
        [g.name, str(g.n), _pct(g.share), _pct(g.rate), _num(g.impact_ratio), _p(g.p_value),
         f"{g.status.icon} {g.status.value}" + (" (ref)" if g.name == a.reference else "")]
        for g in a.groups
    ]


HEAD = ["Category", "N", "Share", "Rate", "Impact ratio", "p-value", "Status"]


def text(audits: list[Audit]) -> str:
    out = []
    for a in audits:
        rows = [HEAD] + _rows(a)
        widths = [max(len(r[i]) for r in rows) for i in range(len(HEAD))]
        line = lambda r: "  ".join(c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(r, widths)))
        out += [f"\n▌ {a.dimension}  ·  {a.meta['mode']} of '{a.meta['column']}'  ·  {a.total} rows, {a.unknown} unknown",
                line(rows[0]), "  ".join("─" * w for w in widths), *map(line, rows[1:]),
                f"→ {VERDICT[a.worst]}"]
    return "\n".join(out).lstrip("\n")


def markdown(audits: list[Audit], title: str = "Bias Audit Report", chart: str | None = None) -> str:
    holm = "Holm–Bonferroni-adjusted across categories in each table" if audits[0].meta["correction"] == "holm" \
        else "not corrected for multiple comparisons"
    worst = max((a.worst for a in audits), key=list(VERDICT).index)
    md = [f"# {title}", "", f"_Generated {date.today().isoformat()} by fairhire._", "",
          f"> **{worst.icon} {worst.value.upper()}** — {VERDICT[worst]}", ""]
    if chart:
        md += [f"![Impact ratios]({chart})", ""]
    for a in audits:
        md += [f"## {a.dimension}", "",
               f"{a.meta['mode'].capitalize()} of `{a.meta['column']}` · {a.total} records · "
               f"{a.unknown} with unknown category (excluded from ratios) · "
               f"reference: **{a.reference}**", "",
               "| " + " | ".join(HEAD) + " |",
               "|" + "|".join([":--"] + ["--:"] * (len(HEAD) - 1)) + "|",
               *["| " + " | ".join(r) + " |" for r in _rows(a)], ""]
    md += ["## Method", "",
           "* **Rate** — share of each category selected (or scoring above the sample median).",
           f"* **Impact ratio** — category rate ÷ highest category rate. Below **{audits[0].threshold}** fails the four-fifths rule.",
           f"* **p-value** — two-sided two-proportion z-test against the reference category (α = {audits[0].alpha}), {holm}.",
           "* **Status** — `ok` passes · `watch` passes but gap is significant · `review` fails but not significant (small sample) · "
           "`adverse` fails and is significant · `excluded` category is under the minimum share and is not rated.",
           "", "_A statistical screen, not a legal determination. Interpret with domain and legal expertise._", ""]
    return "\n".join(md)


def to_json(audits: list[Audit]) -> str:
    def enc(a: Audit) -> dict:
        d = asdict(a)
        d["worst"] = a.worst.value
        for g in d["groups"]:
            g["status"] = g["status"].value
        return d
    return json.dumps([enc(a) for a in audits], indent=2)
