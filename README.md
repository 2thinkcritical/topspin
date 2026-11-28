# Topspin — League of Roses

Ratings for the League of Roses, the tournament series of the Topspin table
tennis club in Tbilisi, Georgia.

**Live site:** https://2thinkcritical.github.io/topspin/

The site is static: GitHub Pages serves `index.html` and one SVG chart per
player. Both are generated from the tournament results in `data/` by a small
Python package with no runtime dependencies.

## How it works

```
data/players.csv  ─┐
                   ├─ topspin.rating ─┬─ topspin.charts ─→ charts/<player id>.svg
data/tournaments/ ─┘   (replays every  └─ topspin.page   ─→ standings table in index.html
                        tournament)
```

- **`topspin/rating.py`** holds the rating rules (see [docs/rating-rules.md](docs/rating-rules.md)).
  It is a pure function of the data: replaying all tournaments always produces the same ratings.
- **`topspin/data.py`** reads and validates the CSV files.
- **`topspin/charts.py`** and **`topspin/page.py`** render the output. `index.html` is written by hand;
  only the rows between its `standings:start` and `standings:end` markers are generated.

## Data

`data/players.csv`: every player and their starting rating.

```csv
id,name,initial_rating
1,Тарасевич Сергей,175
```

`data/tournaments/<number>.csv`: every match of a tournament, with both players' final places.
Ratings are computed from ids; names are there for people reading the file and must match `players.csv`.

```csv
first_id,second_id,first_name,second_name,score,first_place,second_place
124,1,Горбадей Никита,Тарасевич Сергей,3:1,2,3
```

## Adding a tournament

1. Add new players to `data/players.csv`.
2. Save the results as `data/tournaments/38.csv` (the next number).
3. Rebuild and check:

   ```sh
   python3 -m topspin build
   uv run pytest
   ```

4. Commit `data/`, `charts/` and `index.html`. GitHub Pages publishes `main` automatically.

## Development

Requires Python 3.11+. Tests and linting use [uv](https://docs.astral.sh/uv/):

```sh
uv run pytest                          # rules, data integrity and the generated site
uv run ruff check . && uv run ruff format --check .
python3 -m topspin build --check       # fails if generated files are out of date
python3 -m http.server 8000            # preview at http://localhost:8000/
```

CI runs all of these on every push and pull request.

`tests/data/legacy_results.json` holds the ratings produced by the league's original pandas
implementation. The tests require the current code to reproduce them exactly, so the rules
cannot change by accident.
