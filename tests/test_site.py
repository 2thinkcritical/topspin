"""The built site: every link and asset resolves, and the charts are well-formed."""

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from itertools import pairwise
from pathlib import Path

import pytest

from topspin.build import build
from topspin.charts import nice_ticks
from topspin.data import load_players

SVG = {"svg": "http://www.w3.org/2000/svg"}


class _References(HTMLParser):
    """Local files a page refers to through href and src attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.local: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value and not re.match(r"[a-z]+:|#", value):
                self.local.append(value)


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output: Path = tmp_path_factory.mktemp("site")
    build(output)
    return output


@pytest.fixture(scope="module")
def references(site: Path) -> list[str]:
    parser = _References()
    parser.feed((site / "index.html").read_text(encoding="utf-8"))
    return parser.local


def test_every_local_reference_resolves(site: Path, references: list[str]) -> None:
    missing = [ref for ref in references if not (site / ref).is_file()]
    assert not missing


def test_every_player_has_one_row_and_one_chart(site: Path, references: list[str]) -> None:
    chart_links = [ref for ref in references if ref.startswith("charts/")]
    player_ids = {p.id for p in load_players(Path(__file__).parent.parent / "data" / "players.csv")}
    assert sorted(chart_links) == sorted(f"charts/{pid}.svg" for pid in player_ids)
    assert {p.name for p in (site / "charts").iterdir()} == {f"{pid}.svg" for pid in player_ids}


def test_rows_replace_the_placeholder(site: Path) -> None:
    page = (site / "index.html").read_text(encoding="utf-8")
    assert "<!-- standings -->" not in page
    places = [int(p) for p in re.findall(r"<tr><td>(\d+)</td>", page)]
    assert places == list(range(1, len(places) + 1))


def test_charts_are_well_formed(site: Path) -> None:
    for chart in sorted((site / "charts").glob("*.svg")):
        svg = ET.parse(chart).getroot()
        assert svg.tag == "{http://www.w3.org/2000/svg}svg", chart.name

        circles = svg.findall(".//svg:circle", SVG)
        titles = [c.findtext("svg:title", default="", namespaces=SVG) for c in circles]
        tournaments = [int(m.group(1)) for t in titles if (m := re.fullmatch(r"Турнир (\d+): -?[\d.]+", t))]
        assert len(tournaments) == len(titles), chart.name
        assert tournaments == sorted(set(tournaments)), chart.name

        if tournaments:
            ticks = [t for t in svg.findall(".//svg:text", SVG) if "tick-x" in t.get("class", "").split()]
            gaps = [b - a for a, b in pairwise(float(t.get("x", "nan")) for t in ticks)]
            assert len(ticks) >= 2, chart.name
            assert max(gaps) - min(gaps) < 0.5, f"{chart.name}: tournament labels must be evenly spaced"


def test_rebuilding_replaces_old_output(tmp_path: Path) -> None:
    stale = tmp_path / "charts" / "999.svg"
    stale.parent.mkdir()
    stale.write_text("old")
    build(tmp_path)
    assert not stale.exists()


@pytest.mark.parametrize(("low", "high"), [(69, 134), (1078, 1098), (100, 100), (18.07, 26.51)])
def test_axis_ticks_are_round_and_cover_the_data(low: float, high: float) -> None:
    ticks = nice_ticks(low, high)
    assert ticks[0] <= low
    assert ticks[-1] >= high
    steps = {round(b - a, 9) for a, b in pairwise(ticks)}
    assert len(steps) == 1
    assert steps.pop() in {1, 2, 2.5, 5, 10, 20, 25, 50, 100}
