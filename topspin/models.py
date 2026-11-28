"""Domain types shared by the rating engine, the data loaders and the renderers."""

from __future__ import annotations

from dataclasses import dataclass

PlayerId = int


@dataclass(frozen=True, slots=True)
class Player:
    id: PlayerId
    name: str
    initial_rating: float


@dataclass(frozen=True, slots=True)
class Match:
    """One best-of-five match. ``score`` is written from the first player's side, e.g. ``"3:1"``."""

    first: PlayerId
    second: PlayerId
    score: str
    first_place: int
    second_place: int


@dataclass(frozen=True, slots=True)
class Tournament:
    number: int
    matches: tuple[Match, ...]

    @property
    def participants(self) -> frozenset[PlayerId]:
        return frozenset(p for m in self.matches for p in (m.first, m.second))

    def player_at(self, place: int) -> PlayerId:
        for m in self.matches:
            if m.first_place == place:
                return m.first
            if m.second_place == place:
                return m.second
        raise ValueError(f"Tournament {self.number} has no player in place {place}")


@dataclass(frozen=True, slots=True)
class HistoryPoint:
    """A player's rating after a tournament; tournament 0 is the starting rating."""

    tournament: int
    rating: float
