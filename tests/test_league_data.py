"""The real league data: well-formed, consistent, and scored exactly as the original code scored it."""

import json
from pathlib import Path

import pytest

from topspin.build import ROOT
from topspin.data import load_players, load_tournaments, tournament_names
from topspin.rating import calculate, parse_score

DATA = ROOT / "data"
LEGACY = json.loads((Path(__file__).parent / "data" / "legacy_results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def players():
    return load_players(DATA / "players.csv")


@pytest.fixture(scope="module")
def tournaments():
    return load_tournaments(DATA / "tournaments")


@pytest.fixture(scope="module")
def result(players, tournaments):
    return calculate(players, tournaments)


def test_tournament_files_use_canonical_player_names(players):
    names = {p.id: p.name for p in players}
    for path in sorted((DATA / "tournaments").glob("*.csv")):
        for player_id, name in tournament_names(path).items():
            assert names.get(player_id) == name, f"{path.name}: player {player_id} is listed as {name!r}"


def test_matches_are_valid(players, tournaments):
    ids = {p.id for p in players}
    for t in tournaments:
        assert t.participants <= ids, f"tournament {t.number}: unknown players"
        for m in t.matches:
            assert m.first != m.second, f"tournament {t.number}: a player plays themselves"
            parse_score(m.score)
        assert {t.player_at(place) for place in (1, 2, 3)} <= t.participants


def test_history_matches_the_original_implementation(result):
    for player_id, points in result.history.items():
        expected = [tuple(p) for p in LEGACY["history"][str(player_id)]]
        assert [(p.tournament, p.rating) for p in points] == expected, f"player {player_id}"


def test_ratings_and_standings_match_the_original_implementation(result):
    assert result.ratings == pytest.approx({int(k): v for k, v in LEGACY["ratings"].items()}, abs=1e-9)
    assert result.standings() == LEGACY["standings"]
