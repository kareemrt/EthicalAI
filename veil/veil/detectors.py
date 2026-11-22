"""Detectors: what counts as sensitive, and how we know.

Each detector is a regex plus an optional validator. Validators turn
"looks like a number" into "is a real card / IBAN / SSN", which is what keeps
false positives low without any ML model.
"""

from __future__ import annotations

import ipaddress
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Detector:
    label: str                      # placeholder prefix, e.g. EMAIL -> [EMAIL_1]
    pattern: re.Pattern
    validate: Optional[Callable[[str], bool]] = None
    group: int = 0                  # redact only this capture group
    priority: int = 50              # higher wins when matches overlap
    kind: str = "pii"               # "pii" or "secret"


# ── validators ────────────────────────────────────────────────────────────────

def luhn(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def iban(s: str) -> bool:
    s = s.replace(" ", "").upper()
    if not 15 <= len(s) <= 34:
        return False
    rearranged = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


_DATE = re.compile(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}|^\d{1,2}[-./]\d{1,2}[-./]\d{4}")


def phone(s: str) -> bool:
    n = sum(c.isdigit() for c in s)
    return 10 <= n <= 15 and not _DATE.match(s)   # 2026-11-22 14 is a timestamp


def ip(s: str) -> bool:
    try:
        addr = ipaddress.ip_address(s)
    except ValueError:
        return False
    # Loopback / unspecified addresses identify no one.
    return not (addr.is_loopback or addr.is_unspecified)


def entropy(s: str) -> float:
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())


def high_entropy(s: str) -> bool:
    # Mixed case AND digits excludes hex hashes, UUIDs and ordinary words.
    has_classes = (any(c.islower() for c in s) and any(c.isupper() for c in s)
                   and any(c.isdigit() for c in s))
    return has_classes and entropy(s) >= 4.0


# ── registry ──────────────────────────────────────────────────────────────────

def _re(p: str, flags: int = 0) -> re.Pattern:
    return re.compile(p, flags)


DETECTORS: list[Detector] = [
    # Secrets — highest priority, a leaked key is the costliest mistake.
    Detector("PRIVATE_KEY", _re(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), priority=100, kind="secret"),
    Detector("JWT",         _re(r"\beyJ[\w-]{8,}\.eyJ[\w-]{8,}\.[\w-]{8,}"), priority=95, kind="secret"),
    Detector("AWS_KEY",     _re(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), priority=95, kind="secret"),
    Detector("GITHUB_TOKEN", _re(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b"), priority=95, kind="secret"),
    Detector("SLACK_TOKEN", _re(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), priority=95, kind="secret"),
    Detector("API_KEY",     _re(r"\b(?:sk|pk|rk)[-_](?:live|test|ant|proj)?[-_]?[A-Za-z0-9_-]{20,}"), priority=90, kind="secret"),
    Detector("URL_CREDENTIAL", _re(r"[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]+)@", re.I), group=1, priority=90, kind="secret"),
    Detector("SECRET",      _re(r"""(?i)(?<![a-z])(?:pass(?:word|wd)?|secret|token|api[_-]?key|auth[_-]?token)(?:[_-][a-z]+)*["']?\s*[:=]\s*["']?([^\s"',;]{6,})"""), group=1, priority=85, kind="secret"),
    Detector("HIGH_ENTROPY", _re(r"\b[A-Za-z0-9+/_=-]{24,}\b"), validate=high_entropy, priority=40, kind="secret"),

    # Personal data.
    Detector("EMAIL",       _re(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b"), priority=80),
    Detector("IBAN",        _re(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b"), validate=iban, priority=75),
    Detector("CREDIT_CARD", _re(r"\b(?:\d[ -]?){12,18}\d\b"), validate=luhn, priority=70),
    Detector("SSN",         _re(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"), priority=70),
    Detector("IP_ADDRESS",  _re(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{1,4}\b", re.I), validate=ip, priority=60),
    Detector("PHONE",       _re(r"(?<![\w+])(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)[ .-]?)?\d{2,4}(?:[ .-]\d{2,4}){1,4}\b"), validate=phone, priority=50),
]

LABELS = [d.label for d in DETECTORS]


def term_detector(term: str, label: str = "TERM") -> Detector:
    """User-supplied term (a name, a codename, a client) — matched whole-word, any case."""
    return Detector(label, _re(rf"(?<!\w){re.escape(term)}(?!\w)", re.I), priority=78)  # below EMAIL so a term never splits an address
