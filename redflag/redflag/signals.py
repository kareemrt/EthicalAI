"""Human-readable red-flag signals.

Each Signal is a small, testable detector that answers one question a careful
friend would ask ("Is it asking for gift cards?"). Every hit carries the exact
text span that triggered it, so the final verdict can always be explained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable
from urllib.parse import urlparse


@dataclass(frozen=True)
class Hit:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Signal:
    id: str
    label: str      # what we noticed
    why: str        # why scammers do it
    advice: str     # what to do instead
    detect: Callable[[str], list[Hit]]


# ── helpers ──────────────────────────────────────────────────────────────────

def _rx(*patterns: str) -> Callable[[str], list[Hit]]:
    """Build a detector from case-insensitive regex alternatives."""
    rx = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
    return lambda text: [Hit(m.start(), m.end(), m.group(0)) for m in rx.finditer(text)]


NEGATION = re.compile(r"\b(never|not|don'?t|won'?t|will not|do not)\b[\w\s]{0,12}$", re.IGNORECASE)


def _unless_negated(detector: Callable[[str], list[Hit]]) -> Callable[[str], list[Hit]]:
    """Drop hits preceded by a negation ("we will never ask for your PIN")."""
    return lambda text: [h for h in detector(text) if not NEGATION.search(text[max(0, h.start - 30):h.start])]


URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"')]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|info|top|xyz|click|link|live|shop|support|zip|ru|cn|io|co|me|ly|gl|gy|gd|at|cc)(?:/[^\s<>\"')]*)?",
                 re.IGNORECASE)

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "rb.gy", "cutt.ly", "shorturl.at", "tiny.cc"}
RISKY_TLDS = {"top", "xyz", "click", "link", "live", "shop", "support", "zip", "ru", "cn", "info"}
BRANDS = {  # brand keyword -> official registrable domains
    "paypal": {"paypal.com"}, "amazon": {"amazon.com", "amazon.co.uk"}, "apple": {"apple.com"},
    "microsoft": {"microsoft.com"}, "netflix": {"netflix.com"}, "usps": {"usps.com"},
    "fedex": {"fedex.com"}, "dhl": {"dhl.com"}, "irs": {"irs.gov"}, "chase": {"chase.com"},
    "wellsfargo": {"wellsfargo.com"}, "bankofamerica": {"bankofamerica.com"}, "medicare": {"medicare.gov"},
}


def _host(url: str) -> str:
    return (urlparse(url if "://" in url else f"http://{url}").hostname or "").lower()


def _registrable(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-3:] if len(parts) > 2 and parts[-2] in {"co", "com", "gov"} and len(parts[-1]) == 2 else parts[-2:])


def _link_flags(text: str) -> list[Hit]:
    hits = []
    for m in URL.finditer(text):
        host = _host(m.group(0))
        reg, tld = _registrable(host), host.rsplit(".", 1)[-1]
        squashed = host.replace("-", "").replace(".", "")
        lookalike = any(b in squashed and reg not in official for b, official in BRANDS.items())
        if (reg in SHORTENERS or tld in RISKY_TLDS or "xn--" in host or lookalike
                or re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host)):
            hits.append(Hit(m.start(), m.end(), m.group(0)))
    return hits


def _shouting(text: str) -> list[Hit]:
    hits = [Hit(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\b[A-Z]{4,}(?:\s+[A-Z]{2,})+\b|!{2,}", text)]
    return hits


# ── the catalogue ────────────────────────────────────────────────────────────

SIGNALS: tuple[Signal, ...] = (
    Signal("urgency", "Pressure to act fast",
           "Rushing you stops you from thinking it over or asking someone.",
           "Real organisations give you time. Slow down - nothing legitimate expires in minutes.",
           _rx(r"\bact (now|fast|immediately)\b", r"\burgent(ly)?\b", r"\bimmediately\b", r"\bwithin \d+ (hours?|minutes?|hrs?|mins?)\b",
               r"\b(disconnected|closed|suspended|deleted|locked|terminated|cancell?ed|shut off)\b[^.!?\n]{0,20}\bin \d+ (hours?|minutes?|mins?)\b",
               r"\bfinal (notice|warning|reminder)\b", r"\b(expires?|ends) (today|tonight|soon)\b", r"\blast chance\b",
               r"\bright away\b", r"\bbefore it'?s too late\b", r"\btime[- ]sensitive\b")),
    Signal("threat", "Threats or scary consequences",
           "Fear makes people comply without checking.",
           "Government agencies and banks do not threaten arrest by text or phone. Hang up and call them on a number you trust.",
           _rx(r"\b(arrest(ed)?|warrant|deport(ed|ation)?|lawsuit|legal action|prosecut\w+|jail)\b",
               r"\b(account|card|service|number) (has been |will be |is )?(suspended|locked|frozen|disabled|terminated|closed)\b",
               r"\b(suspended|deactivated?|disconnect(ed|ion))\b", r"\bpenalt(y|ies)\b", r"\bcriminal\b")),
    Signal("authority", "Claims to be an official body or big brand",
           "Borrowing a trusted name lowers your guard.",
           "Don't use contact details from the message. Look up the official number or website yourself.",
           _rx(r"\b(IRS|SSA|FBI|HMRC|CRA)\b", r"\bsocial security (administration|office)\b", r"\bmedicare\b",
               r"\b(police|sheriff|customs|border patrol)\b", r"\b(tech(nical)? support|security (team|department))\b",
               r"\b(fraud (department|team))\b")),
    Signal("payment", "Asks for an unusual payment method",
           "Gift cards, crypto and wires are fast and nearly impossible to reverse.",
           "No real agency or company asks to be paid in gift cards or crypto. This alone means stop.",
           _unless_negated(_rx(r"\b(gift|itunes|google play|steam|apple|amazon|target|walmart) cards?\b", r"\bbitcoin|btc\b|\bcrypto(currency)?\b|\busdt\b",
                               r"\bwire (transfer|the money|funds)\b", r"\b(western union|moneygram)\b", r"\b(bitcoin|crypto) atm\b", r"\bprepaid (debit )?card\b",
                               r"\b(send|pay|transfer)\b[^.!?\n]{0,25}\b(via|by|through|on|with) (zelle|venmo|cash ?app)\b"))),
    Signal("credentials", "Asks for passwords, codes or personal numbers",
           "With a one-time code or PIN, a scammer can empty your account.",
           "Never share passwords, PINs or verification codes - not even with someone who says they're from your bank.",
           _unless_negated(_rx(r"\b(send|reply( with)?|provide|confirm|verify|enter|update|share|give|tell|read)\b[^.!?\n]{0,40}\b(password|pin|ssn|social security number|verification code|one[- ]time (pass)?code|otp|card (number|details)|account (number|details)|bank details|login( details)?|security code|cvv)\b"))),
    Signal("prize", "Too good to be true",
           "A surprise prize, refund or guaranteed profit is bait.",
           "You can't win a contest you didn't enter. Real refunds don't need a fee or your card details.",
           _rx(r"\byou('ve| have)? (won|been selected)\b", r"\b(winner|lottery|sweepstakes|jackpot|inheritance)\b",
               r"\bclaim (your|the) (prize|reward|refund|gift|funds)\b", r"\bunclaimed (funds|refund|package)\b",
               r"\bguaranteed (returns?|profits?|income)\b", r"\b(double|triple) your (money|investment)\b",
               r"\b(risk[- ]free|free money)\b", r"\b\d{2,4}% (returns?|profit)\b")),
    Signal("secrecy", "Asks you to keep it secret",
           "Secrecy cuts you off from people who would spot the scam.",
           "Anyone telling you not to tell family or your bank is a scammer. Tell someone now.",
           _rx(r"\b(don'?t|do not) (tell|mention|inform|discuss)\b[^.!?\n]{0,30}\b(anyone|anybody|family|bank|mom|mum|dad|police)\b",
               r"\bkeep (this|it) (a )?(secret|confidential|between us)\b", r"\bbetween (you and me|us)\b")),
    Signal("remote_access", "Wants control of your device",
           "Remote-access apps let a scammer see your screen and move your money.",
           "Never install software because a caller or message told you to. Uninstall it and disconnect if you did.",
           _rx(r"\b(anydesk|teamviewer|ultraviewer|logmein|quick ?support|supremo)\b", r"\bremote (access|desktop|control)\b",
               r"\b(download|install) (this|the|our) (app|software|program)\b")),
    Signal("family_emergency", "Sudden emergency from a 'loved one'",
           "Impersonating a grandchild or relative in trouble triggers panic and love.",
           "Hang up or stop replying, then call your relative on the number you already have.",
           _rx(r"\b(hi |hey )?(mom|mum|dad|grandma|grandpa|nana|granny),? it'?s me\b", r"\b(this is|it'?s) my new number\b",
               r"\bnew (phone|number),? (lost|broke)\b", r"\b(lost|broke) my phone\b", r"\bi'?m in (jail|trouble|hospital)\b",
               r"\b(need|send) (money for )?bail\b", r"\b(please )?don'?t tell (mom|mum|dad|anyone)\b", r"\bcar accident\b")),
    Signal("generic_greeting", "Impersonal greeting",
           "Mass scams don't know your name.",
           "Your real bank or provider usually addresses you by name.",
           _rx(r"\bdear (customer|user|client|member|account holder|valued \w+|sir/madam|beneficiary|friend)\b")),
    Signal("risky_link", "Suspicious link",
           "Shortened, look-alike or odd-domain links hide where they really go.",
           "Don't tap the link. Type the company's address into your browser yourself.",
           _link_flags),
    Signal("shouting", "SHOUTING or excessive punctuation",
           "Capitals and !!! manufacture alarm and excitement.",
           "Professional messages rarely shout. Treat it as a warning sign.",
           _shouting),
    Signal("investment", "Investment or trading pitch",
           "Fake platforms show fake profits until you try to withdraw.",
           "Check any platform with your financial regulator before sending money. Be wary of online-only 'mentors'.",
           _rx(r"\binvestment (opportunity|plan|platform)\b", r"\btrading (platform|account|signals?)\b",
               r"\b(forex|crypto) (mentor|trading|expert)\b", r"\bpassive income\b")),
)


def scan(text: str, signals: Iterable[Signal] = SIGNALS) -> dict[str, list[Hit]]:
    """Run every signal over the text. Returns {signal_id: [hits]} for signals that fired."""
    results = {s.id: s.detect(text) for s in signals}
    return {k: v for k, v in results.items() if v}


BY_ID = {s.id: s for s in SIGNALS}
