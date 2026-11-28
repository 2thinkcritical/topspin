"""The maintainer's documented workflow: append data, pass checks, publish a new site."""

import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from topspin.build import ROOT, build
from topspin.data import MATCH_FIELDS, load_players, load_tournaments


@pytest.mark.parametrize("register_player", [True, False])
def test_next_tournament_checks_accept_registered_players_and_reject_unknown_ones(
    tmp_path: Path, register_player: bool
) -> None:
    source = tmp_path / "source"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".coverage", "_site"
        ),
    )
    players = load_players(source / "data" / "players.csv")
    names = {p.id: p.name for p in players}
    new_id = max(names) + 1
    next_tournament = len(load_tournaments(source / "data" / "tournaments")) + 1
    if register_player:
        with (source / "data" / "players.csv").open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow((new_id, "New Player", 100))
    with (source / "data" / "tournaments" / f"{next_tournament:02}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(MATCH_FIELDS)
        writer.writerows(
            [
                (new_id, 1, "New Player", names[1], "3:1", 1, 2),
                (1, 2, names[1], names[2], "3:1", 2, 3),
                (new_id, 2, "New Player", names[2], "3:0", 1, 3),
            ]
        )
    checks = subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "tests/test_league_data.py", "-q"],
        cwd=source,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if not register_player:
        assert checks.returncode != 0
        assert "unknown players" in checks.stdout
        return
    assert checks.returncode == 0, checks.stdout + checks.stderr
    output = tmp_path / "site"
    assert build(output, root=source) == len(players) + 1
    assert "New Player" in (output / "index.html").read_text(encoding="utf-8")
    chart = (output / "charts" / f"{new_id}.svg").read_text(encoding="utf-8")
    assert f"Турнир {next_tournament}:" in chart
