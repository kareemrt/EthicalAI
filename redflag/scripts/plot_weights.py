"""Render docs/weights.svg - the learned weight of every signal (pure Python, no deps).

    python scripts/plot_weights.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "redflag" / "weights.json").read_text())
sys.path.insert(0, str(ROOT))
from redflag.signals import BY_ID  # noqa: E402

rows = sorted(data["weights"].items(), key=lambda kv: -kv[1])
W, LEFT, RIGHT, TOP, ROW, BAR = 820, 340, 70, 70, 30, 16
H = TOP + ROW * len(rows) + 40
scale = (W - LEFT - RIGHT) / max(w for _, w in rows)


def bar(x, y, w, h, r=4):
    """Bar anchored square at the baseline, 4px rounded at the data end."""
    r = min(r, w / 2)
    return (f'<path class="bar" d="M{x},{y} H{x + w - r} Q{x + w},{y} {x + w},{y + r} V{y + h - r} '
            f'Q{x + w},{y + h} {x + w - r},{y + h} H{x} Z"/>')


out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">',
       '<style>.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.bar{fill:#2a78d6}.grid{stroke:#e4e3df}'
       '@media (prefers-color-scheme:dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}.bar{fill:#3987e5}.grid{stroke:#383835}}</style>',
       f'<rect class="bg" width="{W}" height="{H}" rx="12"/>',
       '<text class="t1" x="24" y="34" font-size="17" font-weight="600">What the model learned to fear</text>',
       f'<text class="t2" x="24" y="54" font-size="13">Logistic-regression weight per signal (log-odds). '
       f'Baseline bias {data["bias"]:+.2f}: a message with no flags scores ~{100 / (1 + 2.718 ** -data["bias"]):.0f}% risk.</text>']
for i in range(0, int(max(w for _, w in rows)) + 1):
    x = LEFT + i * scale
    out.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{TOP - 6}" y2="{H - 34}" stroke-width="1"/>')
    out.append(f'<text class="t2" x="{x:.1f}" y="{H - 16}" font-size="12" text-anchor="middle">{i}</text>')
for n, (sid, w) in enumerate(rows):
    y = TOP + n * ROW
    out.append(f'<text class="t1" x="{LEFT - 12}" y="{y + 12}" font-size="13" text-anchor="end">{BY_ID[sid].label}</text>')
    out.append(bar(LEFT, y, max(w, 0) * scale, BAR))
    out.append(f'<text class="t2" x="{LEFT + max(w, 0) * scale + 8:.1f}" y="{y + 12}" font-size="12">{w:+.2f}</text>')
out.append("</svg>")
(ROOT / "docs" / "weights.svg").write_text("\n".join(out) + "\n")
print("wrote docs/weights.svg")
