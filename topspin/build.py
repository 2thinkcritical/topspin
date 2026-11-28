"""Turn the league's data into the published site files."""

from __future__ import annotations

from pathlib import Path

from .charts import render_chart
from .data import load_players, load_tournaments
from .page import chart_path, fill_standings, render_rows
from .rating import calculate

ROOT = Path(__file__).resolve().parent.parent


def render_site(root: Path = ROOT) -> dict[Path, str]:
    """Every generated file, keyed by its path under ``root``."""
    players = load_players(root / "data" / "players.csv")
    tournaments = load_tournaments(root / "data" / "tournaments")
    result = calculate(players, tournaments)
    last_tournament = tournaments[-1].number if tournaments else 0

    by_id = {p.id: p for p in players}
    # The table shows the latest published history value, rounded to a whole point.
    standings = [(by_id[pid], round(result.history[pid][-1].rating)) for pid in result.standings()]

    files = {root / chart_path(p.id): render_chart(p.name, result.history[p.id], last_tournament) for p in players}
    index = root / "index.html"
    files[index] = fill_standings(index.read_text(encoding="utf-8"), render_rows(standings))
    return files


def stale_files(root: Path = ROOT) -> list[Path]:
    """Generated files that are missing, outdated or no longer produced."""
    files = render_site(root)
    stale = [p for p, text in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
    stale += [p for p in (root / "charts").glob("*.svg") if p not in files]
    return sorted(stale)


def build(root: Path = ROOT) -> int:
    """Write the site and remove charts of players who are no longer listed."""
    files = render_site(root)
    (root / "charts").mkdir(exist_ok=True)
    for path in (root / "charts").glob("*.svg"):
        if path not in files:
            path.unlink()
    for path, text in files.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
    return len(files) - 1
