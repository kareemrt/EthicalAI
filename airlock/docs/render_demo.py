"""Regenerate docs/demo.svg from real scanner output.

    python docs/render_demo.py
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from airlock import scan  # noqa: E402

COLOR = {"high": "#ff6b6b", "medium": "#f7c948", "low": "#56c8d8",
         "dangerous": "#ff6b6b", "suspicious": "#f7c948", "clean": "#5fd38d"}
FG, DIM, BG = "#e6e6e6", "#8b93a1", "#14161b"
CH, LH, PAD, MAXW = 8.45, 21, 20, 112


def spans(parts):
    return "".join(f'<tspan fill="{c}">{escape(t).replace(" ", "&#160;")}</tspan>' for t, c in parts)


def lines_for(path):
    r = scan(path.read_text(encoding="utf-8"), f"examples/{path.name}")
    yield [("$ ", DIM), (f"airlock scan examples/{path.name}", FG)]
    yield [(f"{r.source}  ", FG), (r.verdict.upper(), COLOR[r.verdict]),
           (f"  risk {r.score}/100  ({len(r.findings)} findings)", FG)]
    for f in r.findings:
        sev = str(f.severity)
        msg = f.message if len(f.message) < 46 else f.message[:45] + "…"
        yield [("  ", FG), (f"{sev.upper():<6}", COLOR[sev]), (f" {f'{f.line}:{f.col}':>6}  {f.rule:<27} {msg}", FG)]
        yield [(f"{'':16}└ {f.excerpt[:MAXW - 18]}", DIM)]
    yield [("", FG)]


rows = [row for name in ("product_page.html", "job_application.txt")
        for row in lines_for(ROOT / "examples" / name)][:-1]
w = int(MAXW * CH + 2 * PAD)
h = int(len(rows) * LH + 2 * PAD + 28)
body = "\n".join(f'<text x="{PAD}" y="{PAD + 40 + i * LH}">{spans(r)}</text>' for i, r in enumerate(rows))
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="airlock scan output">
<rect width="{w}" height="{h}" rx="10" fill="{BG}"/>
<circle cx="22" cy="20" r="6" fill="#ff5f57"/><circle cx="42" cy="20" r="6" fill="#febc2e"/><circle cx="62" cy="20" r="6" fill="#28c840"/>
<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="14">
{body}
</g>
</svg>
"""
(ROOT / "docs" / "demo.svg").write_text(svg, encoding="utf-8")
print(f"wrote docs/demo.svg ({len(rows)} lines)")
