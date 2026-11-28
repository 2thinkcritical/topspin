"""Read the league's players and tournament results from CSV files.

data/players.csv              id,name,initial_rating
data/tournaments/<number>.csv first_id,second_id,first_name,second_name,score,first_place,second_place

Names in tournament files are for people reading the files; ratings are
computed from ids only.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .models import Match, Player, Tournament

PLAYER_FIELDS = ("id", "name", "initial_rating")
MATCH_FIELDS = ("first_id", "second_id", "first_name", "second_name", "score", "first_place", "second_place")


def _rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != fields:
            raise ValueError(f"{path}: expected columns {','.join(fields)}")
        return list(reader)


def load_players(path: Path) -> list[Player]:
    players = [
        Player(id=int(r["id"]), name=r["name"].strip(), initial_rating=float(r["initial_rating"]))
        for r in _rows(path, PLAYER_FIELDS)
    ]
    ids = [p.id for p in players]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate player ids")
    return players


def load_tournament(path: Path) -> Tournament:
    matches = tuple(
        Match(
            first=int(r["first_id"]),
            second=int(r["second_id"]),
            score=r["score"].strip(),
            first_place=int(r["first_place"]),
            second_place=int(r["second_place"]),
        )
        for r in _rows(path, MATCH_FIELDS)
    )
    if not matches:
        raise ValueError(f"{path}: no matches")
    if any(m.first == m.second for m in matches):
        raise ValueError(f"{path}: a player is paired with themselves")
    return Tournament(number=int(path.stem), matches=matches)


def load_tournaments(directory: Path) -> list[Tournament]:
    tournaments = sorted((load_tournament(p) for p in directory.glob("*.csv")), key=lambda t: t.number)
    numbers = [t.number for t in tournaments]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"{directory}: tournaments must be numbered 1..N without gaps, got {numbers}")
    return tournaments


def tournament_names(path: Path) -> dict[int, str]:
    """Player names as written in a tournament file, for consistency checks."""
    names: dict[int, str] = {}
    for r in _rows(path, MATCH_FIELDS):
        names[int(r["first_id"])] = r["first_name"].strip()
        names[int(r["second_id"])] = r["second_name"].strip()
    return names
