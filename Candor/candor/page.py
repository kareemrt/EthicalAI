"""Turn raw HTML into a small, queryable document model.

Standard library only. We don't need a full DOM: just elements with their
text, inherited visibility flags ("hidden", "fine print") and parent links,
which is enough for every rule in ``rules.py``.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
SKIP = {"script", "style", "noscript", "template", "svg", "head"}
AUTO_CLOSE = {"p", "li", "option", "tr", "td", "th", "dt", "dd"}

_WS = re.compile(r"\s+")
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
_FONT_SIZE = re.compile(r"font-size\s*:\s*([\d.]+)\s*(px|pt|em|rem|%)", re.I)
_FAINT_COLOR = re.compile(r"(?<![-\w])color\s*:\s*#([0-9a-f]{3}|[0-9a-f]{6})\b", re.I)
_FINE_CLASS = re.compile(r"fine-?print|disclaimer|legal-?text|small-?print", re.I)
# Largest size we still consider "fine print", per CSS unit.
_FINE_LIMIT = {"px": 11, "pt": 8, "em": 0.75, "rem": 0.75, "%": 75}


def _is_fine(tag: str, attrs: dict) -> bool:
    """True if this element visually de-emphasises its text."""
    if tag == "small" or _FINE_CLASS.search(attrs.get("class", "")):
        return True
    style = attrs.get("style", "")
    m = _FONT_SIZE.search(style)
    if m and float(m.group(1)) <= _FINE_LIMIT[m.group(2).lower()]:
        return True
    m = _FAINT_COLOR.search(style)
    if m:  # light grey text, e.g. #ccc / #d0d0d0, reads as faint on white
        h = m.group(1)
        rgb = [int(c * 2, 16) for c in h] if len(h) == 3 else \
              [int(h[i:i + 2], 16) for i in (0, 2, 4)]
        return min(rgb) >= 0xBB and max(rgb) - min(rgb) < 0x20
    return False


class Element:
    __slots__ = ("tag", "attrs", "parent", "children", "line", "hidden",
                 "fine", "_parts", "_text")

    def __init__(self, tag: str, attrs: dict, parent: "Element | None", line: int):
        self.tag, self.attrs, self.parent, self.line = tag, attrs, parent, line
        self.children: list[Element] = []
        self._parts: list[str] = []
        self._text: str | None = None
        inherited_hidden = parent.hidden if parent else False
        self.hidden = inherited_hidden or "hidden" in attrs or \
            attrs.get("aria-hidden") == "true" or \
            bool(_HIDDEN_STYLE.search(attrs.get("style", "")))
        self.fine = (parent.fine if parent else False) or _is_fine(tag, attrs)

    @property
    def text(self) -> str:
        """All descendant text, whitespace-normalised."""
        if self._text is None:
            self._text = _WS.sub(" ", " ".join(self._parts)).strip()
        return self._text

    @property
    def label(self) -> str:
        """Human-facing name of a control: its text, value or aria-label."""
        return self.text or self.attrs.get("value", "") or self.attrs.get("aria-label", "")

    @property
    def selector(self) -> str:
        """Short CSS-like locator, e.g. ``button#decline`` or ``a.no-thanks``."""
        if self.attrs.get("id"):
            return f"{self.tag}#{self.attrs['id']}"
        if self.attrs.get("name"):
            return f"{self.tag}[name={self.attrs['name']}]"
        cls = self.attrs.get("class", "").split()
        return f"{self.tag}.{cls[0]}" if cls else self.tag

    def ancestors(self):
        node = self.parent
        while node:
            yield node
            node = node.parent

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.selector} L{self.line} {self.text[:40]!r}>"


class Page(HTMLParser):
    """Parse once, then query: ``Page(html).elements``, ``.actions``, ``.checkboxes``."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.root = Element("#root", {}, None, 1)
        self.elements: list[Element] = []
        self._stack = [self.root]
        self._skip = 0
        self.feed(html)
        self.close()
        self.by_id = {e.attrs["id"]: e for e in self.elements if e.attrs.get("id")}

    # -- parsing ---------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        if self._skip or tag in SKIP:
            self._skip += tag in SKIP
            return
        if tag in AUTO_CLOSE and self._stack[-1].tag == tag:
            self._stack.pop()
        parent = self._stack[-1]
        el = Element(tag, {k: v or "" for k, v in attrs}, parent, self.getpos()[0])
        parent.children.append(el)
        self.elements.append(el)
        if tag not in VOID:
            self._stack.append(el)

    def handle_endtag(self, tag):
        if self._skip:
            self._skip -= tag in SKIP
            return
        if tag in VOID:
            return
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if not self._skip and data.strip():
            for el in self._stack:
                el._parts.append(data)

    # -- queries ---------------------------------------------------------------
    @property
    def title(self) -> str:
        h1 = next((e for e in self.elements if e.tag == "h1"), None)
        return h1.text if h1 else ""

    @property
    def actions(self) -> list[Element]:
        """Everything a user can click to make a choice."""
        return [e for e in self.elements if not e.hidden and (
            e.tag in ("button", "a") or e.attrs.get("role") == "button" or
            (e.tag == "input" and e.attrs.get("type") in ("submit", "button")))]

    @property
    def checkboxes(self) -> list[Element]:
        return [e for e in self.elements if e.tag == "input" and not e.hidden
                and e.attrs.get("type") in ("checkbox", "radio")]

    def label_for(self, control: Element) -> str:
        """Visible label of a form control (``<label for>``, wrapping label, or parent)."""
        for anc in control.ancestors():
            if anc.tag == "label":
                return anc.text
        cid = control.attrs.get("id")
        if cid:
            for e in self.elements:
                if e.tag == "label" and e.attrs.get("for") == cid:
                    return e.text
        return control.parent.text if control.parent else ""

    def deepest(self, pattern: re.Pattern, *, include_hidden=False) -> list[Element]:
        """Innermost elements whose text matches ``pattern``.

        A child's text is a subset of its parent's, so we walk top-down and only
        enter subtrees that match: cost is ~one regex pass per matching branch.
        """
        found, todo = [], [c for c in reversed(self.root.children)]
        while todo:
            el = todo.pop()
            if (el.hidden and not include_hidden) or not pattern.search(el.text):
                continue
            matching = [c for c in el.children
                        if (include_hidden or not c.hidden) and pattern.search(c.text)]
            if matching:
                todo.extend(reversed(matching))
            else:
                found.append(el)
        return found
