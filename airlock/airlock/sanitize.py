"""Neutralize untrusted text before it reaches a model.

Sanitizing is lossy by design: it keeps what a human would see and drops
what only a machine would. It does NOT rewrite suspicious *wording* —
that's a judgment call left to the scan report and to you.
"""
from __future__ import annotations

from .detectors.exfil import PLACEHOLDER, URL
from .detectors.html import looks_like_html, visible_text
from .detectors.unicode import TAG_RUN, INVISIBLE, is_flag_sequence


def sanitize(text: str, *, html: bool | None = None) -> str:
    """Return a safer copy of `text`.

    1. HTML -> only the text a person would see (hidden elements, comments,
       scripts and styles removed). Auto-detected unless `html` is given.
    2. Invisible Unicode removed (tag smuggling, variation-selector payloads,
       bidi controls, zero-width characters) — regional flag emoji are kept.
    3. URLs with fill-in placeholders are defanged.
    """
    if html if html is not None else looks_like_html(text):
        text = visible_text(text)

    flags = [m.span() for m in TAG_RUN.finditer(text) if is_flag_sequence(text, *m.span())]
    if flags:  # keep legit 🏴 subdivision flags, strip everything else
        parts, last = [], 0
        for s, e in flags:
            parts += [INVISIBLE.sub("", text[last:s]), text[s:e]]
            last = e
        text = "".join(parts) + INVISIBLE.sub("", text[last:])
    else:
        text = INVISIBLE.sub("", text)

    return URL.sub(lambda m: "[link removed by airlock]" if PLACEHOLDER.search(m.group()) else m.group(), text)
