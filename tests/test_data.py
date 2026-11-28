"""Loading and validating the CSV files."""

from pathlib import Path

import pytest

from topspin.data import MATCH_FIELDS, PLAYER_FIELDS, load_players, load_tournament, load_tournaments
from topspin.models import Match, Player, Tournament
from topspin.page import fill_standings
from topspin.rating import calculate

PLAYERS_HEADER = ",".join(PLAYER_FIELDS)
MATCHES_HEADER = ",".join(MATCH_FIELDS)


def _write(path: Path, *lines: str) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_players(tmp_path: Path) -> None:
    path = _write(tmp_path / "players.csv", PLAYERS_HEADER, "1, Иванов Иван ,175", "2,Петров Пётр,150.5")
    players = load_players(path)
    assert [(p.id, p.name, p.initial_rating) for p in players] == [(1, "Иванов Иван", 175), (2, "Петров Пётр", 150.5)]


def test_load_players_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = _write(tmp_path / "players.csv", PLAYERS_HEADER, "1,A,100", "1,B,100")
    with pytest.raises(ValueError, match="duplicate player ids"):
        load_players(path)


def test_columns_are_checked(tmp_path: Path) -> None:
    path = _write(tmp_path / "players.csv", "id,name,telegram,rating", "1,A,a,100")
    with pytest.raises(ValueError, match="expected columns"):
        load_players(path)


def test_load_tournament_takes_its_number_from_the_file_name(tmp_path: Path) -> None:
    path = _write(tmp_path / "07.csv", MATCHES_HEADER, "1,2,A,B,3:1,1,2")
    assert load_tournament(path) == Tournament(7, (Match(1, 2, "3:1", 1, 2),))


@pytest.mark.parametrize(
    ("rows", "message"),
    [((), "no matches"), (("1,1,A,A,3:0,1,2",), "paired with themselves")],
)
def test_load_tournament_rejects_invalid_files(tmp_path: Path, rows: tuple[str, ...], message: str) -> None:
    path = _write(tmp_path / "01.csv", MATCHES_HEADER, *rows)
    with pytest.raises(ValueError, match=message):
        load_tournament(path)


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_player_places_are_rejected_in_any_row_order(tmp_path: Path, reverse: bool) -> None:
    rows = ("1,2,A,B,3:1,1,2", "3,1,C,A,0:3,3,4")
    path = _write(tmp_path / "1.csv", MATCHES_HEADER, *(rows[::-1] if reverse else rows))
    with pytest.raises(ValueError, match=r"1.csv: player 1.*conflicting places"):
        load_tournament(path)


@pytest.mark.parametrize(("first_place", "second_place"), [(0, 2), (1, -1)])
def test_places_must_be_positive(tmp_path: Path, first_place: int, second_place: int) -> None:
    path = _write(tmp_path / "1.csv", MATCHES_HEADER, f"1,2,A,B,3:1,{first_place},{second_place}")
    with pytest.raises(ValueError, match=r"1.csv: player .*place must be positive"):
        load_tournament(path)


@pytest.mark.parametrize("place", [1, 2, 3])
def test_podium_places_cannot_be_shared(tmp_path: Path, place: int) -> None:
    path = _write(tmp_path / "1.csv", MATCHES_HEADER, f"1,2,A,B,3:1,{place},{place}")
    with pytest.raises(ValueError, match=rf"1.csv: podium place {place}.*multiple players"):
        load_tournament(path)


def test_bonus_sized_tournament_requires_all_podium_places(tmp_path: Path) -> None:
    rows = [f"{i},{i + 1},A,B,3:0,{i},{i + 1}" for i in range(1, 16, 2)]
    rows[1] = "3,4,A,B,3:0,4,4"
    path = _write(tmp_path / "1.csv", MATCHES_HEADER, *rows)
    with pytest.raises(ValueError, match=r"1.csv: missing podium places.*3"):
        load_tournament(path)


def test_valid_csv_row_order_preserves_ratings_and_allows_nonpodium_ties(tmp_path: Path) -> None:
    rows = [f"{i},{i + 1},A,B,3:0,{i},{i + 1}" for i in range(1, 16, 2)]
    rows[-1] = "15,16,A,B,3:0,15,15"
    rows.append("1,3,A,B,1:3,1,3")
    path = tmp_path / "1.csv"
    players = [Player(i, str(i), 200) for i in range(1, 17)]
    original = calculate(players, [load_tournament(_write(path, MATCHES_HEADER, *rows))])
    reordered = calculate(players, [load_tournament(_write(path, MATCHES_HEADER, *reversed(rows)))])
    assert original == reordered
    assert {pid: original.ratings[pid] for pid in (1, 2, 3, 4)} == {1: 205, 2: 193, 3: 222, 4: 190}


def test_real_league_tournament_places_are_valid() -> None:
    tournaments = load_tournaments(Path(__file__).parent.parent / "data" / "tournaments")
    assert len(tournaments) >= 37


def test_tournaments_must_be_numbered_without_gaps(tmp_path: Path) -> None:
    for number in (1, 3):
        _write(tmp_path / f"{number:02d}.csv", MATCHES_HEADER, "1,2,A,B,3:1,1,2")
    with pytest.raises(ValueError, match="without gaps"):
        load_tournaments(tmp_path)


def test_player_at_requires_the_place_to_exist() -> None:
    tournament = Tournament(1, (Match(1, 2, "3:1", 1, 2),))
    assert tournament.player_at(2) == 2
    with pytest.raises(ValueError, match="no player in place 3"):
        tournament.player_at(3)


def test_page_template_needs_exactly_one_placeholder() -> None:
    with pytest.raises(ValueError, match="exactly once"):
        fill_standings("<table></table>", "<tr></tr>")
