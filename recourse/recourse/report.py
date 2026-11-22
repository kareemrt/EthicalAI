"""Turn results into words people can read: terminal text, Markdown, JSON, SVG."""

from __future__ import annotations

from typing import Mapping
from xml.sax.saxutils import escape

from .audit import Report
from .model import Feature, Model
from .solver import Plan, best_plan, gap, locked_penalty, single_changes

MARK = {"flag": "⚠", "ok": "✓", "info": "·"}


def fmt(f: Feature, v: float) -> str:
    """Render a value with its unit: $41k, 78%, 2.5 yrs."""
    num = f"{v:,.2f}".rstrip("0").rstrip(".")
    if f.unit.startswith("$"):
        return f"${num}{f.unit[1:]}"
    if f.unit == "%":
        return f"{num}%"
    return f"{num} {f.unit}".strip()


def _plan_lines(plan: Plan) -> list[str]:
    w = max(len(c.feature.title) for c in plan.changes)
    return [f"    • {c.feature.title:<{w}}  {fmt(c.feature, c.before)} → {fmt(c.feature, c.after)}"
            for c in plan.changes]


# ------------------------------------------------------------------ explain
def explain_data(model: Model, x: Mapping[str, float]) -> dict:
    plan = best_plan(model, x)

    def change(c):
        return {"feature": c.feature.name, "from": c.before, "to": c.after, "effort": round(c.cost, 3)}

    return {
        "model": model.name,
        "decision": model.positive if model.approves(x) else model.negative,
        "score": round(model.score(x), 4),
        "threshold": model.threshold,
        "reasons": [{"feature": f.name, "value": x[f.name], "reference": f.reference,
                     "impact": round(c, 4)} for f, c in model.reasons(x)],
        "best_plan": {"feasible": plan.feasible, "effort": round(plan.cost, 3),
                      "shortfall": round(plan.shortfall, 4),
                      "changes": [change(c) for c in plan.changes]},
        "single_changes": [change(p.changes[0]) for p in single_changes(model, x)],
        "locked": [{"feature": f.name, "impact": round(p, 4)} for f, p in locked_penalty(model, x)],
    }


def explain_text(model: Model, x: Mapping[str, float], who: str = "applicant") -> str:
    s, approved = model.score(x), model.approves(x)
    out = [f"{model.name} — {who}",
           f"Decision: {(model.positive if approved else model.negative).upper()}"
           f"   (score {s:+.2f}, needs ≥ {model.threshold:+.2f})", ""]
    if approved:
        return "\n".join(out + ["No action needed."])

    reasons = model.reasons(x)
    if reasons:
        out.append("Main reasons")
        cols = [(f.title, fmt(f, x[f.name]), f"typical {fmt(f, f.reference)}", f"{c:+.2f}")
                for f, c in reasons]
        w = [max(len(r[i]) for r in cols) for i in range(4)]
        for i, (t, v, ref, c) in enumerate(cols, 1):
            out.append(f"  {i}. {t:<{w[0]}}  {v:>{w[1]}}  {ref:<{w[2]}}  {c:>{w[3]}}")
        out.append("")

    plan = best_plan(model, x)
    if plan.feasible:
        out.append("What would change the outcome")
        out.append(f"  Least-effort plan  (effort {plan.cost:.2f})")
        out += _plan_lines(plan)
        singles = [p for p in single_changes(model, x) if len(plan.changes) > 1 or
                   p.changes[0].feature is not plan.changes[0].feature]
        if singles:
            out.append("  Or any one of these on its own")
            w = max(len(p.changes[0].feature.title) for p in singles)
            for p in singles:
                c = p.changes[0]
                out.append(f"    • {c.feature.title:<{w}}  {fmt(c.feature, c.before)} → "
                           f"{fmt(c.feature, c.after)}  (effort {p.cost:.2f})")
    else:
        out.append("No achievable path to approval under this policy.")
        out.append(f"  Even the largest realistic changes leave the score {plan.shortfall:.2f} short:")
        out += _plan_lines(plan) if plan.changes else ["    (no changeable features help)"]

    locks = locked_penalty(model, x)
    if locks:
        total = sum(p for _, p in locks)
        names = ", ".join(f"{f.title} ({f.note or 'fixed'})" for f, _ in locks)
        share = -total / gap(model, x)
        tail = ("without them you would already be approved" if share >= 1
                else f"{share:.0%} of the gap to approval")
        out += ["", f"Outside your control: {names}.",
                f"  These cost {-total:.2f} points — {tail}."]
    return "\n".join(out)


# -------------------------------------------------------------------- audit
def _table(r: Report) -> list[list[str]]:
    rows = [["group", "n", "declined", "median effort", "no recourse", "locked penalty"]]
    for g in r.groups:
        rows.append([g.group, str(g.n), f"{g.declined} ({g.decline_rate:.0%})", f"{g.median_cost:.2f}",
                     f"{g.no_recourse} ({g.no_recourse_rate:.0%})", f"{g.mean_locked:+.2f}"])
    return rows


