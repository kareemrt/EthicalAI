"""Text signals: the red flags fraud investigators teach people to look for.

Every rule is plain data so anyone (a caregiver, a librarian, a bank's
fraud team) can read, audit, or extend it without touching the engine.

Fields
------
id        stable identifier, used in JSON output and tests
category  groups related rules; only the strongest hit per category counts
weight    0..1, how strongly this flag alone suggests a scam
pattern   case-insensitive regex run over normalised text
title     short label shown to the reader
why       one sentence, plain language: why scammers do this
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    id: str
    category: str
    weight: float
    pattern: re.Pattern
    title: str
    why: str


def _s(id, category, weight, pattern, title, why):
    return Signal(id, category, weight, re.compile(pattern, re.I), title, why)


SIGNALS: tuple[Signal, ...] = (
    # --- How they want to be paid --------------------------------------
    _s("pay_giftcard", "payment", 0.85,
       r"\b(gift ?cards?|itunes cards?|google play cards?|steam cards?|"
       r"apple cards?)\b.{0,60}\b(buy|purchase|pay|send|scratch|codes?|numbers?)\b|"
       r"\b(buy|purchase|pay|send|get)\b.{0,60}\bgift ?cards?\b",
       "Asks for payment in gift cards",
       "No real government agency, utility, or business takes payment in gift cards. "
       "Gift cards are untraceable, which is why scammers want them."),
    _s("pay_crypto", "payment", 0.7,
       r"\b(bitcoin|btc|crypto(currency)?|usdt|tether|ethereum|bitcoin atm|crypto atm)\b",
       "Mentions cryptocurrency payment",
       "Crypto payments can't be reversed. Legitimate agencies never demand them."),
    _s("pay_wire", "payment", 0.55,
       r"\b(wire transfer|western union|moneygram|zelle|cash app|venmo)\b"
       r".{0,80}\b(send|pay|transfer|wire|immediately|now|today)\b|"
       r"\b(send|pay|transfer|wire)\b.{0,40}\b(via|through|by|with) "
       r"(zelle|cash app|venmo|western union|moneygram|wire)\b",
       "Asks you to wire money or use a payment app",
       "Wires and peer-to-peer apps work like cash: once sent, it's gone."),
    _s("pay_cash_courier", "payment", 0.75,
       r"\b(courier|driver|agent)\b.{0,60}\b(pick ?up|collect)\b.{0,40}\b(cash|money|gold|package)\b|"
       r"\bmail (cash|money)\b|\bcash in (a|an) (box|envelope)\b",
       "Wants cash picked up or mailed",
       "Sending a courier for cash is a hallmark of grandparent and tech-support scams."),

    # --- Pressure and isolation ----------------------------------------
    _s("urgency", "pressure", 0.3,
       r"\b(act now|immediately|urgent(ly)?|within (24|48) hours|"
       r"today only|final (notice|warning)|last chance|expires? (today|tonight|soon)|"
       r"right away|as soon as possible|asap|time.?sensitive)\b",
       "Creates a sense of urgency",
       "Rushing you is the oldest trick: it stops you from pausing to check."),
    _s("secrecy", "isolation", 0.65,
       r"\b(don'?t|do not|never) (tell|inform|mention|contact|talk to)\b.{0,40}"
       r"\b(anyone|anybody|bank|police|(your )?(family|son|daughter|wife|husband|kids|"
       r"children|parents|mom|mum|dad))\b|"
       r"\bkeep (this|it) (a )?(secret|confidential|between us)\b|\bgag order\b",
       "Tells you to keep it secret",
       "Scammers isolate you so no friend, relative, or bank teller can warn you."),
    _s("threat", "threat", 0.55,
       r"\b(arrest(ed)?|warrant|lawsuit|legal action|deport(ed|ation)?|jail|police will|"
       r"suspend(ed)?|terminat(e|ed)|frozen|lock(ed)?|disconnect(ed)?|seiz(e|ed|ure))\b"
       r".{0,60}\b(account|social security|ssn|number|license|power|service|you|your)\b|"
       r"\b(account|social security|ssn|number|license|service)\b.{0,30}"
       r"\b(suspended|frozen|locked|terminated|disconnected)\b|"
       r"\blegal action will be\b|\bwarrant (has been|was) issued\b",
       "Threatens arrest, suspension or legal action",
       "Fear is used to override judgment. Agencies contact you by mail first and "
       "never threaten immediate arrest by text or phone."),

    # --- What they want from you ---------------------------------------
    _s("ask_credentials", "credentials", 0.6,
       r"\b(confirm|verify|update|provide|enter|send|reply with|validate)\b.{0,40}"
       r"\b(password|passcode|pin|social security|ssn|account number|card number|"
       r"cvv|login|bank details|date of birth)\b",
       "Asks you to confirm passwords or personal numbers",
       "Your bank already has your details. Requests to 'verify' them are fishing."),
    _s("ask_code", "credentials", 0.8,
       r"\b(read|tell|give|send|share|forward)\b.{0,30}\b(me|us|back)\b.{0,30}"
       r"\b(code|otp|verification code|one.?time)\b|"
       r"\b(code|otp)\b.{0,30}\b(we|i) (just )?sent\b.{0,30}\b(read|tell|give|share)\b|"
       r"\breply with\b.{0,20}\b(code|otp)\b",
       "Asks you to share a one-time code",
       "Those codes are the key to your account. Anyone asking for one is trying to break in."),
    _s("remote_access", "credentials", 0.75,
       r"\b(anydesk|teamviewer|ultraviewer|logmein|remote (access|desktop|support)|"
       r"screen ?share|share (your|the) screen|install (this|the) (app|software))\b",
       "Wants remote access to your device",
       "Remote-access tools let a stranger see and control your computer and bank."),

    # --- The story they tell -------------------------------------------
    _s("prize", "bait", 0.6,
       r"\b(you('ve| have)? won|winner|lottery|sweepstakes|prize|jackpot|"
       r"claim your (reward|gift|prize)|selected to receive|free (gift|iphone|vacation))\b",
       "Says you won a prize",
       "You can't win a contest you didn't enter, and real prizes never need a fee."),
    _s("fee_to_receive", "bait", 0.65,
       r"\b(processing|release|delivery|customs|clearance|redelivery|handling|tax(es)?) "
       r"(fee|charge|payment)\b",
       "Asks a small fee to release something",
       "A small 'fee' is how they collect your card number, then charge far more."),
    _s("family_emergency", "story", 0.6,
       r"\b(grandma|grandpa|grandmother|grandfather|mom|dad)\b.{0,80}"
       r"\b(jail|arrested|accident|hospital|bail|trouble|lost my phone|new number)\b|"
       r"\b(hi|hey) (mum|mom|dad)\b.{0,40}\bnew (number|phone)\b",
       "A 'family member' in trouble",
       "Voices and numbers are easy to fake. Hang up and call your relative on the number you know."),
    _s("refund_overpay", "story", 0.55,
       r"\b(refund|overpa(id|yment)|accidentally (sent|deposited|transferred))\b"
       r".{0,80}\b(send (it )?back|return|refund)\b|"
       r"\b(send|wire|transfer|return)\b.{0,40}\b(overpa(id|yment)|the difference|excess)\b",
       "Claims you were overpaid and must send money back",
       "The 'overpayment' is fake or later reversed; the money you send back is real."),
    _s("fake_check", "story", 0.6,
       r"\b(send|mail) you a (check|cheque)\b.{0,80}\b(deposit|cash)\b",
       "Sends you a check and asks for money back",
       "Fake checks can take weeks to bounce. By then the money you forwarded is gone."),
    _s("investment", "story", 0.55,
       r"\b(guaranteed (returns?|profit)|risk.?free|double your money|\d{2,}% (return|profit)|"
       r"trading platform|investment opportunity)\b",
       "Promises guaranteed or unusually high returns",
       "Real investments always carry risk. 'Guaranteed' profits are a red flag."),
    _s("account_problem", "story", 0.4,
       r"\b(unusual|suspicious) (activity|sign.?in|login)|"
       r"(problem|issue) with your (account|payment|order|package|delivery)|"
       r"(package|parcel|shipment).{0,40}(on hold|undeliverable|could not be delivered|"
       r"incomplete address)|unpaid (toll|invoice|bill)\b",
       "Claims there's a problem with your account or delivery",
       "A made-up problem is the hook to get you to click a link or call a fake number."),
    _s("generic_greeting", "story", 0.15,
       r"^\W*(dear (customer|user|client|member|sir|madam|valued)|hello (customer|user))\b",
       "Generic greeting instead of your name",
       "Companies you do business with usually know your name."),
)


# Phrases that show up in *legitimate* security messages. When present,
# the code-sharing rule is skipped so real 2FA texts aren't flagged.
SAFE_CODE_PHRASES = re.compile(
    r"\b(never|do not|don'?t|won'?t ever|will never) (share|give|tell)|"
    r"\b(we|staff) (will )?never ask\b", re.I)


def match_signals(text: str) -> list[tuple[Signal, str]]:
    """Return (signal, matched excerpt) pairs for every rule that fires."""
    hits = []
    code_is_safe = bool(SAFE_CODE_PHRASES.search(text))
    for sig in SIGNALS:
        if sig.id == "ask_code" and code_is_safe:
            continue
        m = sig.pattern.search(text)
        if m:
            hits.append((sig, m.group(0).strip()))
    return hits
