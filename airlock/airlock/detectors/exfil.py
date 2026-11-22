"""Data-exfiltration channels and encoded payloads.

* URLs with template placeholders ask the model to "fill in" private data.
* Auto-loading images with data-shaped query strings leak on render.
* Base64 blobs that decode to instructions slip past keyword filters.
"""
from __future__ import annotations

import base64
import binascii
import re
from urllib.parse import parse_qsl, urlsplit

from ..findings import Severity, Source
from . import phrases

URL = re.compile(r"https?://[^\s\"'<>()\]]+(?:\([^\s)]*\)[^\s\"'<>()\]]*)*", re.I)
PLACEHOLDER = re.compile(r"\{[^}\s]{0,40}\}|\$\{|%7B|\[(?:[A-Z_]{3,})\]|<[A-Za-z_]{3,}>|\bINSERT_|\bYOUR_", re.I)
MD_IMAGE = re.compile(r"!\[[^\]\n]*\]\(\s*<?(https?://[^\s)>]+)", re.I)
HTML_IMAGE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']?(https?://[^\"'\s>]+)", re.I)
B64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{32,8192}={0,2}(?![A-Za-z0-9+/=])")
LEAKY_PARAM = re.compile(r"^(q|d|data|payload|secret|token|key|chat|msg|message|conversation|"
                         r"history|info|leak|exfil|content|prompt|context|email|pw|pass(word)?)$", re.I)


def detect(src: Source):
    text = src.text

    for m in URL.finditer(text):
        if PLACEHOLDER.search(m.group()):
            yield src.finding(
                "exfil.url-template", Severity.HIGH,
                "URL contains a fill-in placeholder — a model may be tricked into "
                "writing private data into it.", m.start(), m.end())

    for rx in (MD_IMAGE, HTML_IMAGE):
        for m in rx.finditer(text):
            url = m.group(1)
            if PLACEHOLDER.search(url):
                continue  # already reported above
            params = parse_qsl(urlsplit(url).query, keep_blank_values=True)
            if any(LEAKY_PARAM.match(k) or len(v) >= 32 for k, v in params):
                yield src.finding(
                    "exfil.image-beacon", Severity.MEDIUM,
                    "Auto-loading image sends data-shaped query parameters to "
                    f"{urlsplit(url).hostname} when rendered.", m.start(1), m.start(1) + len(url))

    for m in B64.finditer(text):
        decoded = _b64_text(m.group())
        hit = decoded and phrases.first_match(decoded)
        if hit:
            yield src.finding(
                "exfil.encoded-instructions", Severity.HIGH,
                f"Base64 blob decodes to instructions ({hit[0]}).",
                m.start(), excerpt=f'decoded: "{decoded}"')


def _b64_text(blob: str) -> str | None:
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True)
        text = raw.decode("utf-8")
    except (binascii.Error, ValueError):
        return None
    return text if text and sum(c.isprintable() or c in "\n\t" for c in text) / len(text) > 0.95 else None
