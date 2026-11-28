"""Render a player's rating history as a self-contained SVG in the site's style."""

from __future__ import annotations

import math
from collections.abc import Sequence
from html import escape

from .models import HistoryPoint

WIDTH, HEIGHT = 1000, 640
LEFT, RIGHT, TOP, BOTTOM = 96, 952, 250, 560
X_TICK_STEP = 5
MIN_SPAN = 10  # rating points

BACKGROUND, CARD, TILE, BORDER, GRID = "#1f5a3e", "#1b1e24", "#22262e", "#2f343d", "#2a2f38"
TEXT, MUTED, ACCENT, UP, DOWN = "#ffffff", "#9aa3b2", "#ff7a1a", "#3fb27f", "#ef5350"

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
.empty{{font:500 18px 'Inter',Arial,sans-serif;fill:{MUTED}}}
.pt:hover{{r:7}}
</style>"""


def nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    """Round axis values (steps of 1, 2, 2.5 or 5 x 10^n) covering ``low..high``.

    Flat histories are padded to a span of MIN_SPAN so the axis keeps whole numbers.
    """
    if high - low < MIN_SPAN:
        pad = (MIN_SPAN - (high - low)) / 2
        low, high = low - pad, high + pad
    raw = (high - low) / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    first, last = math.floor(low / step) * step, math.ceil(high / step) * step
    if first == last:
        last += step
    return [first + i * step for i in range(round((last - first) / step) + 1)]


def format_number(value: float) -> str:
    return f"{value:g}" if not float(value).is_integer() else str(int(value))


def format_change(change: float) -> str:
    points = round(change)
    sign = "+" if points > 0 else "−" if points < 0 else "±"
    return f"{sign}{abs(points)}"


def _tiles(history: Sequence[HistoryPoint]) -> list[str]:
    ratings = [p.rating for p in history]
    played = len(history) - 1
    if played:
        change = ratings[-1] - ratings[-2]
        color = UP if round(change) > 0 else DOWN if round(change) < 0 else MUTED
        last = (format_change(change), color)
    else:
        last = ("—", MUTED)
    tiles = [
        ("РЕЙТИНГ", str(round(ratings[-1])), TEXT),
        ("ЛУЧШИЙ", str(round(max(ratings))), TEXT),
        ("ТУРНИРОВ", str(played), TEXT),
        ("ПОСЛЕДНИЙ ТУРНИР", *last),
    ]
    gap = 14
    width = (WIDTH - 96 - 3 * gap) / len(tiles)
    out = []
    for i, (label, value, color) in enumerate(tiles):
        x = 48 + i * (width + gap)
        out += [
            f'<rect x="{x:.1f}" y="138" width="{width:.1f}" height="74" rx="10" fill="{TILE}" stroke="{BORDER}"/>',
            f'<text x="{x + 16:.1f}" y="164" class="lab">{label}</text>',
            f'<text x="{x + 16:.1f}" y="198" class="val" fill="{color}">{value}</text>',
        ]
    return out


def _plot(history: Sequence[HistoryPoint], last_tournament: int) -> list[str]:
    ratings = [p.rating for p in history]
    ticks = nice_ticks(min(ratings), max(ratings))
    low, high = ticks[0], ticks[-1]

    def x(tournament: float) -> float:
        return LEFT + (RIGHT - LEFT) * tournament / last_tournament

    def y(rating: float) -> float:
        return BOTTOM - (BOTTOM - TOP) * (rating - low) / (high - low)

    out = [
        f'<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{ACCENT}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient></defs>'
    ]
    for value in ticks:
        out += [
            f'<line x1="{LEFT}" y1="{y(value):.1f}" x2="{RIGHT}" y2="{y(value):.1f}" stroke="{GRID}"/>',
            f'<text x="{LEFT - 14}" y="{y(value) + 5:.1f}" text-anchor="end" class="ax">{format_number(value)}</text>',
        ]
    for t in range(0, last_tournament + 1, X_TICK_STEP):
        out += [
            f'<line x1="{x(t):.1f}" y1="{BOTTOM}" x2="{x(t):.1f}" y2="{BOTTOM + 6}" stroke="{MUTED}"/>',
            f'<text class="tick-x ax" x="{x(t):.1f}" y="{BOTTOM + 26}" text-anchor="middle">{t}</text>',
        ]
    out.append(
        f'<text x="{(LEFT + RIGHT) / 2}" y="{BOTTOM + 54}" text-anchor="middle" class="axt">НОМЕР ТУРНИРА</text>'
    )

    line = " ".join(f"{x(p.tournament):.1f},{y(p.rating):.1f}" for p in history)
    first, last = history[0], history[-1]
    out += [
        f'<polygon points="{x(first.tournament):.1f},{BOTTOM} {line} {x(last.tournament):.1f},{BOTTOM}" '
        'fill="url(#fill)"/>',
        f'<polyline points="{line}" fill="none" stroke="{ACCENT}" stroke-width="3" '
        'stroke-linejoin="round" stroke-linecap="round"/>',
    ]
    for p in history:
        look = f'r="7" fill="{ACCENT}"' if p is last else f'r="4.5" fill="{CARD}" stroke="{ACCENT}" stroke-width="2.5"'
        out.append(
            f'<circle class="pt" cx="{x(p.tournament):.1f}" cy="{y(p.rating):.1f}" {look}>'
            f"<title>Турнир {p.tournament}: {format_number(p.rating)}</title></circle>"
        )

    # Current rating next to the last point: to its right when there is room,
    # otherwise above or below it, away from the incoming line.
    label = str(round(last.rating))
    tag_w = 18 + 9 * len(label)
    px, py = x(last.tournament), y(last.rating)
    if px + 14 + tag_w <= RIGHT:
        tag_x, tag_y = px + 14, py - 13
    else:
        tag_x = min(max(px - tag_w / 2, LEFT), RIGHT + 20 - tag_w)
        above = ratings[-2] <= last.rating or py + 44 > BOTTOM
        tag_y = py - 40 if above else py + 14
    out += [
        f'<rect x="{tag_x:.1f}" y="{tag_y:.1f}" width="{tag_w}" height="26" rx="6" fill="#fff"/>',
        f'<text x="{tag_x + tag_w / 2:.1f}" y="{tag_y + 18:.1f}" text-anchor="middle" class="tag">{label}</text>',
    ]
    return out


def render_chart(name: str, history: Sequence[HistoryPoint], last_tournament: int) -> str:
    """SVG chart of ``history`` on an x axis running from tournament 0 to ``last_tournament``."""
    out = [
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BACKGROUND}"/>',
        f'<rect x="20" y="20" width="{WIDTH - 40}" height="{HEIGHT - 40}" rx="16" fill="{CARD}"/>',
        f'<text x="48" y="70" class="name">{escape(name)}</text>',
        '<text x="48" y="100" class="sub">ИЗМЕНЕНИЕ РЕЙТИНГА · ЛИГА РОЗ</text>',
        '<a href="../"><rect class="back-box" x="812" y="44" width="140" height="38" rx="19"/>'
        '<text x="882" y="68" text-anchor="middle" class="back">← К рейтингу</text></a>',
        *_tiles(history),
    ]
    if len(history) > 1:
        out += _plot(history, last_tournament)
    else:
        out.append(
            f'<text x="{WIDTH / 2}" y="{(TOP + BOTTOM) / 2}" text-anchor="middle" class="empty">'
            "Ещё не играл в турнирах лиги</text>"
        )
    return (
        # The background fills the whole browser window when a chart is opened directly.
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'style="background:{BACKGROUND}" role="img" '
        f'aria-label="Рейтинг: {escape(name)}">{STYLE}{"".join(out)}</svg>\n'
    )
