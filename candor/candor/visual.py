"""Visual heuristics: is an element hidden, tiny, faded or low-contrast?"""
from __future__ import annotations

import re

from .dom import Document, Node

NAMED = {
    "white": (255, 255, 255), "black": (0, 0, 0), "gray": (128, 128, 128),
    "grey": (128, 128, 128), "silver": (192, 192, 192), "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211), "gainsboro": (220, 220, 220),
    "whitesmoke": (245, 245, 245), "darkgray": (169, 169, 169),
    "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
    "transparent": None,
}
SMALL_PRINT_HINTS = ("fine-print", "fineprint", "small-print", "smallprint",
                     "disclaimer", "legal", "footnote", "terms-small", "tiny")


def parse_color(value: str | None):
    if not value:
        return None
    v = value.strip().lower()
    if v in NAMED:
        return NAMED[v]
    if m := re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v):
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    if m := re.match(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)", v):
        return tuple(int(x) for x in m.groups())
    return None


def luminance(rgb) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg) -> float:
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def font_px(value: str | None) -> float | None:
    if not value:
        return None
    if m := re.fullmatch(r"([\d.]+)\s*(px|pt|em|rem|%)?", value.strip()):
        n, unit = float(m.group(1)), m.group(2) or "px"
        return {"px": n, "pt": n * 4 / 3, "em": n * 16, "rem": n * 16, "%": n * 0.16}[unit]
    return {"xx-small": 9, "x-small": 10, "smaller": 13, "small": 13}.get(value.strip())


def deemphasis(doc: Document, node: Node) -> str | None:
    """Return a human reason if the element is visually suppressed, else None."""
    chain = [node, *node.ancestors()]
    for n in chain:
        s = doc.style(n)
        if s.get("display") == "none" or s.get("visibility") == "hidden" or "hidden" in n.attrs:
            return "hidden from view"
        try:
            if float(s.get("opacity", "1")) <= 0.5:
                return f"faded (opacity {s['opacity']})"
        except ValueError:
            pass
    px = font_px(doc.computed(node, "font-size"))
    if px is not None and px <= 11:
        return f"tiny text ({px:g}px)"
    if any(n.tag == "small" for n in chain):
        return "set in <small> print"
    if any(h in n.hint() for n in chain for h in SMALL_PRINT_HINTS):
        return "styled as fine print"
    fg = parse_color(doc.computed(node, "color"))
    bg = parse_color(doc.computed(node, "background-color") or doc.computed(node, "background")) or (255, 255, 255)
    if fg and (ratio := contrast(fg, bg)) < 3:
        return f"low contrast ({ratio:.1f}:1, WCAG wants ≥4.5:1)"
    return None
