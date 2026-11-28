"""Build player rating charts (charts/<id>.svg) from data/ratings.json.

Usage (from the repository root):

    python3 scripts/build_charts.py

data/ratings.json maps a player id (the chart file name) to the player's name
and rating history: a list of [tournament number, rating] pairs in order.
Tournament 0 is the starting rating. After a new tournament, append its
[number, rating] pair to each player who played and run this script again.
"""

from html import escape
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ratings.json"
CHARTS = ROOT / "charts"

W, H = 1000, 640
LEFT, RIGHT, TOP, BOTTOM = 96, 952, 250, 560
TICK_STEP = 5

BG, CARD, TILE, BORDER, GRID = "#1f5a3e", "#1b1e24", "#22262e", "#2f343d", "#2a2f38"
TEXT, MUTED, ORANGE, GREEN, RED = "#ffffff", "#9aa3b2", "#ff7a1a", "#3fb27f", "#ef5350"

STYLE = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@600;700&amp;family=Inter:wght@400;500;600&amp;display=swap');
.name{{font:700 40px 'Oswald','Arial Narrow',sans-serif;fill:{TEXT};text-transform:uppercase;letter-spacing:2px}}
.sub{{font:500 14px 'Inter',Arial,sans-serif;fill:{MUTED};letter-spacing:3px}}
.back{{font:600 14px 'Inter',Arial,sans-serif;fill:{TEXT}}}
.back-box{{fill:none;stroke:rgba(255,255,255,.45);stroke-width:1.5}}
a:hover .back-box{{fill:#229ed9;stroke:#229ed9}}
.lab{{font:500 11px 'Inter',Arial,sans-serif;fill:{MUTED};letter-spacing:1.5px}}
.val{{font:700 28px 'Oswald','Arial Narrow',sans-serif}}
.ax{{font:500 14px 'Inter',Arial,sans-serif;fill:{MUTED}}}
.axt{{font:500 12px 'Inter',Arial,sans-serif;fill:{MUTED};letter-spacing:2px}}
.tag{{font:600 14px 'Inter',Arial,sans-serif;fill:{CARD}}}
.pt:hover{{r:7}}
</style>"""


def nice_ticks(lo, hi, count=5):
    """Round axis values that cover lo..hi."""
    raw = max(hi - lo, 1) / count
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    first, last = math.floor(lo / step) * step, math.ceil(hi / step) * step
    if first == last:
        last += step
    n = round((last - first) / step)
    return [first + i * step for i in range(n + 1)]


def num(v):
    """Rating as written in the data: whole numbers without a decimal point."""
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def signed(d):
    d = round(d)
    return ("+" if d > 0 else "−" if d < 0 else "±") + str(abs(d))


def chart(name, history, t_max):
    values = [v for _, v in history]
    cur = values[-1]
    delta = cur - values[-2] if len(values) > 1 else 0
    played = sum(1 for t, _ in history if t > 0)
    ticks = nice_ticks(min(values), max(values))
    lo, hi = ticks[0], ticks[-1]

    def x(t):
        return LEFT + (RIGHT - LEFT) * t / t_max

    def y(v):
        return BOTTOM - (BOTTOM - TOP) * (v - lo) / (hi - lo)

    out = [
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<rect x="20" y="20" width="{W - 40}" height="{H - 40}" rx="16" fill="{CARD}"/>',
        f'<text x="48" y="70" class="name">{escape(name)}</text>',
        '<text x="48" y="100" class="sub">ИЗМЕНЕНИЕ РЕЙТИНГА · ЛИГА РОЗ</text>',
        '<a href="../"><rect class="back-box" x="812" y="44" width="140" height="38" rx="19"/>'
        '<text x="882" y="68" text-anchor="middle" class="back">← К рейтингу</text></a>',
    ]

    delta_color = GREEN if round(delta) > 0 else RED if round(delta) < 0 else MUTED
    tiles = [("РЕЙТИНГ", num(round(cur)), TEXT), ("ЛУЧШИЙ", num(round(max(values))), TEXT),
             ("ТУРНИРОВ", str(played), TEXT), ("ПОСЛЕДНИЙ ТУРНИР", signed(delta), delta_color)]
    gap = 14
    tile_w = (W - 96 - 3 * gap) / 4
    for i, (label, value, color) in enumerate(tiles):
        tx = 48 + i * (tile_w + gap)
        out.append(f'<rect x="{tx:.1f}" y="138" width="{tile_w:.1f}" height="74" rx="10" fill="{TILE}" stroke="{BORDER}"/>')
        out.append(f'<text x="{tx + 16:.1f}" y="164" class="lab">{label}</text>')
        out.append(f'<text x="{tx + 16:.1f}" y="198" class="val" fill="{color}">{value}</text>')

    out.append(f'<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0" stop-color="{ORANGE}" stop-opacity=".35"/>'
               f'<stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></linearGradient></defs>')
    for v in ticks:
        out.append(f'<line x1="{LEFT}" y1="{y(v):.1f}" x2="{RIGHT}" y2="{y(v):.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{LEFT - 14}" y="{y(v) + 5:.1f}" text-anchor="end" class="ax">{num(v)}</text>')
    for t in range(0, t_max + 1, TICK_STEP):
        out.append(f'<line x1="{x(t):.1f}" y1="{BOTTOM}" x2="{x(t):.1f}" y2="{BOTTOM + 6}" stroke="{MUTED}"/>')
        out.append(f'<text class="tick-x ax" x="{x(t):.1f}" y="{BOTTOM + 26}" text-anchor="middle">{t}</text>')
    out.append(f'<text x="{(LEFT + RIGHT) / 2}" y="{BOTTOM + 54}" text-anchor="middle" class="axt">НОМЕР ТУРНИРА</text>')

    line = " ".join(f"{x(t):.1f},{y(v):.1f}" for t, v in history)
    out.append(f'<polygon points="{x(history[0][0]):.1f},{BOTTOM} {line} {x(history[-1][0]):.1f},{BOTTOM}" fill="url(#fill)"/>')
    out.append(f'<polyline points="{line}" fill="none" stroke="{ORANGE}" stroke-width="3" '
               'stroke-linejoin="round" stroke-linecap="round"/>')
    for i, (t, v) in enumerate(history):
        last = i == len(history) - 1
        style = f'r="7" fill="{ORANGE}"' if last else f'r="4.5" fill="{CARD}" stroke="{ORANGE}" stroke-width="2.5"'
        out.append(f'<circle class="pt" cx="{x(t):.1f}" cy="{y(v):.1f}" {style}><title>Турнир {t}: {num(v)}</title></circle>')

    # Подпись текущего рейтинга у последней точки.
    t, v = history[-1]
    label = num(round(v))
    tag_w = 18 + 9 * len(label)
    prev = values[-2] if len(values) > 1 else v
    if x(t) + 14 + tag_w <= RIGHT:  # есть место справа от точки
        tag_x, tag_y = x(t) + 14, y(v) - 13
    else:  # над точкой, если линия приходит снизу, иначе под ней
        tag_x = min(max(x(t) - tag_w / 2, LEFT), RIGHT + 20 - tag_w)
        above = prev <= v or y(v) + 44 > BOTTOM
        tag_y = y(v) - 40 if above else y(v) + 14
    out.append(f'<rect x="{tag_x:.1f}" y="{tag_y:.1f}" width="{tag_w}" height="26" rx="6" fill="#fff"/>')
    out.append(f'<text x="{tag_x + tag_w / 2:.1f}" y="{tag_y + 18:.1f}" text-anchor="middle" class="tag">{label}</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Рейтинг: {escape(name)}">{STYLE}' + "".join(out) + "</svg>\n")


def main():
    players = json.loads(DATA.read_text(encoding="utf-8"))
    t_max = max(t for p in players.values() for t, _ in p["history"])
    for pid, p in players.items():
        (CHARTS / f"{pid}.svg").write_text(chart(p["name"], p["history"], t_max), encoding="utf-8")
    print(f"Built {len(players)} charts.")


if __name__ == "__main__":
    main()
