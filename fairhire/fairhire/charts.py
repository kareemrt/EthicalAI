"""Tiny dependency-free SVG chart: impact ratio per group, threshold line marked."""

from __future__ import annotations

from html import escape

from .metrics import DimensionResult

# Colours are defined once as CSS classes so the chart adapts to light/dark mode.
STYLE = """
.t{font:12px system-ui,-apple-system,Segoe UI,sans-serif;fill:#1f2328}
.m{fill:#59636e}.ok{fill:#3b82c4}.bad{fill:#d1495b}.na{fill:#c4c9cf}
.th{stroke:#1f2328;stroke-dasharray:4 3}.ax{stroke:#d0d7de}
@media (prefers-color-scheme:dark){.t{fill:#e6edf3}.m{fill:#9198a1}.th{stroke:#e6edf3}.ax{stroke:#3d444d}.na{fill:#4b5563}}
"""


def impact_chart(dim: DimensionResult, threshold: float, width: int = 640) -> str:
    row, label_w, value_w, pad = 26, 190, 60, 10
    plot_w = width - label_w - value_w - pad
    top = 30
    height = top + row * len(dim.groups) + 24
    x = lambda v: label_w + min(v, 1.0) * plot_w  # noqa: E731

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
        f'role="img" aria-label="Impact ratios by {escape(dim.name)}"><style>{STYLE}</style>',
        f'<text class="t" x="0" y="16" font-weight="600">Impact ratio by {escape(dim.name)}</text>',
    ]
    for i, g in enumerate(dim.groups):
        y = top + i * row
        out.append(f'<text class="t" x="{label_w - 8}" y="{y + 16}" text-anchor="end">{escape(g.name)}</text>')
        if g.excluded:
            out.append(f'<rect class="na" x="{label_w}" y="{y + 5}" width="{plot_w}" height="16" rx="3" opacity=".35"/>')
            out.append(f'<text class="m t" x="{label_w + 8}" y="{y + 17}">n={g.n} — too few to judge</text>')
            continue
        cls = "bad" if g.adverse else "ok"
        out.append(f'<rect class="{cls}" x="{label_w}" y="{y + 5}" width="{x(g.impact_ratio) - label_w:.1f}" height="16" rx="3"/>')
        out.append(f'<text class="t" x="{width - value_w + 6}" y="{y + 17}">{g.impact_ratio:.2f}</text>')

    tx = x(threshold)
    bottom = top + row * len(dim.groups)
    out += [
        f'<line class="ax" x1="{label_w}" x2="{label_w}" y1="{top}" y2="{bottom}"/>',
        f'<line class="th" x1="{tx:.1f}" x2="{tx:.1f}" y1="{top - 4}" y2="{bottom + 4}"/>',
        f'<text class="m t" x="{tx:.1f}" y="{bottom + 18}" text-anchor="middle">{threshold:.2f} threshold</text>',
        "</svg>",
    ]
    return "".join(out)
