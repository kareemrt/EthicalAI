"""Regenerate docs/class-sizes.svg from the example dataset.

    python docs/make_figures.py

Two small multiples on one shared scale: how many records sit in classes of
each size before and after `lineup fix`. Bars on the left are people an
attacker can single out; bars on the right are people hidden in a crowd.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lineup.cli import audit  # noqa: E402

result = audit(str(ROOT / "examples" / "patients.csv"), k=5, fix=True)
panels = [("Before: raw extract", result["risk"]), ("After: lineup fix --k 5", result["after"])]

W, H, PAD, GAP = 760, 350, 56, 48
pw = (W - 2 * PAD - GAP) / 2
top, base = 116, H - 58
peak = max(max(r.size_histogram.values()) for _, r in panels)

parts = []
for p, (title, r) in enumerate(panels):
    x0 = PAD + p * (pw + GAP)
    verdict = f"k = {r.k_min} · {r.unique_pct:.0f}% unique" if r.k_min < 5 else f"k = {r.k_min} · 0% unique"
    parts.append(f'<text x="{x0}" y="{top - 62}" class="t">{title}</text>')
    parts.append(f'<text x="{x0}" y="{top - 42}" class="s">{verdict}</text>')
    parts.append(f'<line x1="{x0}" x2="{x0 + pw}" y1="{base}" y2="{base}" class="axis"/>')
    items = list(r.size_histogram.items())
    slot = pw / len(items)
    bw = slot - 14
    for i, (label, count) in enumerate(items):
        x = x0 + i * slot + 7
        h = (base - top) * count / peak
        if h:
            # 4px rounded top, square at the baseline
            rr = min(4, h, bw / 2)
            parts.append(
                f'<path class="bar" d="M{x:.1f},{base} V{base - h + rr:.1f} '
                f'Q{x:.1f},{base - h:.1f} {x + rr:.1f},{base - h:.1f} H{x + bw - rr:.1f} '
                f'Q{x + bw:.1f},{base - h:.1f} {x + bw:.1f},{base - h + rr:.1f} V{base} Z">'
                f'<title>{label}: {count:,} records</title></path>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{base - h - 6:.1f}" class="v">{count:,}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{base + 18}" class="l">{label.replace(" (unique)", "")}</text>')
    parts.append(f'<text x="{x0 + pw / 2}" y="{base + 38}" class="l">records by equivalence-class size</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
  aria-label="Records by equivalence-class size, before and after anonymization">
<style>
  .bg {{ fill: #fcfcfb; }} .bar {{ fill: #2a78d6; }} .axis {{ stroke: #c3c2b7; stroke-width: 1; }}
  text {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #0b0b0b; }}
  .t {{ font-size: 15px; font-weight: 600; }} .s {{ font-size: 12px; fill: #52514e; }}
  .v {{ font-size: 12px; text-anchor: middle; font-variant-numeric: tabular-nums; }}
  .l {{ font-size: 11px; fill: #52514e; text-anchor: middle; }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ fill: #1a1a19; }} .bar {{ fill: #3987e5; }} .axis {{ stroke: #52514e; }}
    text {{ fill: #f0efec; }} .s, .l {{ fill: #c3c2b7; }}
  }}
</style>
<rect class="bg" width="{W}" height="{H}" rx="10"/>
{chr(10).join(parts)}
</svg>
'''
(ROOT / "docs" / "class-sizes.svg").write_text(svg)
print("wrote docs/class-sizes.svg")
