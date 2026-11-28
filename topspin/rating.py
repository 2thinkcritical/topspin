"""League of Roses rating rules.

Each tournament is scored against the ratings players had *before* it, so the
order of matches within a tournament does not matter. The rules are described
in docs/rating-rules.md; the constants below are the single source of truth.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from .models import HistoryPoint, Match, Player, PlayerId, Tournament

# Rating gap at which the favourite no longer gains anything for a win.
MAX_GAP = 100
# A player is "new" while they have played this many tournaments or fewer.
NEW_PLAYER_TOURNAMENTS = 5

# Match-closeness coefficient D: a clean sweep is worth more than a five-setter.
SCORE_COEFFICIENTS = {"3:0": 1.2, "3:1": 1.0, "3:2": 0.8}

# Tournament strength coefficient K, chosen by the participants' average rating.
# Each entry is (upper bound of the average, K); the last bound is open-ended.
K_BY_AVERAGE = ((250, 0.2), (350, 0.25), (450, 0.3), (550, 0.35), (float("inf"), 0.4))

# Podium bonuses apply only to tournaments with at least this many players and are
# a share of the player's rating, shrinking as they outrank the field's top twelve.
BONUS_MIN_PARTICIPANTS = 16
BONUS_FIELD_SIZE = 12
# place -> ((upper bound of rating minus field average, share of rating), ...)
PODIUM_BONUSES = {
    1: ((100, 0.025), (150, 0.02), (200, 0.01)),
    2: ((100, 0.015), (150, 0.01), (200, 0.005)),
    3: ((100, 0.01), (150, 0.005)),
}


def parse_score(score: str) -> tuple[bool, float]:
    """Return whether the first player won and the closeness coefficient D."""
    try:
        a, b = (int(part) for part in score.split(":"))
    except ValueError:
        raise ValueError(f"Invalid match score {score!r}") from None
    key = f"{max(a, b)}:{min(a, b)}"
    if key not in SCORE_COEFFICIENTS:
        raise ValueError(f"Invalid match score {score!r}")
    return a > b, SCORE_COEFFICIENTS[key]


def tournament_k(average_rating: float) -> float:
    return next(k for bound, k in K_BY_AVERAGE if average_rating < bound)


def win_gain(winner_rating: float, loser_rating: float, k: float, d: float) -> float:
    """Points the winner takes from the loser."""
    gap = winner_rating - loser_rating
    return (MAX_GAP - gap) * k * d / 10 if gap < MAX_GAP else 0.0


def round_cents(value: float) -> float:
    """Round to hundredths the way the league's original (NumPy-based) code did.

    Scaling first and rounding half to even differs from ``round(value, 2)`` for
    values such as 230.925, and published histories depend on it.
    """
    return round(value * 100) / 100


def podium_bonus(place: int, rating: float, field_average: float) -> float:
    lead = rating - field_average
    for bound, share in PODIUM_BONUSES[place]:
        if lead < bound:
            return rating * share
    return 0.0


@dataclass(frozen=True, slots=True)
class RatingResult:
    """Exact ratings after the last tournament and each player's rating history.

    History values are rounded to hundredths after every tournament, as the
    league has always published them; ``ratings`` keeps full precision and
    decides the order of the table.
    """

    ratings: Mapping[PlayerId, float]
    history: Mapping[PlayerId, Sequence[HistoryPoint]]

    def standings(self) -> list[PlayerId]:
        """Player ids from the highest rating down; equal ratings keep id order."""
        return sorted(self.ratings, key=lambda pid: (-self.ratings[pid], pid))


def _match_coefficients(
    match: Match, first_wins: bool, d: float, k: float, new_players: frozenset[PlayerId]
) -> tuple[float, float]:
    """Return (K, D) for a match, softening the result when a newcomer is involved."""
    first_new, second_new = match.first in new_players, match.second in new_players
    if first_new and second_new:
        return 1.0, 1.0
    if first_new or second_new:
        newcomer_won = first_wins == first_new
        return (1.0 if newcomer_won else 0.5), 1.0
    return k, d


def score_tournament(
    tournament: Tournament, ratings: Mapping[PlayerId, float], new_players: frozenset[PlayerId]
) -> dict[PlayerId, float]:
    """Rating change of every participant, including podium bonuses."""
    participants = tournament.participants
    k = tournament_k(sum(ratings[p] for p in participants) / len(participants))

    changes: dict[PlayerId, float] = {}
    for match in tournament.matches:
        first_wins, d = parse_score(match.score)
        match_k, match_d = _match_coefficients(match, first_wins, d, k, new_players)
        winner, loser = (match.first, match.second) if first_wins else (match.second, match.first)
        gain = win_gain(ratings[winner], ratings[loser], match_k, match_d)
        changes[match.first] = changes.get(match.first, 0.0) + (gain if first_wins else -gain)
        changes[match.second] = changes.get(match.second, 0.0) + (-gain if first_wins else gain)

    if len(participants) >= BONUS_MIN_PARTICIPANTS:
        top = sorted((ratings[p] for p in participants), reverse=True)[:BONUS_FIELD_SIZE]
        field_average = sum(top) / BONUS_FIELD_SIZE
        for place in PODIUM_BONUSES:
            player = tournament.player_at(place)
            changes[player] += podium_bonus(place, ratings[player], field_average)
    return changes


def calculate(players: Iterable[Player], tournaments: Iterable[Tournament]) -> RatingResult:
    """Replay every tournament in order and return the resulting ratings."""
    ratings = {p.id: float(p.initial_rating) for p in players}
    history = {pid: [HistoryPoint(0, rating)] for pid, rating in ratings.items()}
    played: dict[PlayerId, int] = dict.fromkeys(ratings, 0)

    for tournament in sorted(tournaments, key=lambda t: t.number):
        unknown = tournament.participants - ratings.keys()
        if unknown:
            raise ValueError(f"Tournament {tournament.number} has unknown players: {sorted(unknown)}")
        new_players = frozenset(p for p in tournament.participants if played[p] <= NEW_PLAYER_TOURNAMENTS)
        for pid, change in score_tournament(tournament, ratings, new_players).items():
            ratings[pid] += change
            previous = history[pid][-1].rating
            history[pid].append(HistoryPoint(tournament.number, round_cents(previous + change)))
        for pid in tournament.participants:
            played[pid] += 1

    return RatingResult(ratings=ratings, history={pid: tuple(h) for pid, h in history.items()})
