"""Dependency-free SVG charts.

The output is a standalone SVG string that renders in browsers, GitHub
Markdown and the HTML report, and adapts to light and dark themes.
"""
from __future__ import annotations

from html import escape

from .metrics import Audit

COLORS = {"PASS": "#1a9e77", "REVIEW": "#e0a106", "FAIL": "#d64545"}
ROW, BAR_W, VALUE_W, PAD = 30, 360, 170, 16


def impact_chart(audit: Audit) -> str:
    """Horizontal bars of impact ratio per group, with the threshold marked."""
    groups = [g for g in audit.groups if g.impact_ratio is not None]
    names = [g.name if len(g.name) <= 32 else g.name[:31] + "…" for g in groups]
    x0 = PAD + 12 + 7 * max(map(len, names), default=6)   # ~7px per character
    width = x0 + BAR_W + VALUE_W
    top = 44
    height = top + ROW * max(len(groups), 1) + 34
    tx = x0 + BAR_W * audit.threshold

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-label="Impact ratios by {escape(audit.attribute)}" '
        'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" font-size="13">',
        "<style>text{fill:#1f2937}.muted{fill:#6b7280}.grid{stroke:#d1d5db}"
        "@media (prefers-color-scheme:dark){text{fill:#e5e7eb}.muted{fill:#9ca3af}"
        ".grid{stroke:#4b5563}}</style>",
        f'<text x="{PAD}" y="24" font-weight="600" font-size="15">'
        f'Impact ratio by {escape(audit.attribute)}</text>',
    ]
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        x = x0 + BAR_W * tick
        out.append(f'<line class="grid" x1="{x}" y1="{top - 6}" x2="{x}" '
                   f'y2="{height - 28}" stroke-width="1"/>')
        out.append(f'<text class="muted" x="{x}" y="{height - 12}" '
                   f'text-anchor="middle" font-size="11">{tick:g}</text>')

    out += [
        f'<line x1="{tx}" y1="{top - 10}" x2="{tx}" y2="{height - 28}" '
        f'stroke="{COLORS["FAIL"]}" stroke-width="1.5" stroke-dasharray="5 4"/>',
        f'<text x="{tx + 4}" y="{top - 12}" font-size="11" fill="{COLORS["FAIL"]}" '
        f'style="fill:{COLORS["FAIL"]}">{audit.threshold:g} threshold</text>',
    ]
    for i, (g, name) in enumerate(zip(groups, names)):
        y = top + i * ROW
        w = max(BAR_W * g.impact_ratio, 1.5)
        out += [
            f'<text x="{x0 - 10}" y="{y + 15}" text-anchor="end"><title>'
            f'{escape(g.name)}</title>{escape(name)}</text>',
            f'<rect x="{x0}" y="{y + 3}" width="{w:.1f}" height="{ROW - 10}" rx="3" '
            f'fill="{COLORS[g.status]}"/>',
            f'<text x="{x0 + BAR_W + 12}" y="{y + 15}" font-size="12">'
            f'{g.impact_ratio:.2f}<tspan class="muted"> · {g.rate:.1%} of {g.n:,}'
            "</tspan></text>",
        ]

    out.append("</svg>")
    return "\n".join(out)
