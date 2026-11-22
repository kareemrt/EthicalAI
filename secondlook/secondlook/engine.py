"""Combine red flags into one explainable verdict.

Scoring is deliberately simple so it can be explained to anyone:

1. Each rule that fires has a weight (0..1).
2. Within a category only the strongest hit counts, so a message that
   says "urgent" five times isn't five times as suspicious.
3. Categories combine like independent warnings:
       risk = 1 - (1 - w1) * (1 - w2) * ...
   Two moderate flags together are more worrying than either alone,
   but the score can never exceed 100%.
"""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, field

from .links import analyze_url, brand_mismatch, extract_urls
from .signals import match_signals

LEVELS = (  # (minimum risk, label, headline)
    (0.70, "high", "Likely a scam"),
    (0.35, "caution", "Be careful"),
    (0.00, "low", "No common scam signs found"),
)

ADVICE = {
    "high": [
        "Don't click links, reply, call back, or pay anything.",
        "If it claims to be a company or agency, contact them using the number "
        "on your card, bill, or their official website — never the one in the message.",
        "Talk it over with someone you trust before doing anything.",
        "Report it: forward texts to 7726 (SPAM) and report fraud at reportfraud.ftc.gov "
        "(US) or your national fraud centre.",
    ],
    "caution": [
        "Pause. Nothing legitimate requires you to act in the next few minutes.",
        "Check independently: open the company's app or type their address yourself.",
        "Never share codes, passwords, or card numbers in reply to a message.",
    ],
    "low": [
        "No common scam patterns were found, but no tool catches everything.",
        "If something still feels off, trust that feeling and check with the sender directly.",
    ],
}


@dataclass
class Flag:
    id: str
    category: str
    weight: float
    title: str
    why: str
    evidence: str


@dataclass
class Report:
    risk: float
    level: str
    headline: str
    flags: list[Flag] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk"] = round(self.risk, 3)
        return d


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(str.maketrans("‘’“”", "''\"\""))
    return " ".join(text.split())


def check(message: str) -> Report:
    """Analyse one message and return a Report. Pure function, no I/O."""
    text = normalize(message)
    flags: list[Flag] = [
        Flag(s.id, s.category, s.weight, s.title, s.why, excerpt[:120])
        for s, excerpt in match_signals(text)
    ]

    urls = extract_urls(text)
    found = [f for u in urls for f in analyze_url(u)]
    if not any(f.id in ("link_brand_bait", "link_lookalike") for f in found):
        found += brand_mismatch(text, urls)  # skip if already explained more precisely
    for f in found:
        flags.append(Flag(f.id, "link", f.weight, f.title, f.why, f.url))

    strongest: dict[str, float] = {}
    for f in flags:
        strongest[f.category] = max(strongest.get(f.category, 0.0), f.weight)
    safe = 1.0
    for w in strongest.values():
        safe *= 1.0 - w
    risk = 1.0 - safe

    level, headline = next((lv, h) for floor, lv, h in LEVELS if risk >= floor)
    flags.sort(key=lambda f: -f.weight)
    return Report(risk, level, headline, flags, urls, ADVICE[level])
