"""Dependency-free SVG chart of impact ratios, readable on light and dark backgrounds."""

from html import escape

from .audit import Audit

OK, ADVERSE, MUTED = "#2a9d8f", "#e76f51", "#8b949e"
ROW, LABEL_W, BAR_W, PAD = 22, 260, 360, 16


def impact_svg(audit: Audit) -> str:
    """One horizontal bar per group, grouped by dimension, with the threshold line."""
    rows: list[str] = []
    y = PAD
    for dim in audit.dimensions:
        y += 6
        rows.append(_text(PAD, y + 12, dim.name.upper(), weight=700, size=12))
        y += ROW
        for g in dim.groups:
            colour = MUTED if g.excluded else (OK if g.impact_ratio >= audit.threshold else ADVERSE)
            width = max(2.0, min(g.impact_ratio, 1.0) * BAR_W)
            x0 = PAD + LABEL_W
            rows.append(_text(x0 - 10, y + 13, g.group, anchor="end"))
            fade = ' opacity="0.45"' if g.excluded else ""
            rows.append(f'<rect x="{x0}" y="{y + 3}" width="{width:.1f}" height="{ROW - 8}" '
                        f'rx="3" fill="{colour}"{fade}/>')
            tag = "n/a (small)" if g.excluded else f"{g.impact_ratio:.2f}"
            rows.append(_text(x0 + width + 6, y + 13, tag))
            y += ROW
        y += 8

    height = y + PAD + 18
    tx = PAD + LABEL_W + audit.threshold * BAR_W
    width_total = PAD * 2 + LABEL_W + BAR_W + 90
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_total} {height}" '
        f'width="{width_total}" height="{height}" font-family="system-ui,-apple-system,Segoe UI,sans-serif">',
        f'<title>Impact ratios for "{escape(audit.outcome)}"</title>',
        *rows,
        f'<line x1="{tx:.1f}" y1="{PAD}" x2="{tx:.1f}" y2="{y}" stroke="{ADVERSE}" stroke-dasharray="4 3"/>',
        _text(tx, y + 14, f"{audit.threshold:.0%} threshold (four-fifths rule)", anchor="middle", fill=ADVERSE),
        "</svg>",
    ])


def _text(x, y, s, anchor="start", weight=400, size=12, fill=MUTED) -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{escape(str(s))}</text>')
