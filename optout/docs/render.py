"""Render optout's coloured terminal output as an SVG for the README.

    python docs/render.py examples/partial docs/report-partial.svg
"""

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optout import audit, report  # noqa: E402
from optout.site import open_site  # noqa: E402

COLORS = {"31": "#ff6b6b", "32": "#51cf66", "33": "#fcc419", "2": "#7d8590", "1": "#f0f6fc"}
LINE, CHAR, PAD = 19, 8.4, 20


def to_svg(ansi: str, title: str) -> str:
    lines = ansi.rstrip("\n").split("\n")
    width = int(max(len(re.sub(r"\033\[\d+m", "", l)) for l in lines) * CHAR + 2 * PAD)
    height = len(lines) * LINE + 2 * PAD + 28
    rows = []
    for i, line in enumerate(lines):
        spans, style = [], None
        for part in re.split(r"(\033\[\d+m)", line):
            if m := re.fullmatch(r"\033\[(\d+)m", part):
                style = None if m[1] == "0" else m[1]
            elif part:
                attrs = f' fill="{COLORS[style]}"' if style else ""
                attrs += ' font-weight="bold"' if style == "1" else ""
                spans.append(f"<tspan{attrs}>{html.escape(part)}</tspan>")
        rows.append(f'<text x="{PAD}" y="{PAD + 40 + i * LINE}" xml:space="preserve">{"".join(spans)}</text>')
    dots = "".join(f'<circle cx="{20 + 18 * i}" cy="18" r="6" fill="{c}"/>'
                   for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="14" fill="#c9d1d9">'
            f'<rect width="100%" height="100%" rx="10" fill="#0d1117"/>{dots}'
            f'<text x="{width / 2}" y="23" text-anchor="middle" fill="#7d8590" font-size="12">{html.escape(title)}</text>'
            + "".join(rows) + "</svg>\n")


if __name__ == "__main__":
    target, out = sys.argv[1], sys.argv[2]
    text = report.text(audit.run(open_site(target)), color=True)
    Path(out).write_text(to_svg(text, f"$ optout check {target}"))
