"""Turn markup into scannable text blocks plus structural signals.

One streaming pass with the stdlib HTMLParser. No DOM, no dependencies.
Output:
  blocks  - (line, text) for each block-level run of visible text
  signals - (pattern_id, line, excerpt) for patterns found in the markup itself
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

BLOCK_TAGS = frozenset(
    "address article aside blockquote body br button dd details dialog div dl dt "
    "fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr label legend "
    "li main nav ol option p pre section summary table td th tr ul".split()
)
VOID_TAGS = frozenset("area base br col embed hr img input link meta source track wbr".split())
SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg"})

COUNTDOWN_ATTR = re.compile(r"count-?down|timer|time-?left|expir", re.I)
TINY_STYLE = re.compile(
    r"font-size\s*:\s*(?:[0-9](?:\.\d+)?px|0?\.[0-6]\d*(?:em|rem))|opacity\s*:\s*0?\.[0-4]|"
    r"color\s*:\s*#(?:e[0-9a-f]{2}|f[0-9a-f]{2}|eee|ddd|fff)\b",
    re.I,
)
TINY_CLASS = re.compile(r"(?:^|[\s_-])(?:fine-?print|text-(?:xs|\[(?:[0-9]|10)px\])|tiny|legalese)(?:$|[\s_-])", re.I)
MATERIAL_TERMS = re.compile(
    r"renew|recurring|cancel|\bfees?\b|charge|subscri|commit|[$€£]\s?\d|per (?:month|year)|/\s?mo\b|/\s?yr\b",
    re.I,
)
CONSENT_TERMS = re.compile(
    r"newsletter|marketing|offers|promo|partner|third.part|share|consent|subscribe|updates|"
    r"insurance|protection|warranty|donat|add-?on|upgrade|premium|tip\b",
    re.I,
)
WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    return WS.sub(" ", text).strip()


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[int, str]] = []
        self.signals: list[tuple[str, int, str]] = []
        self._buf: list[str] = []
        self._tiny_buf: list[str] = []
        self._line = 0
        self._stack: list[tuple[str, bool]] = []  # (tag, is_tiny)
        self._tiny = 0
        self._skip = 0
        self._pending: list[tuple[int, str]] = []  # pre-checked boxes awaiting label text

    # ── tags ─────────────────────────────────────────────────────────────
    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag in SKIP_TAGS:
            self._skip += 1
            return
        if tag in BLOCK_TAGS and tag != "label":
            self._flush()
        line = self.getpos()[0]
        ident = f"{a.get('id', '')} {a.get('class', '')}"
        if COUNTDOWN_ATTR.search(ident) or "data-countdown" in a or "data-expires" in a:
            shown = " ".join(f'{k}="{v}"' for k, v in a.items() if k in ("id", "class") or k.startswith("data-"))
            self.signals.append(("countdown_timer", line, f"<{tag} {shown}>"))
        if tag == "input" and a.get("type", "").lower() == "checkbox" and "checked" in a:
            ctx = " ".join(a.get(k, "") for k in ("name", "id", "value", "aria-label"))
            self._pending.append((line, ctx))
        if tag in VOID_TAGS:
            return
        tiny = bool(TINY_STYLE.search(a.get("style", "")) or TINY_CLASS.search(a.get("class", "")))
        self._stack.append((tag, tiny))
        self._tiny += tiny

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and self._stack and self._stack[-1][0] == tag:
            self._tiny -= self._stack.pop()[1]

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if any(t == tag for t, _ in self._stack):
            while self._stack:
                t, tiny = self._stack.pop()
                self._tiny -= tiny
                if t == tag:
                    break
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._skip or not data.strip():
            return
        if not self._buf:
            self._line = self.getpos()[0]
        self._buf.append(data)
        if self._tiny:
            self._tiny_buf.append(data)

    # ── block assembly ───────────────────────────────────────────────────
    def _flush(self) -> None:
        text = _clean("".join(self._buf))
        if text:
            self.blocks.append((self._line, text))
            tiny = _clean("".join(self._tiny_buf))
            if tiny and MATERIAL_TERMS.search(tiny):
                self.signals.append(("hidden_terms", self._line, tiny))
            self._resolve_checkboxes(text)
        self._buf, self._tiny_buf = [], []

    def _resolve_checkboxes(self, label: str) -> None:
        for line, ctx in self._pending:
            context = f"{ctx} {label[:160]}"
            if CONSENT_TERMS.search(context):
                self.signals.append(("preselection", line, f"[x] {label[:120]}"))
        self._pending.clear()

    def close(self):
        super().close()
        self._flush()
        for line, ctx in self._pending:  # boxes with no label text at all
            if CONSENT_TERMS.search(ctx):
                self.signals.append(("preselection", line, f"[x] {ctx.strip()}"))
        self._pending.clear()


def extract_html(source: str) -> tuple[list[tuple[int, str]], list[tuple[str, int, str]]]:
    parser = _Extractor()
    parser.feed(source)
    parser.close()
    return parser.blocks, parser.signals


def extract_text(source: str) -> list[tuple[int, str]]:
    """Plain text / Markdown: one block per paragraph, tagged with its first line."""
    blocks, buf, start = [], [], 1
    for n, line in enumerate(source.splitlines(), 1):
        if line.strip():
            if not buf:
                start = n
            buf.append(line)
        elif buf:
            blocks.append((start, _clean(" ".join(buf))))
            buf = []
    if buf:
        blocks.append((start, _clean(" ".join(buf))))
    return blocks
