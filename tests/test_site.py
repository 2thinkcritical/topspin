"""The built site: every link and asset resolves, and the charts are well-formed."""

import re
import shutil
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from itertools import pairwise
from pathlib import Path

import pytest

from topspin.build import ROOT, build
from topspin.charts import nice_ticks, render_chart
from topspin.data import load_players
from topspin.models import HistoryPoint

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


def test_registered_player_without_matches_has_an_explanatory_chart() -> None:
    chart = ET.fromstring(render_chart("New Player", [HistoryPoint(0, 100)], last_tournament=38))
    text = list(chart.itertext())
    assert "New Player" in text
    assert "Ещё не играл в турнирах лиги" in text
    assert "100" in text
    assert not chart.findall(".//svg:circle", SVG)


def test_rebuilding_replaces_old_output(tmp_path: Path) -> None:
    stale = tmp_path / "charts" / "999.svg"
    stale.parent.mkdir()
    stale.write_text("old")
    build(tmp_path)
    assert not stale.exists()


@pytest.mark.parametrize(
    "destination", [".", "..", "web", "web/output", "data", "topspin", "tests", ".git", ".github", "docs", ".venv"]
)
def test_build_rejects_source_destinations_without_deleting_files(tmp_path: Path, destination: str) -> None:
    root = tmp_path / "source"
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "web", root / "web")
    output = root / destination
    output.mkdir(parents=True, exist_ok=True)
    sentinel = output / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="source"):
        build(output, root=root)
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert (root / "data" / "players.csv").is_file()


def test_build_rejects_symbolic_link_destination(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    output = tmp_path / "link"
    output.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        build(output)
    assert output.is_symlink()
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_build_rejects_a_file_destination(tmp_path: Path) -> None:
    output = tmp_path / "keep.txt"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="directory"):
        build(output)
    assert output.read_text(encoding="utf-8") == "keep"


def test_staging_failure_keeps_previous_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "site"
    output.mkdir()
    previous = output / "index.html"
    previous.write_text("previous site", encoding="utf-8")

    def fail_copy(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copytree", fail_copy)
    with pytest.raises(OSError, match="disk full"):
        build(output)
    assert previous.read_text(encoding="utf-8") == "previous site"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["site"]


@pytest.mark.parametrize("previous_site", [False, True])
def test_install_failure_restores_previous_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, previous_site: bool
) -> None:
    output = tmp_path / "site"
    if previous_site:
        output.mkdir()
        (output / "index.html").write_text("previous site", encoding="utf-8")
    replace = Path.replace

    def fail_install(path: Path, target: str | Path) -> Path:
        if path.name == "site" and path.parent.name.startswith(".site-"):
            raise OSError("install failed")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_install)
    with pytest.raises(OSError, match="install failed"):
        build(output)
    if previous_site:
        assert (output / "index.html").read_text(encoding="utf-8") == "previous site"
    else:
        assert not output.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == (["site"] if previous_site else [])


def test_build_rejects_source_through_a_symbolic_link_parent(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="source"):
        build(alias / "web" / "output", root=root)
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("source_name", ["data", "web"])
@pytest.mark.parametrize("ancestor", [False, True])
def test_build_protects_external_symlinked_sources_and_their_ancestors(
    tmp_path: Path, source_name: str, ancestor: bool
) -> None:
    root, external = tmp_path / "source", tmp_path / "external"
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "web", root / "web")
    external.mkdir()
    target = external / source_name
    shutil.move(root / source_name, target)
    (root / source_name).symlink_to(target, target_is_directory=True)
    sentinel = target / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="source"):
        build(external if ancestor else target, root=root)
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_failed_rollback_retains_recoverable_previous_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "site"
    output.mkdir()
    (output / "index.html").write_text("previous site", encoding="utf-8")
    replace = Path.replace

    def fail_install_and_restore(path: Path, target: str | Path) -> Path:
        if path.parent.name.startswith(".site-"):
            raise OSError("rename unavailable")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_install_and_restore)
    with pytest.raises(OSError, match="backup kept at"):
        build(output)
    retained = list(tmp_path.glob(".site-*/previous/index.html"))
    assert len(retained) == 1
    assert retained[0].read_text(encoding="utf-8") == "previous site"


@pytest.mark.parametrize(("low", "high"), [(69, 134), (1078, 1098), (100, 100), (18.07, 26.51)])
def test_axis_ticks_are_round_and_cover_the_data(low: float, high: float) -> None:
    ticks = nice_ticks(low, high)
    assert ticks[0] <= low
    assert ticks[-1] >= high
    steps = {round(b - a, 9) for a, b in pairwise(ticks)}
    assert len(steps) == 1
    assert steps.pop() in {1, 2, 2.5, 5, 10, 20, 25, 50, 100}
