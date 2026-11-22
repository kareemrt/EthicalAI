"""Render an audit as terminal text, Markdown or JSON."""

import json
import os
import sys
from dataclasses import asdict


def _bar(fraction, width=20):
    filled = round(max(0.0, min(1.0, fraction)) * width)
    return "█" * filled + "░" * (width - filled)


def _paint(text, code):
    if sys.stdout.isatty() and not os.environ.get("NO_COLOR"):
        return f"\033[{code}m{text}\033[0m"
    return text


def verdict(risk):
    if risk.passes:
        return f"SAFER TO SHARE (every record hides among ≥{risk.k_target})"
    return f"NOT SAFE TO SHARE (target k={risk.k_target}, actual k={risk.k_min})"


def to_dict(audit):
    data = {k: v for k, v in audit.items() if k not in ("risk", "after", "fix")}
    data["risk"] = asdict(audit["risk"]) | {"passes": audit["risk"].passes}
    if audit.get("fix"):
        fix = audit["fix"]
        data["fix"] = {"levels": fix.levels, "depths": fix.depths,
                       "suppressed": fix.suppressed, "info_loss": round(fix.info_loss, 4)}
        data["after"] = asdict(audit["after"]) | {"passes": audit["after"].passes}
    return data


def render_json(audit):
    return json.dumps(to_dict(audit), indent=2, ensure_ascii=False)


def _risk_lines(r):
    n = max(r.records, 1)
    rows = [("Unique records", r.unique, r.unique_pct),
            (f"In classes < k={r.k_target}", r.at_risk, r.at_risk_pct)]
    lines = [f"  {label:<20} {count:>7,}  {pct:5.1f}%  {_bar(count / n)}" for label, count, pct in rows]
    return lines + [
        f"  {'Average risk':<20} {r.avg_risk:>7.2f}",
        f"  {'Worst-case risk':<20} {r.max_risk:>7.2f}  (k = {r.k_min})",
    ]


def render_text(audit):
    r = audit["risk"]
    head = f"Lineup · {audit['dataset']} · {r.records:,} records"
    out = [head, "─" * len(head)]
    ok = r.passes
    out.append(_paint(("✓ " if ok else "✗ ") + verdict(r), "32;1" if ok else "31;1"))
    out.append("")

    if audit["direct_identifiers"]:
        out.append("Direct identifiers  (remove before sharing)")
        width = max(map(len, audit["direct_identifiers"]))
        for col, why in audit["direct_identifiers"].items():
            out.append(f"  • {col:<{width}}  {why}")
        out.append("")

    out.append(f"Quasi-identifiers   {', '.join(r.qis) or '(none)'}")
    out.append(f"Sensitive           {', '.join(audit['sensitive']) or '(none)'}")
    out.append("")
    out.append("Re-identification risk")
    out += _risk_lines(r)
    out.append("")

    out.append("Records by class size")
    n = max(r.records, 1)
    for label, count in r.size_histogram.items():
        out.append(f"  {label:<11} {_bar(count / n)} {count:>7,}")
    out.append("")

    if audit["drivers"]:
        out.append("What drives the risk  (unique records saved if the column were removed)")
        width = max(len(d[0]) for d in audit["drivers"])
        for col, saved, distinct in audit["drivers"]:
            out.append(f"  {col:<{width}}  {saved:>6,} saved   {distinct:,} distinct values")
        out.append("")

    for d in r.diversity:
        out.append("Attribute disclosure (l-diversity)")
        out.append(f"  {d.column}: l = {d.l_min} · {d.homogeneous_records:,} records "
                   f"reveal their {d.column} just by their class")
        out.append("")

    fix = audit.get("fix")
    if fix:
        a = audit["after"]
        out.append(_paint("After anonymization", "1"))
        for q in r.qis:
            lv, depth = fix.levels[q], fix.depths[q]
            state = "kept as is" if lv == 0 else "hidden" if lv == depth else f"level {lv}/{depth}"
            out.append(f"  {q:<20} {state}")
        out.append(f"  Records suppressed   {fix.suppressed:,} ({100 * fix.suppressed / n:.1f}%)")
        out.append(f"  Information loss     {fix.info_loss:.0%}")
        out += _risk_lines(a)
        out += [f"  l-diversity of {d.column}: {d.l_min} · {d.homogeneous_records:,} records still revealed"
                for d in a.diversity]
        out.append(_paint(("✓ " if a.passes else "✗ ") + verdict(a), "32;1" if a.passes else "31;1"))
    elif not ok:
        out.append(f"Next: lineup fix {audit['dataset']} --k {r.k_target} -o safe.csv")
    return "\n".join(out)


def render_markdown(audit):
    r = audit["risk"]
    out = [f"# Re-identification audit: `{audit['dataset']}`", "",
           f"**{'✅' if r.passes else '❌'} {verdict(r)}** · {r.records:,} records", ""]
    if audit["direct_identifiers"]:
        out += ["## Direct identifiers", "", "| Column | Why |", "|---|---|"]
        out += [f"| `{c}` | {w} |" for c, w in audit["direct_identifiers"].items()]
        out.append("")
    out += ["## Risk", "", "| Metric | Value |", "|---|---|",
            f"| Quasi-identifiers | {', '.join(f'`{q}`' for q in r.qis)} |",
            f"| k-anonymity | {r.k_min} (target {r.k_target}) |",
            f"| Unique records | {r.unique:,} ({r.unique_pct:.1f}%) |",
            f"| Records in classes < k | {r.at_risk:,} ({r.at_risk_pct:.1f}%) |",
            f"| Average / worst-case risk | {r.avg_risk:.2f} / {r.max_risk:.2f} |"]
    out += [f"| l-diversity of `{d.column}` | {d.l_min} ({d.homogeneous_records:,} records revealed) |"
            for d in r.diversity]
    if audit["drivers"]:
        out += ["", "## Risk drivers", "", "| Column | Unique records saved if removed | Distinct values |",
                "|---|---|---|"]
        out += [f"| `{c}` | {s:,} | {d:,} |" for c, s, d in audit["drivers"]]
    if audit.get("fix"):
        fix, a = audit["fix"], audit["after"]
        out += ["", "## After anonymization", "",
                f"**{'✅' if a.passes else '❌'} {verdict(a)}** · k = {a.k_min} · "
                f"{fix.suppressed:,} records suppressed · {fix.info_loss:.0%} information loss"]
    return "\n".join(out) + "\n"


RENDERERS = {"text": render_text, "md": render_markdown, "json": render_json}
