"""Dependency-free SVG chart: impact ratio per group with the four-fifths line."""
from __future__ import annotations

from html import escape

from .metrics import Audit

OK, BAD, REF, INK, MUTED, GRID, BG = "#2f9e77", "#d9534f", "#4c6ef5", "#1f2933", "#6b7785", "#e4e7eb", "#ffffff"


def impact_svg(audits: list[Audit], width: int = 720) -> str:
    label_w, pad, bar_h, gap, head = 190, 24, 22, 8, 34
    plot_w = width - label_w - pad * 2 - 56
    rows: list[str] = []
    y = pad
    for audit in audits:
        rows.append(f'<text x="{pad}" y="{y + 16}" font-weight="600" font-size="14" fill="{INK}">'
                    f'{escape(audit.attribute.replace("*", " × "))}</text>')
        y += head
        for g in audit.groups:
            ratio = g.impact_ratio or 0.0
            colour = REF if g.name == audit.reference else (BAD if "adverse-impact" in g.flags else OK)
            w = max(2.0, min(ratio, 1.0) * plot_w)
            x0 = pad + label_w
            rows.append(
                f'<text x="{x0 - 10}" y="{y + bar_h * 0.7}" text-anchor="end" font-size="12" fill="{INK}">'
                f'{escape(g.name)} <tspan fill="{MUTED}">n={g.n}</tspan></text>'
                f'<rect x="{x0}" y="{y}" width="{plot_w}" height="{bar_h}" rx="4" fill="{GRID}"/>'
                f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="4" fill="{colour}"/>'
                f'<text x="{x0 + plot_w + 8}" y="{y + bar_h * 0.7}" font-size="12" '
                f'font-weight="600" fill="{colour}">{ratio:.2f}</text>'
            )
            y += bar_h + gap
        y += gap * 2
    top, bottom = pad + head - 6, y - gap * 2
    xt = pad + label_w + audits[0].threshold * plot_w if audits else 0
    rows.append(f'<line x1="{xt:.1f}" y1="{top}" x2="{xt:.1f}" y2="{bottom}" stroke="{INK}" '
                f'stroke-width="1.5" stroke-dasharray="4 4"/>'
                f'<text x="{xt:.1f}" y="{bottom + 16}" text-anchor="middle" font-size="11" fill="{MUTED}">'
                f'four-fifths line ({audits[0].threshold:g})</text>' if audits else "")
    legend_y = bottom + 40
    legend = "".join(
        f'<rect x="{pad + i * 150}" y="{legend_y - 10}" width="12" height="12" rx="3" fill="{c}"/>'
        f'<text x="{pad + i * 150 + 18}" y="{legend_y}" font-size="12" fill="{INK}">{t}</text>'
        for i, (c, t) in enumerate([(REF, "reference group"), (OK, "within threshold"), (BAD, "adverse impact")])
    )
    height = legend_y + pad
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" '
            f'role="img" aria-label="Impact ratio by group">'
            f'<rect width="100%" height="100%" rx="12" fill="{BG}" stroke="{GRID}"/>'
            + "".join(rows) + legend + "</svg>\n")
