"""Turn the league's data and the page sources into the published site."""

from __future__ import annotations

import shutil
from pathlib import Path

from .charts import render_chart
from .data import load_players, load_tournaments
from .page import chart_path, fill_standings, render_rows
from .rating import calculate

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "web"  # hand-written page, styles, scripts and images
OUTPUT = ROOT / "_site"


def render_pages(root: Path = ROOT) -> dict[str, str]:
    """Generated files keyed by their path inside the site: the standings page and every chart."""
    players = load_players(root / "data" / "players.csv")
    tournaments = load_tournaments(root / "data" / "tournaments")
    result = calculate(players, tournaments)
    last_tournament = tournaments[-1].number if tournaments else 0

    by_id = {p.id: p for p in players}
    # The table shows the latest history value, rounded to a whole point.
    standings = [(by_id[pid], round(result.history[pid][-1].rating)) for pid in result.standings()]

    pages = {chart_path(p.id): render_chart(p.name, result.history[p.id], last_tournament) for p in players}
    template = (root / SOURCE / "index.html").read_text(encoding="utf-8")
    pages["index.html"] = fill_standings(template, render_rows(standings))
    return pages


def build(output: Path = OUTPUT, root: Path = ROOT) -> int:
    """Write the complete site to ``output``, replacing what was there. Returns the number of charts."""
    pages = render_pages(root)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(root / SOURCE, output)
    for relative, text in pages.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return len(pages) - 1
