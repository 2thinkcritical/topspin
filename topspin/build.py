"""Turn the league's data and the page sources into the published site."""

from __future__ import annotations

import shutil
from contextlib import ExitStack
from pathlib import Path
from tempfile import mkdtemp

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
    if output.is_symlink():
        raise ValueError(f"{output}: output must not be a symbolic link")
    output, root = output.resolve(), root.resolve()
    protected = [
        (root / name).resolve() for name in (SOURCE, "data", "topspin", "tests", "docs", ".git", ".github", ".venv")
    ]
    if root.is_relative_to(output) or any(
        output.is_relative_to(source) or source.is_relative_to(output) for source in protected
    ):
        raise ValueError(f"{output}: output must not replace or overlap source directories")
    if output.exists() and not output.is_dir():
        raise ValueError(f"{output}: output must be a directory")
    pages = render_pages(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage on the same filesystem; a failed copy/write leaves the last site untouched.
    temporary = Path(mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    staging, backup = temporary / "site", temporary / "previous"
    with ExitStack() as cleanup:
        cleanup.callback(shutil.rmtree, temporary)
        shutil.copytree(root / SOURCE, staging)
        for relative, text in pages.items():
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        if output.exists():
            output.replace(backup)
        try:
            staging.replace(output)
        except OSError:
            if backup.exists():
                try:
                    backup.replace(output)
                except OSError as error:
                    cleanup.pop_all()  # Keep the staged files and previous site for manual recovery.
                    raise OSError(f"Could not restore previous site; backup kept at {backup}") from error
            raise
    return len(pages) - 1
