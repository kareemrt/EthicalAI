"""Render an Audit as a terminal report or JSON."""

import json
import os
import sys
from dataclasses import asdict

from .agents import ANSWER, CATEGORIES, SEARCH, USER
from .audit import Audit

_C = {"red": 31, "green": 32, "yellow": 33, "dim": 2, "bold": 1}


def _color(on: bool):
    def paint(text: str, style: str) -> str:
        return f"\033[{_C[style]}m{text}\033[0m" if on else text
    return paint


def text(audit: Audit, color: bool | None = None, verbose: bool = False) -> str:
    if color is None:
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    c = _color(color)
    out = [f"\n  {c('optout', 'bold')} · {audit.site} · path {audit.path}\n"]

    for cat, title in CATEGORIES.items():
        rows = audit.of(cat)
        want_open = cat == SEARCH
        good = sum(v.decision.allowed == want_open for v in rows)
        bar = "█" * round(10 * good / len(rows)) + "░" * (10 - round(10 * good / len(rows)))
        label = "open" if want_open else "blocked" + ("  (your call)" if cat in (ANSWER, USER) else "")
        out.append(f"  {c(title.upper(), 'bold'):<38} {bar}  {good}/{len(rows)} {label}")
        reasons = {(v.decision.allowed, v.decision.reason) for v in rows}
        if len(reasons) == 1 and not verbose:  # uniform category: one line says it all
            allowed, reason = reasons.pop()
            state = "open" if allowed else "blocked"
            out.append(c(f"    all {len(rows)} {state} — {reason}", "dim"))
        else:
            for v in rows:
                ok = v.decision.allowed == want_open
                if not verbose and (ok or cat in (ANSWER, USER)):
                    continue  # compact mode: show only what needs attention
                mark = c("✓", "green") if ok else c("✗", "yellow" if cat in (ANSWER, USER) else "red")
                state = "open   " if v.decision.allowed else "blocked"
                out.append(f"    {mark} {v.agent.token:<29} {v.agent.operator:<23} {state}  "
                           + c(v.decision.reason, "dim"))
        out.append("")

    out.append(f"  {c('SIGNALS', 'bold')}")
    rs = audit.robots_status
    robots_line = (f"robots.txt found, names {audit.robots_groups} user agent{'s' * (audit.robots_groups != 1)}" if 200 <= rs < 300
                   else f"robots.txt unreachable (HTTP {rs}) — crawlers must assume full disallow"
                   if rs >= 500 else f"no robots.txt (HTTP {rs}) — everything is open")
    out.append(f"    {c('✓', 'green') if 200 <= rs < 300 else c('✗', 'red')} {robots_line}")
    for s in audit.signals:
        out.append(f"    {c('✓', 'green') if s.present else c('·', 'yellow')} {s.name:<36} {c(s.detail, 'dim')}")

    grade_style = {"A": "green", "B": "green", "C": "yellow"}.get(audit.grade, "red")
    out.append(f"\n  {c('GRADE ' + audit.grade, grade_style)}  " +
               ("; ".join(audit.problems) or "AI training crawlers are opted out."))
    if audit.problems or audit.grade != "A":
        out.append(c("  fix:  optout generate training >> robots.txt   (and --tdmrep for EU opt-out)", "dim"))
    return "\n".join(out) + "\n"


def as_json(audit: Audit) -> str:
    data = asdict(audit)
    data["grade"], data["problems"] = audit.grade, audit.problems
    return json.dumps(data, indent=2, default=str)
