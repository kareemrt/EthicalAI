"""Tiny dependency-free SVG bar chart of impact ratios.

Charts adapt to light/dark mode via an embedded media query, so they look
right both on GitHub and in a browser.
"""

from __future__ import annotations

from html import escape

from .audit import Dimension
from .metrics import EXCLUDED

COLORS = {"ok": "#2f9e6e", "review": "#d99a00", "adverse": "#d64545"}

STYLE = """
text{font:12px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;fill:#3b3f45}
.t{font-weight:600;font-size:14px}.m{fill:#80868f}.grid{stroke:#d8dce1}
.thr{stroke:#3b3f45;stroke-dasharray:4 3}
@media (prefers-color-scheme:dark){text{fill:#d6d9dd}.grid{stroke:#3a3f46}.thr{stroke:#d6d9dd}}
"""


def impact_chart(dim: Dimension, threshold: float, width: int = 720) -> str:
    label_w, pad, row_h, top = 270, 16, 26, 58
    bar_w = width - label_w - pad * 2 - 48
    rows = dim.groups
    height = top + row_h * len(rows) + 30
    scale = max([1.0, *(g.impact_ratio or 0 for g in rows)])
    x0 = label_w + pad

    def x(v: float) -> float:
        return x0 + bar_w * v / scale

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Impact ratios by {escape(dim.name)}">',
        f"<style>{STYLE}</style>",
        f'<text class="t" x="{pad}" y="22">Impact ratio by {escape(dim.name)}</text>',
    ]
    lx = width - pad
    for status in ("ok", "review", "adverse"):  # legend, laid out right-to-left
        lx -= 8 + 7 * len(status)
        out.append(f'<circle cx="{lx - 8}" cy="18" r="4" fill="{COLORS[status]}"/>'
                   f'<text class="m" x="{lx}" y="22">{status}</text>')
        lx -= 22
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        if tick <= scale:
            out.append(f'<line class="grid" x1="{x(tick):.1f}" x2="{x(tick):.1f}" '
                       f'y1="{top - 8}" y2="{height - 24}"/>')
            out.append(f'<text class="m" x="{x(tick):.1f}" y="{height - 8}" '
                       f'text-anchor="middle">{tick:g}</text>')

    tx = x(threshold)
    out.append(f'<line class="thr" x1="{tx:.1f}" x2="{tx:.1f}" y1="{top - 10}" '
               f'y2="{height - 24}"/>')
    out.append(f'<text class="m" x="{tx:.1f}" y="{top - 14}" text-anchor="middle">'
               f"{threshold:g} threshold</text>")
    for i, g in enumerate(rows):
        y = top + i * row_h
        label = g.group if len(g.group) <= 40 else g.group[:39] + "…"
        out.append(f'<text x="{x0 - 10}" y="{y + 13}" text-anchor="end">'
                   f"<title>{escape(g.group)}</title>{escape(label)}</text>")
        if g.status == EXCLUDED:
            out.append(f'<text class="m" x="{x0 + 4}" y="{y + 13}">'
                       f"excluded · n={g.total} ({g.share:.1%})</text>")
            continue
        ir = g.impact_ratio or 0
        out.append(f'<rect x="{x0}" y="{y}" width="{max(1.0, x(ir) - x0):.1f}" '
                   f'height="{row_h - 8}" rx="3" fill="{COLORS[g.status]}"/>')
        out.append(f'<text x="{x0 + bar_w + 44}" y="{y + 13}" text-anchor="end">'
                   f"{ir:.2f}</text>")

    out.append("</svg>")
    return "\n".join(out)
