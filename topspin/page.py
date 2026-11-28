"""Fill the standings table in index.html.

The page is hand-written; only the rows between the ``standings:start`` and
``standings:end`` comments are generated.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from html import escape

from .models import Player

_ROWS = re.compile(r"(<!-- standings:start[^>]*-->\n).*?(<!-- standings:end -->)", re.DOTALL)


def chart_path(player_id: int) -> str:
    return f"charts/{player_id}.svg"


def render_rows(standings: Sequence[tuple[Player, int]]) -> str:
    """Table rows for players already ordered by rating, with their displayed rating."""
    return "".join(
        f"<tr>\n<td>{place}</td>\n"
        f'<td><a href="{chart_path(player.id)}">{escape(player.name)}</a></td>\n'
        f"<td>{rating}</td>\n</tr>\n"
        for place, (player, rating) in enumerate(standings, start=1)
    )


def fill_standings(page: str, rows: str) -> str:
    if not _ROWS.search(page):
        raise ValueError("index.html has no standings:start/standings:end markers")
    return _ROWS.sub(lambda m: m.group(1) + rows + m.group(2), page, count=1)
