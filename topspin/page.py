"""Fill the standings table of web/index.html, which marks its place with ``<!-- standings -->``."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from .models import Player

PLACEHOLDER = "<!-- standings -->"


def chart_path(player_id: int) -> str:
    return f"charts/{player_id}.svg"


def render_rows(standings: Sequence[tuple[Player, int]]) -> str:
    """Table rows for players already ordered by rating, with their displayed rating."""
    return "\n".join(
        f'      <tr><td>{place}</td><td><a href="{chart_path(player.id)}">{escape(player.name)}</a></td>'
        f"<td>{rating}</td></tr>"
        for place, (player, rating) in enumerate(standings, start=1)
    )


def fill_standings(template: str, rows: str) -> str:
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"The page template must contain {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, rows)
