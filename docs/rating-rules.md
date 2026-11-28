# League of Roses rating rules

Every tournament is scored against the ratings players had before it, then
all rating changes are applied at once. The constants live in
[`topspin/rating.py`](../topspin/rating.py).

## Match result

For a match won by a player rated `W` against a player rated `L`:

```
gain = (100 − (W − L)) × K × D / 10     if W − L < 100
gain = 0                                otherwise
```

The winner gains `gain` and the loser loses the same amount, so an upset is
worth more than a win the favourite was expected to take.

**D: how decisive the match was**

| Score | D   |
|-------|-----|
| 3:0   | 1.2 |
| 3:1   | 1.0 |
| 3:2   | 0.8 |

**K: how strong the tournament was**, by the average rating of its participants:

| Average rating | K    |
|----------------|------|
| below 250      | 0.20 |
| 250 – 349      | 0.25 |
| 350 – 449      | 0.30 |
| 450 – 549      | 0.35 |
| 550 and above  | 0.40 |

## Newcomers

A player is new while they have played five tournaments or fewer before the
current one. Their matches use fixed coefficients instead of the table above:

| Match                                | K   | D |
|--------------------------------------|-----|---|
| two newcomers                        | 1   | 1 |
| newcomer beats an established player | 1   | 1 |
| established player beats a newcomer  | 0.5 | 1 |

New players reach their level quickly, and established players risk little
against them.

## Podium bonus

In tournaments with at least 16 players, the top three receive a share of
their own rating. The share shrinks the more the player outrates the field,
measured as the average rating of the twelve highest-rated participants:

| Rating above the field average | 1st   | 2nd   | 3rd   |
|--------------------------------|-------|-------|-------|
| below 100                      | 2.5 % | 1.5 % | 1.0 % |
| 100 – 149                      | 2.0 % | 1.0 % | 0.5 % |
| 150 – 199                      | 1.0 % | 0.5 % | —     |
| 200 and above                  | —     | —     | —     |

## Published values

Each player's history is rounded to hundredths after every tournament, and
the table shows the latest value rounded to a whole point. The table is
ordered by the unrounded rating, so two players shown with the same rating
can still be in a definite order.
