from itertools import pairwise

import pytest

from topspin.models import Match, Player, Tournament
from topspin.rating import (
    calculate,
    parse_score,
    podium_bonus,
    round_cents,
    score_tournament,
    tournament_k,
    win_gain,
)


@pytest.mark.parametrize(
    ("score", "first_wins", "d"),
    [("3:0", True, 1.2), ("3:1", True, 1.0), ("3:2", True, 0.8), ("0:3", False, 1.2), ("2:3", False, 0.8)],
)
def test_parse_score(score, first_wins, d):
    assert parse_score(score) == (first_wins, d)


@pytest.mark.parametrize("score", ["3:3", "4:1", "1-3", "", "a:b"])
def test_parse_score_rejects_invalid(score):
    with pytest.raises(ValueError, match="Invalid match score"):
        parse_score(score)


@pytest.mark.parametrize(
    ("average", "k"),
    [(100, 0.2), (249.9, 0.2), (250, 0.25), (349.9, 0.25), (350, 0.3), (450, 0.35), (550, 0.4), (1200, 0.4)],
)
def test_tournament_k(average, k):
    assert tournament_k(average) == k


def test_win_gain():
    assert win_gain(300, 300, k=0.2, d=1.0) == pytest.approx(2.0)
    assert win_gain(250, 300, k=0.2, d=1.2) == pytest.approx(3.6)  # upset: the underdog gains more
    assert win_gain(390, 300, k=0.2, d=1.0) == pytest.approx(0.2)
    assert win_gain(400, 300, k=0.4, d=1.2) == 0.0  # a 100-point favourite gains nothing


def test_podium_bonus_shrinks_with_lead_over_the_field():
    assert podium_bonus(1, 400, field_average=350) == pytest.approx(10.0)
    assert podium_bonus(1, 400, field_average=280) == pytest.approx(8.0)
    assert podium_bonus(1, 400, field_average=230) == pytest.approx(4.0)
    assert podium_bonus(1, 400, field_average=200) == 0.0
    assert podium_bonus(2, 400, field_average=400) == pytest.approx(6.0)
    assert podium_bonus(3, 400, field_average=400) == pytest.approx(4.0)
    assert podium_bonus(3, 400, field_average=240) == 0.0


def test_round_cents_matches_the_original_rounding():
    assert round_cents(230.925) == 230.92
    assert round(230.925, 2) == 230.93  # why the helper exists


def _duel(score: str, number: int = 1) -> Tournament:
    return Tournament(number, (Match(1, 2, score, first_place=1, second_place=2),))


@pytest.mark.parametrize(
    ("new_players", "score", "gain"),
    [
        (set(), "3:1", 2.5),  # K for an average of 300 is 0.25, D for 3:1 is 1
        (set(), "3:0", 3.0),
        ({2}, "3:1", 5.0),  # newcomer loses: K 0.5, D 1
        ({2}, "1:3", 10.0),  # newcomer wins: K 1, D 1
        ({1, 2}, "3:0", 10.0),  # two newcomers: K 1, D 1
    ],
)
def test_match_coefficients(new_players, score, gain):
    changes = score_tournament(_duel(score), {1: 300.0, 2: 300.0}, frozenset(new_players))
    sign = 1 if parse_score(score)[0] else -1
    assert changes == pytest.approx({1: sign * gain, 2: -sign * gain})


def _round_robin_pairs(size: int) -> Tournament:
    """Player i beats player i + 1 for every odd i; player i finishes in place i."""
    matches = tuple(Match(i, i + 1, "3:0", i, i + 1) for i in range(1, size, 2))
    return Tournament(1, matches)


def test_podium_bonuses_need_sixteen_players():
    ratings = dict.fromkeys(range(1, 17), 200.0)
    gain = 2.4  # equal ratings, K 0.2, D 1.2
    with_bonus = score_tournament(_round_robin_pairs(16), ratings, frozenset())
    assert with_bonus[1] == pytest.approx(gain + 5.0)
    assert with_bonus[2] == pytest.approx(-gain + 3.0)
    assert with_bonus[3] == pytest.approx(gain + 2.0)
    assert with_bonus[4] == pytest.approx(-gain)

    del ratings[16]
    small = Tournament(1, (*_round_robin_pairs(16).matches[:-1], Match(15, 1, "0:3", 15, 1)))
    without_bonus = score_tournament(small, ratings, frozenset())
    assert len(small.participants) == 15
    assert without_bonus[3] == pytest.approx(gain)


def test_calculate_records_only_tournaments_a_player_entered():
    players = [Player(1, "A", 100), Player(2, "B", 100), Player(3, "C", 100)]
    result = calculate(players, [_duel("3:0", number=1), _duel("0:3", number=2)])
    assert [(p.tournament, p.rating) for p in result.history[1]] == [(0, 100), (1, 110), (2, 98)]
    assert [(p.tournament, p.rating) for p in result.history[3]] == [(0, 100)]
    assert result.standings() == [2, 3, 1]


def test_players_stop_being_new_after_five_tournaments():
    players = [Player(1, "A", 300), Player(2, "B", 300)]
    result = calculate(players, [_duel("3:0", n) for n in range(1, 8)])
    gains = [b.rating - a.rating for a, b in pairwise(result.history[1])]
    gap = result.history[1][5].rating - result.history[2][5].rating
    assert gains[5] == pytest.approx((100 - gap) / 10, abs=0.01)  # newcomers: K 1, D 1
    assert gains[6] < gains[5] / 2  # tournament 7 uses the normal K and D


def test_calculate_rejects_unknown_players():
    with pytest.raises(ValueError, match="unknown players"):
        calculate([Player(1, "A", 100)], [_duel("3:0")])
