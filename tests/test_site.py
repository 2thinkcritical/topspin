"""The committed site: generated files are current, links resolve, charts are well-formed."""

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from itertools import pairwise

import pytest

from topspin.build import ROOT, stale_files
from topspin.charts import nice_ticks

SVG = {"svg": "http://www.w3.org/2000/svg"}


class _ChartLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href") or ""
        if tag == "a" and href.startswith("charts/"):
            self.links.append(href)


def _chart_links() -> list[str]:
    parser = _ChartLinks()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    return parser.links


def test_generated_files_are_up_to_date():
    stale = [str(p.relative_to(ROOT)) for p in stale_files()]
    assert not stale, "run `python -m topspin build`: " + ", ".join(stale)


def test_every_player_links_to_their_own_chart():
    links = _chart_links()
    assert links
    assert len(links) == len(set(links))
    assert {ROOT / link for link in links} == set((ROOT / "charts").glob("*.svg"))


def test_page_uses_no_external_chart_service():
    assert "quickchart" not in (ROOT / "index.html").read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("link", _chart_links())
def test_chart_is_well_formed(link):
    svg = ET.parse(ROOT / link).getroot()
    assert svg.tag == "{http://www.w3.org/2000/svg}svg"

    titles = [c.findtext("svg:title", default="", namespaces=SVG) for c in svg.findall(".//svg:circle", SVG)]
    tournaments = [int(m.group(1)) for t in titles if (m := re.fullmatch(r"Турнир (\d+): -?[\d.]+", t))]
    assert len(tournaments) == len(titles)
    assert tournaments == sorted(set(tournaments))

    if tournaments:
        ticks = [t for t in svg.findall(".//svg:text", SVG) if "tick-x" in t.get("class", "").split()]
        xs = [float(t.get("x")) for t in ticks]
        gaps = [b - a for a, b in pairwise(xs)]
        assert len(ticks) >= 2
        assert max(gaps) - min(gaps) < 0.5, "tournament labels must be evenly spaced"


@pytest.mark.parametrize(("low", "high"), [(69, 134), (1078, 1098), (100, 100), (18.07, 26.51)])
def test_axis_ticks_are_round_and_cover_the_data(low, high):
    ticks = nice_ticks(low, high)
    assert ticks[0] <= low
    assert ticks[-1] >= high
    steps = {round(b - a, 9) for a, b in pairwise(ticks)}
    assert len(steps) == 1
    assert steps.pop() in {1, 2, 2.5, 5, 10, 20, 25, 50, 100}
