"""Dependency-free SVG chart of impact ratios with the four-fifths line."""

from __future__ import annotations

from html import escape

from .metrics import Audit, Status

# Status colors (fixed). Each bar is also labelled with an icon + word, so
# color never carries meaning alone.
COLOR = {Status.OK: "#0ca30c", Status.WATCH: "#fab219", Status.REVIEW: "#ec835a",
         Status.ADVERSE: "#d03b3b", Status.EXCLUDED: "#c3c2b7"}

STYLE = """
.bg{fill:#fcfcfb}.t{fill:#0b0b0b}.s{fill:#52514e}.grid{stroke:#e1e0d9}.axis{stroke:#c3c2b7}.thr{stroke:#0b0b0b}.v{paint-order:stroke;stroke:#fcfcfb;stroke-width:4px}
text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}
@media (prefers-color-scheme:dark){.bg{fill:#1a1a19}.t{fill:#f0efec}.s{fill:#c3c2b7}.grid{stroke:#2c2c2a}.axis{stroke:#383835}.thr{stroke:#f0efec}.v{stroke:#1a1a19}}
"""


def svg(audits: list[Audit], width: int = 760) -> str:
    label_w, status_w, row_h, bar_h, pad, value_w = 210, 96, 26, 14, 20, 40
    plot_w = width - label_w - status_w - value_w - 2 * pad
    scale = lambda r: label_w + pad + plot_w * min(r, 1.0)

    body, y = [], 56
    for a in audits:
        body.append(f'<text class="t" x="{pad}" y="{y}" font-size="13" font-weight="600">{escape(a.dimension)}</text>')
        y += 12
        for g in a.groups:
            cy = y + row_h / 2
            body.append(f'<text class="s" x="{label_w + pad - 10}" y="{cy + 4}" font-size="12" text-anchor="end">'
                        f'{escape(g.name)}</text>')
            if g.impact_ratio is not None:
                x0, x1 = scale(0), scale(g.impact_ratio)
                w = max(x1 - x0, 2)
                body.append(f'<path fill="{COLOR[g.status]}" d="M{x0},{cy - bar_h/2}h{w - 4}a4,4 0 0 1 4,4'
                            f'v{bar_h - 8}a4,4 0 0 1 -4,4h{-(w - 4)}z"><title>{escape(g.name)}: impact ratio '
                            f'{g.impact_ratio:.3f}, rate {g.rate:.1%}, n={g.n}</title></path>')
                body.append(f'<text class="s v" x="{x1 + 6}" y="{cy + 4}" font-size="11">{g.impact_ratio:.2f}</text>')
            body.append(f'<text class="t" x="{width - pad - status_w}" y="{cy + 4}" font-size="12">'
                        f'<tspan fill="{COLOR[g.status]}" font-weight="700">{g.status.icon}</tspan> {g.status.value}</text>')
            y += row_h
        y += 18

    top, bottom = 40, y - 10
    thr = audits[0].threshold
    grid = "".join(
        f'<line class="grid" x1="{scale(v)}" x2="{scale(v)}" y1="{top}" y2="{bottom}"/>'
        f'<text class="s" x="{scale(v)}" y="{bottom + 16}" font-size="11" text-anchor="middle">{v:.1f}</text>'
        for v in (0.2, 0.4, 0.6, 1.0))
    threshold = (f'<line class="thr" x1="{scale(thr)}" x2="{scale(thr)}" y1="{top}" y2="{bottom}" stroke-width="1.5" '
                 f'stroke-dasharray="4 3"/><text class="t" x="{scale(thr)}" y="{bottom + 16}" font-size="11" '
                 f'text-anchor="middle" font-weight="600">{thr} · four-fifths</text>')
    height = bottom + 34
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="Impact ratio by category"><style>{STYLE}</style>'
            f'<rect class="bg" width="100%" height="100%" rx="8"/>'
            f'<text class="t" x="{pad}" y="28" font-size="15" font-weight="700">Impact ratio by category</text>'
            f'<text class="s" x="{width - pad}" y="28" font-size="11" text-anchor="end">rate ÷ highest rate · '
            f'1.0 = parity</text>'
            f'<line class="axis" x1="{scale(0)}" x2="{scale(0)}" y1="{top}" y2="{bottom}"/>'
            f'{grid}{threshold}{"".join(body)}</svg>\n')
