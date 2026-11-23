"""Tiny dependency-free SVG line charts that follow the OS light/dark theme."""

from typing import List, Optional, Sequence, Tuple

W, H = 640, 400
L, R, T, B = 60, 160, 48, 52  # margins; legend lives in the right margin
PW, PH = W - L - R, H - T - B

STYLE = """<style>
  svg{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#e4e3df;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a}
  @media (prefers-color-scheme:dark){svg{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#3a3a37;--s1:#3987e5;--s2:#d95926;--s3:#199e70}}
  text{font:12px system-ui,-apple-system,Segoe UI,sans-serif;fill:var(--ink2)}
  .t{font-size:15px;font-weight:600;fill:var(--ink)} .k{fill:var(--ink)}
  .g{stroke:var(--grid);stroke-width:1} .ref{stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:5 4;fill:none}
</style>"""

Series = Tuple[str, str, Sequence[Tuple[float, float]]]  # label, css var, points


def _x(v: float) -> float:
    return L + v * PW


def _y(v: float, lo: float = 0.0) -> float:
    return T + (1 - (v - lo) / (1 - lo)) * PH


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line_chart(title: str, xlabel: str, ylabel: str, series: Sequence[Series],
               diagonal: bool = False, hline: Optional[Tuple[float, str]] = None,
               marker: Optional[Tuple[float, float, str]] = None, dots: bool = True,
               y_min: float = 0.0) -> str:
    """X spans [0, 1], Y spans [y_min, 1]. Returns a standalone SVG document."""
    def y(v: float) -> float:
        return _y(v, y_min)

    o: List[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                    f'width="{W}" height="{H}" role="img" aria-label="{_esc(title)}">', STYLE,
                    f'<rect width="{W}" height="{H}" rx="8" fill="var(--bg)"/>',
                    f'<text class="t" x="{L}" y="28">{_esc(title)}</text>']
    for i in range(6):  # grid + tick labels every 20%
        v, yv = i / 5, y_min + (1 - y_min) * i / 5
        o.append(f'<line class="g" x1="{L}" x2="{L + PW}" y1="{y(yv):.1f}" y2="{y(yv):.1f}"/>')
        o.append(f'<text x="{L - 8}" y="{y(yv) + 4:.1f}" text-anchor="end">{round(yv * 100)}%</text>')
        o.append(f'<text x="{_x(v):.1f}" y="{T + PH + 18}" text-anchor="middle">{round(v * 100)}%</text>')
    o.append(f'<text x="{L + PW / 2}" y="{H - 12}" text-anchor="middle">{_esc(xlabel)}</text>')
    o.append(f'<text transform="translate(16 {T + PH / 2}) rotate(-90)" text-anchor="middle">'
             f'{_esc(ylabel)}</text>')

    legend = []
    if diagonal:
        o.append(f'<line class="ref" x1="{_x(0)}" y1="{y(0)}" x2="{_x(1)}" y2="{y(1)}"/>')
        legend.append(("Perfect calibration", None))
    if hline:
        v, label = hline
        o.append(f'<line class="ref" x1="{_x(0)}" x2="{_x(1)}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        legend.append((label, None))

    for label, var, pts in series:
        if not pts:
            continue
        path = " ".join(f"{'M' if i == 0 else 'L'}{_x(px):.1f},{y(py):.1f}" for i, (px, py) in enumerate(pts))
        o.append(f'<path d="{path}" fill="none" stroke="var({var})" stroke-width="2" '
                 'stroke-linejoin="round" stroke-linecap="round"/>')
        if dots:
            o += [f'<circle cx="{_x(px):.1f}" cy="{y(py):.1f}" r="4" fill="var({var})" '
                  f'stroke="var(--bg)" stroke-width="2"/>' for px, py in pts]
        legend.append((label, var))

    if marker:
        mx, my, label = marker
        o.append(f'<circle cx="{_x(mx):.1f}" cy="{y(my):.1f}" r="7" fill="none" stroke="var(--ink)" stroke-width="2"/>')
        o.append(f'<text class="k" x="{_x(mx) - 10:.1f}" y="{y(my) + 26:.1f}" text-anchor="end">{_esc(label)}</text>')

    lx, ly = L + PW + 18, T + 8
    for i, (label, var) in enumerate(legend):
        yy = ly + i * 22
        if var:
            o.append(f'<line x1="{lx}" x2="{lx + 18}" y1="{yy}" y2="{yy}" stroke="var({var})" stroke-width="2"/>'
                     f'<circle cx="{lx + 9}" cy="{yy}" r="4" fill="var({var})"/>')
        else:
            o.append(f'<line class="ref" x1="{lx}" x2="{lx + 18}" y1="{yy}" y2="{yy}"/>')
        o.append(f'<text class="k" x="{lx + 26}" y="{yy + 4}">{_esc(label)}</text>')
    o.append("</svg>")
    return "\n".join(o)
