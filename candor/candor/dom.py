"""A tiny, forgiving HTML DOM built on the standard library.

Just enough structure for the rules: a tree of `Node`s, source line numbers,
visible text, and a resolved style per element (inline styles plus simple
`tag`, `.class` and `#id` selectors found in <style> blocks).
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr"}
SKIP_TEXT = {"script", "noscript", "template"}
_WS = re.compile(r"\s+")


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line")

    def __init__(self, tag: str, attrs: dict | None = None,
                 parent: "Node | None" = None, line: int = 0):
        self.tag, self.attrs, self.parent, self.line = tag, attrs or {}, parent, line
        self.children: list[Node | str] = []

    # -- navigation ---------------------------------------------------------
    def iter(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent

    # -- content ------------------------------------------------------------
    def text(self) -> str:
        """Visible text of this node and its descendants, whitespace-collapsed."""
        parts: list[str] = []

        def walk(n: Node):
            if n.tag in SKIP_TEXT or n.tag == "style":
                return
            for c in n.children:
                if isinstance(c, str):
                    parts.append(c)
                else:
                    walk(c)
            if n.tag == "input" and n.attrs.get("type") in ("submit", "button"):
                parts.append(n.attrs.get("value", ""))
        walk(self)
        return _WS.sub(" ", " ".join(parts)).strip()

    def own_text(self) -> str:
        """Text directly inside this element (not its children); empty for code."""
        if self.tag in SKIP_TEXT or self.tag == "style":
            return ""
        return _WS.sub(" ", " ".join(c for c in self.children if isinstance(c, str))).strip()

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    @property
    def id(self) -> str:
        return self.attrs.get("id", "")

    def hint(self) -> str:
        """id + classes + aria-label + name, lowercased: handy for keyword checks."""
        a = self.attrs
        return " ".join([self.id, *self.classes, a.get("aria-label", ""),
                         a.get("name", ""), a.get("role", "")]).lower()

    def snippet(self, limit: int = 90) -> str:
        t = self.text() or self.attrs.get("value", "") or f"<{self.tag}>"
        return t if len(t) <= limit else t[: limit - 1] + "…"

    def __repr__(self):
        return f"<{self.tag} line={self.line}>"


class Document:
    """Parsed page: `root`, flat `nodes`, `labels` (for=id → label) and CSS."""

    def __init__(self, html: str, source: str = "<string>"):
        self.source = source
        builder = _Builder()
        builder.feed(html)
        builder.close()
        self.root = builder.root
        self.nodes = [n for n in self.root.iter() if n is not self.root]
        self.labels = {n.attrs["for"]: n for n in self.nodes
                       if n.tag == "label" and n.attrs.get("for")}
        self.css = _parse_css(" ".join(
            c for n in self.nodes if n.tag == "style"
            for c in n.children if isinstance(c, str)))
        self._style_cache: dict[int, dict] = {}

    def find(self, *tags: str):
        return [n for n in self.nodes if n.tag in tags]

    def text(self) -> str:
        return self.root.text()

    def style(self, node: Node) -> dict:
        """Own declared style: tag < .class < #id < inline (specificity order)."""
        key = id(node)
        if key not in self._style_cache:
            s: dict = {}
            s.update(self.css.get(node.tag, {}))
            for c in node.classes:
                s.update(self.css.get("." + c, {}))
            if node.id:
                s.update(self.css.get("#" + node.id, {}))
            s.update(_parse_decls(node.attrs.get("style", "")))
            self._style_cache[key] = s
        return self._style_cache[key]

    def computed(self, node: Node, prop: str) -> str | None:
        """Nearest declared value of `prop` on the node or an ancestor."""
        for n in (node, *node.ancestors()):
            if n is self.root:
                break
            v = self.style(n).get(prop)
            if v:
                return v
        return None


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.stack[-1], self.getpos()[0])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):  # tolerate unclosed tags
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _parse_decls(text: str) -> dict:
    out = {}
    for decl in text.split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            out[k.strip().lower()] = v.replace("!important", "").strip().lower()
    return out


_SIMPLE_SELECTOR = re.compile(r"^(?:[a-z][a-z0-9]*|[.#][\w-]+)$", re.I)


def _parse_css(css: str) -> dict:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: dict[str, dict] = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        decls = _parse_decls(body)
        for sel in selectors.split(","):
            sel = sel.strip()
            if _SIMPLE_SELECTOR.match(sel):
                rules.setdefault(sel.lower() if sel[0] not in ".#" else sel, {}).update(decls)
    return rules
