"""Invisible-character attacks: text a human can't see but a model reads.

* Tag characters (U+E0000-E007F) mirror ASCII invisibly ("ASCII smuggling").
* Variation selectors can carry arbitrary bytes behind a single emoji.
* Bidi controls reorder what's displayed vs. what's processed ("Trojan Source").
* Zero-width characters split words to dodge filters or encode bits.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Sequence

from ..findings import Severity, Source

TAG_RUN = re.compile("[\U000E0000-\U000E007F]+")
VS_RUN = re.compile("[︀-️\U000E0100-\U000E01EF]{4,}")
BIDI = re.compile("[‪-‮⁦-⁩]")
ZW_RUN = re.compile("[​‌‍⁠﻿᠎]+")

# Everything a sanitizer should drop (tags, VS supplement, bidi, zero-width).
INVISIBLE = re.compile(
    "[\U000E0000-\U000E007F\U000E0100-\U000E01EF‪-‮⁦-⁩"
    "​‌‍⁠﻿᠎]"
)

BLACK_FLAG = "\U0001F3F4"   # 🏴 + tag letters + U+E007F = regional flag (legit)
CANCEL_TAG = "\U000E007F"


def is_flag_sequence(text: str, start: int, end: int) -> bool:
    return start > 0 and text[start - 1] == BLACK_FLAG and text[end - 1] == CANCEL_TAG


def decode_tags(run: str) -> str:
    return "".join(chr(ord(c) - 0xE0000) for c in run if 0x20 <= ord(c) - 0xE0000 < 0x7F)


def decode_variation_selectors(run: str) -> str:
    """Bytes hidden as VS1-16 (0-15) and VS17-256 (16-255)."""
    data = bytes(ord(c) - 0xFE00 if ord(c) < 0xE0000 else ord(c) - 0xE0100 + 16 for c in run)
    return data.decode("utf-8", errors="ignore")


def printable(s: str) -> bool:
    return bool(s) and sum(ch.isprintable() for ch in s) / len(s) > 0.9


_NON_ASCII = re.compile(r"[^\x00-\x7F]")


@lru_cache(maxsize=4096)
def _fold(ch: str) -> str:
    return "" if INVISIBLE.match(ch) else unicodedata.normalize("NFKC", ch)


def skeletonize(text: str) -> tuple[str, Sequence[int]]:
    """Drop invisibles and NFKC-fold look-alikes (e.g. fullwidth ｉｇｎｏｒｅ).

    Returns the folded text and, for each folded char, its original index,
    so regex matches on the skeleton can be reported at true positions.
    Pure-ASCII text (the common case) is returned untouched.
    """
    if not _NON_ASCII.search(text):
        return text, range(len(text) + 1)
    out: list[str] = []
    index: list[int] = []
    last = 0
    for m in _NON_ASCII.finditer(text):
        i = m.start()
        out.append(text[last:i])
        index.extend(range(last, i))
        folded = _fold(m.group())
        out.append(folded)
        index.extend([i] * len(folded))
        last = i + 1
    out.append(text[last:])
    index.extend(range(last, len(text) + 1))
    return "".join(out), index


def detect(src: Source):
    text = src.text

    for m in TAG_RUN.finditer(text):
        if is_flag_sequence(text, m.start(), m.end()):
            continue
        hidden = decode_tags(m.group())
        yield src.finding(
            "unicode.tag-smuggling", Severity.HIGH,
            f"{len(m.group())} invisible tag characters spell out hidden text.",
            m.start(), excerpt=f'hidden: "{hidden}"' if hidden else "(non-printable tags)")

    for m in VS_RUN.finditer(text):
        hidden = decode_variation_selectors(m.group())
        if printable(hidden):
            yield src.finding(
                "unicode.variation-smuggling", Severity.HIGH,
                f"{len(m.group())} variation selectors encode a hidden message.",
                m.start(), excerpt=f'hidden: "{hidden}"')
        else:
            yield src.finding(
                "unicode.variation-smuggling", Severity.MEDIUM,
                f"Run of {len(m.group())} variation selectors can smuggle binary data.",
                m.start(), excerpt="(binary payload)")

    bidi = list(BIDI.finditer(text))
    if bidi:
        yield src.finding(
            "unicode.bidi-control", Severity.MEDIUM,
            f"{len(bidi)} bidirectional control character(s) can make displayed text "
            "differ from what a model reads.", bidi[0].start(),
            excerpt=" ".join(f"U+{ord(m.group()):04X}" for m in bidi[:6]))

    quiet = []  # lone, low-risk zero-widths get one summary finding
    for m in ZW_RUN.finditer(text):
        run, s, e = m.group(), m.start(), m.end()
        if run == "﻿" and s == 0:
            continue                    # byte-order mark
        if run in ("‌", "‍"):
            continue                    # legit joiners: emoji, Indic & Persian scripts
        splits_word = (s > 0 and e < len(text) and text[s - 1].isascii()
                       and text[s - 1].isalpha() and text[e].isascii() and text[e].isalpha())
        if len(run) >= 8:
            yield src.finding("unicode.zero-width", Severity.MEDIUM,
                              f"Run of {len(run)} zero-width characters may encode hidden bits.",
                              s, excerpt=f"{len(run)} × U+{ord(run[0]):04X}…")
        elif splits_word:
            yield src.finding("unicode.zero-width", Severity.MEDIUM,
                              "Zero-width character splits a word — a common filter-evasion trick.",
                              s, excerpt=INVISIBLE.sub("·", text[max(0, s - 12):e + 12]))
        else:
            quiet.append(s)
    if quiet:
        yield src.finding("unicode.zero-width", Severity.LOW,
                          f"{len(quiet)} stray zero-width character(s).", quiet[0],
                          excerpt=INVISIBLE.sub("·", text[max(0, quiet[0] - 12):quiet[0] + 12]))