def audit_text(r: Report) -> str:
    rows = _table(r)
    w = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    line = lambda row: "  ".join(c.ljust(w[i]) if i == 0 else c.rjust(w[i]) for i, c in enumerate(row))
    out = [f"Recourse audit — {r.model.name}  (grouped by '{r.group_by}', {len(r.cases)} records)", "",
           line(rows[0]), line(["─" * n for n in w])] + [line(row) for row in rows[1:]] + ["", "Findings"]
    out += [f"  {MARK[f.severity]} {f.text}" for f in r.findings]
    return "\n".join(out)


def audit_markdown(r: Report) -> str:
    rows = _table(r)
    md = [f"# Recourse audit: {r.model.name}", "",
          f"{len(r.cases)} records, grouped by `{r.group_by}`. *Effort* is the minimum total cost of "
          "changes that would flip a decline into an approval under the model's action policy.", "",
          "| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    md += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    md += ["", "## Findings", ""] + [f"- {MARK[f.severity]} {f.text}" for f in r.findings]
    return "\n".join(md) + "\n"


def audit_data(r: Report) -> dict:
    return {
        "model": r.model.name, "group_by": r.group_by, "records": len(r.cases),
        "groups": [{"group": g.group, "n": g.n, "declined": g.declined,
                    "decline_rate": round(g.decline_rate, 4), "median_effort": round(g.median_cost, 4),
                    "no_recourse": g.no_recourse, "no_recourse_rate": round(g.no_recourse_rate, 4),
                    "mean_locked_penalty": round(g.mean_locked, 4)} for g in r.groups],
        "findings": [{"severity": f.severity, "text": f.text} for f in r.findings],
    }


def audit_svg(r: Report) -> str:
    """Three small-multiple bar panels comparing groups. Theme-aware, no deps."""
    panels = [("Declined", lambda g: g.decline_rate, "{:.0%}"),
              ("Median effort to flip a decline", lambda g: g.median_cost, "{:.2f}"),
              ("Declined with no path to approval", lambda g: g.no_recourse_rate, "{:.0%}")]
    label_w, bar_w, row_h, pw = 90, 150, 26, 300
    h = 60 + len(r.groups) * row_h
    width = pw * len(panels)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" width="{width}" '
             f'height="{h}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="12">',
             "<style>.t{fill:#1f2328}.m{fill:#59636e}.b0{fill:#4c6ef5}.b1{fill:#e8590c}.b2{fill:#2b8a3e}"
             ".b3{fill:#ae3ec9}.g{stroke:#d0d7de}@media(prefers-color-scheme:dark){.t{fill:#e6edf3}"
             ".m{fill:#9198a1}.b0{fill:#748ffc}.b1{fill:#ff922b}.b2{fill:#51cf66}.b3{fill:#da77f2}"
             ".g{stroke:#3d444d}}</style>"]
    for p, (title, get, form) in enumerate(panels):
        x0 = p * pw + 10
        top = max((get(g) for g in r.groups), default=0) or 1
        parts.append(f'<text class="t" x="{x0}" y="20" font-weight="600">{escape(title)}</text>')
        parts.append(f'<line class="g" x1="{x0 + label_w}" y1="32" x2="{x0 + label_w}" y2="{h - 10}"/>')
        for i, g in enumerate(r.groups):
            y = 38 + i * row_h
            bw = max(1.0, bar_w * get(g) / top)
            parts.append(f'<text class="m" x="{x0 + label_w - 8}" y="{y + 13}" text-anchor="end">'
                         f'{escape(g.group)}</text>')
            parts.append(f'<rect class="b{i % 4}" x="{x0 + label_w}" y="{y}" width="{bw:.1f}" '
                         f'height="18" rx="3"/>')
            parts.append(f'<text class="t" x="{x0 + label_w + bw + 6:.1f}" y="{y + 13}">'
                         f'{form.format(get(g))}</text>')
    return "\n".join(parts + ["</svg>"]) + "\n"


# ------------------------------------------------------------------ inspect
def inspect_text(model: Model) -> str:
    rows = [["feature", "weight", "changeable", "limits", "effort/unit", "note"]]
    for f in model.features.values():
        if f.mutable:
            arrow = {"increase": "↑", "decrease": "↓", "both": "↕"}[f.direction]
            lim = [] if f.max_change == float("inf") else [f"±{fmt(f, f.max_change)}"]
            if f.direction != "decrease" and f.max != float("inf"):
                lim.append(f"≤{fmt(f, f.max)}")
            if f.direction != "increase" and f.min != float("-inf"):
                lim.append(f"≥{fmt(f, f.min)}")
            rows.append([f.title, f"{f.weight:+g}", f"yes {arrow}", " ".join(lim) or "—", f"{f.cost:g}", f.note])
        else:
            rows.append([f.title, f"{f.weight:+g}", "no", "—", "—", f.note])
    w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = [f"{model.name}: score = {model.intercept:+g} + Σ weight·value, {model.positive} if ≥ {model.threshold:g}", ""]
    out += ["  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip() for r in rows]
    n_fixed, n = len(model.fixed), len(model.fixed) + len(model.mutable)
    out += ["", f"{n_fixed} of {n} weighted features cannot be changed by the person being scored."]
    if not model.mutable:
        out.append("⚠ No changeable features: nobody declined by this model has recourse.")
    out += [f"· {note}" for note in model.notes]
    return "\n".join(out)
