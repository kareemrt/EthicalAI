"""Render impact ratios as a self-contained SVG bar chart (no plotting libs)."""

from __future__ import annotations

from html import escape

from .metrics import Audit

OK, BAD, MUTED, INK, SUB, GRID, BG = "#2f9e6b", "#d6453d", "#b8bcc4", "#1f2328", "#656d76", "#e4e7eb", "#ffffff"


def to_svg(a: Audit, width: int = 720) -> str:
    label_w, value_w, row_h, head_h, pad = 230, 64, 26, 34, 24
    plot_w = width - label_w - value_w - 2 * pad
    x0 = pad + label_w

    def x(v: float) -> float:
        return x0 + min(v, 1.0) * plot_w

    body, y = [], pad + 34
    for attr in a.attributes:
        body.append(f'<text x="{pad}" y="{y + 18}" class="h">{escape(attr.attribute)}</text>')
        y += head_h
        for g in attr.groups:
            ir = None if g.excluded else g.impact_ratio
            color = MUTED if ir is None else BAD if ir < a.threshold else OK
            body.append(f'<text x="{x0 - 10}" y="{y + 17}" class="l" text-anchor="end">'
                        f'{escape(g.group)}</text>')
            body.append(f'<rect x="{x0}" y="{y + 5}" width="{plot_w}" height="{row_h - 10}" '
                        f'rx="3" fill="{GRID}" opacity=".45"/>')
            if ir is not None:
                body.append(f'<rect x="{x0}" y="{y + 5}" width="{x(ir) - x0:.1f}" '
                            f'height="{row_h - 10}" rx="3" fill="{color}"/>')
            txt = "small n" if g.excluded else f"{ir:.2f}" if ir is not None else "—"
            body.append(f'<text x="{x0 + plot_w + 8}" y="{y + 17}" class="v" fill="{color}">{txt}</text>')
            y += row_h
        y += 8

    height = y + pad
    tx = x(a.threshold)
    verdict = ("PASS", OK) if a.passed else (f"{len(a.flagged())} group(s) flagged", BAD)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<style>.t{{font-size:16px;font-weight:600;fill:{INK}}}.h{{font-size:13px;font-weight:600;fill:{INK}}}.l{{font-size:12px;fill:{INK}}}.v{{font-size:12px;font-weight:600}}.s{{font-size:11px;fill:{SUB}}}</style>
<rect width="100%" height="100%" rx="10" fill="{BG}"/>
<text x="{pad}" y="{pad + 8}" class="t">Impact ratio by group · {escape(a.outcome)}</text>
<text x="{width - pad}" y="{pad + 8}" class="v" text-anchor="end" fill="{verdict[1]}">{verdict[0]}</text>
{chr(10).join(body)}
<line x1="{tx:.1f}" x2="{tx:.1f}" y1="{pad + 40}" y2="{height - pad}" stroke="{BAD}" stroke-width="1.5" stroke-dasharray="4 3"/>
<text x="{tx + 4:.1f}" y="{pad + 34}" class="s">{a.threshold:.2f} threshold</text>
</svg>
"""
