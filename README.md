# Topspin — League of Roses

[![Site](https://github.com/2thinkcritical/topspin/actions/workflows/site.yml/badge.svg)](https://github.com/2thinkcritical/topspin/actions/workflows/site.yml)

Ratings for the League of Roses, the tournament series of the Topspin table
tennis club in Tbilisi, Georgia.

**Live site:** https://2thinkcritical.github.io/topspin/

The repository holds the tournament results, the rating rules and the page
sources. On every push to `main`, GitHub Actions tests the code, builds the
site and publishes it to GitHub Pages. Nothing generated is committed.

## How it works

```
data/players.csv  ─┐
                   ├─→ topspin.rating ─┬─→ topspin.charts ─→ _site/charts/<player id>.svg
data/tournaments/ ─┘                   └─→ topspin.page   ─→ _site/index.html
web/  (page, styles, script, images) ──────────────────────→ _site/
```

| Path | Contents |
|------|----------|
| `data/` | Players with their starting ratings, and the matches of every tournament. |
| `topspin/rating.py` | The rating rules ([docs/rating-rules.md](docs/rating-rules.md)). A pure function of the data. |
| `topspin/data.py` | Reads and validates the CSV files. |
| `topspin/charts.py`, `topspin/page.py` | Render each player's chart and the standings table. |
| `topspin/build.py` | Puts the site together in `_site/`. |
| `web/` | The hand-written page: `index.html` (the table goes where it says `<!-- standings -->`), `style.css`, `title-ball.js`, images. |
| `tests/` | Rating rules, data integrity, the built site, and parity with the original implementation. |

The Python package has no runtime dependencies.

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

1. Add any new players to `data/players.csv`.
2. Add the results as `data/tournaments/38.csv` (the next number).
3. Commit and push to `main`, or upload the file through the GitHub web interface.

The site updates a minute or two later. If the data is invalid, the workflow fails,
the live site stays as it was, and the run's log says what is wrong.

## Development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                    # install the dev tools from uv.lock
uv run pytest                              # tests, with 100 % line and branch coverage required
uv run mypy                                # strict type checking of the package and the tests
uv run ruff check . && uv run ruff format --check .
uv run python -m topspin build             # writes _site/
python3 -m http.server -d _site 8000       # preview at http://localhost:8000/
```

The [Site workflow](.github/workflows/site.yml) runs the same checks on Python 3.11 and 3.13
for every push and pull request, then builds the site and deploys it from `main`. Dependabot
keeps the actions and dev tools up to date.

`tests/data/legacy_results.json` holds the ratings produced by the league's original pandas
implementation. The tests require the current code to reproduce them exactly, so the rules
cannot change by accident.

## License

Released into the public domain under [the Unlicense](LICENSE).
