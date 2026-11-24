# Topspin — League of Roses

A table tennis rating table for the Topspin club in Tbilisi, Georgia. The site displays the final standings and links each player to a chart of their rating history.

**Live site:** https://2thinkcritical.github.io/topspin/

## Project structure

- `index.html` — the rating table and its styles.
- `charts/` — self-contained SVG charts, served alongside the page.
- `scripts/check_site.py` — a dependency-free integrity check for the site.
- `.github/workflows/check.yml` — runs the integrity check on pushes and pull requests.

The site is static: it needs no application server, database, build process, or third-party chart service. The Telegram link leads to an external service.

## Run locally

From the repository root:

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/`. To check the links and charts, run:

```sh
python3 scripts/check_site.py
```

## Deployment

GitHub Pages publishes the repository's `main` branch. Changes pushed to that branch are deployed by GitHub Pages.
