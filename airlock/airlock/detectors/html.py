"""Content hidden from humans in HTML but still read by models.

Covers CSS-hidden elements (display:none, font-size:0, off-screen, ...),
the `hidden` attribute, and HTML comments that carry instructions. Also
exposes `visible_text()` — what a person actually sees — for sanitizing.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from itertools import count

from ..findings import Finding, Severity, Source, shorten
from . import phrases

HTML_HINT = re.compile(r"<(!doctype|html|head|body|div|p|span|a|img|section|article|table|ul|!--)\b", re.I)

_HIDE = [
    ("display:none", re.compile(r"display\s*:\s*none", re.I)),
    ("visibility:hidden", re.compile(r"visibility\s*:\s*hidden", re.I)),
    ("zero font size", re.compile(r"font-size\s*:\s*0*(\.0*)?[01]?(px|pt)?\s*(;|$|!)", re.I)),
    ("zero opacity", re.compile(r"opacity\s*:\s*0*(\.0+)?\s*(;|$|!)", re.I)),
    ("transparent text", re.compile(r"(^|;|\s)color\s*:\s*transparent", re.I)),
    ("off-screen", re.compile(r"(left|top|text-indent)\s*:\s*-\d{4,}", re.I)),
    ("clipped to nothing", re.compile(r"clip(-path)?\s*:\s*(rect\(0|inset\(50%)", re.I)),
]
_SKIP = {"script", "style", "noscript", "svg"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
         "param", "source", "track", "wbr"}
_BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
          "section", "article", "header", "footer", "blockquote", "pre", "table"}


def looks_like_html(text: str) -> bool:
    return bool(HTML_HINT.search(text))


def _hidden_reason(attrs: dict) -> str | None:
    if "hidden" in attrs:
        return "hidden attribute"
    style = attrs.get("style") or ""
    return next((name for name, rx in _HIDE if rx.search(style)), None)


class _Walker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ids = count()
        self.stack: list[tuple[str, str | None, int]] = []   # (tag, hidden reason, uid)
        self.visible: list[str] = []
        self.hidden: dict[int, list] = {}   # uid of hidden root -> [line, col, reason, chunks]
        self.comments: list[tuple[int, int, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK:
            self.visible.append("\n")
        if tag not in _VOID:
            self.stack.append((tag, _hidden_reason(dict(attrs)), next(self._ids)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in _BLOCK:
            self.visible.append("\n")

    def handle_data(self, data):
        if any(tag in _SKIP for tag, _, _ in self.stack):
            return
        root = next(((why, uid) for _, why, uid in self.stack if why), None)
        if root is None:
            self.visible.append(data)
            return
        why, uid = root
        if uid not in self.hidden:
            line, col = self.getpos()
            self.hidden[uid] = [line, col + 1, why, []]
        self.hidden[uid][3].append(data)

    def handle_comment(self, data):
        line, col = self.getpos()
        self.comments.append((line, col + 1, data))

    def run(self, text: str) -> "_Walker":
        self.feed(text)
        self.close()
        return self


def visible_text(html: str) -> str:
    text = "".join(_Walker().run(html).visible)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip() + "\n"


def detect(src: Source):
    if not looks_like_html(src.text):
        return
    walker = _Walker().run(src.text)

    for line, col, reason, chunks in walker.hidden.values():
        text = " ".join("".join(chunks).split())
        hit = phrases.first_match(text)
        if hit:
            yield _at(line, col, "html.hidden-instructions", Severity.HIGH,
                      f"Text hidden via {reason} contains instructions ({hit[0]}).", text)
        elif len(text) >= 40:
            yield _at(line, col, "html.hidden-text", Severity.LOW,
                      f"{len(text)} characters of text hidden via {reason}.", text)

    for line, col, body in walker.comments:
        hit = phrases.first_match(body)
        if hit:
            yield _at(line, col, "html.comment-instructions", Severity.HIGH,
                      f"HTML comment contains instructions ({hit[0]}).", body)


def _at(line, col, rule, severity, message, excerpt):
    return Finding(rule, severity, message, line, col, shorten(excerpt))
