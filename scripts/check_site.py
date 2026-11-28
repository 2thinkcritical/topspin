"""Check the static site's player-chart links and SVG documents."""

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("charts/"):
                self.links.append(href)


def main():
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    parser = LinkCollector()
    parser.feed(page)
    assert parser.links, "No player charts found"
    assert len(parser.links) == len(set(parser.links)), "Duplicate chart links"
    assert "quickchart.io" not in page.lower(), "External chart service found"
    for link in parser.links:
        path = (ROOT / urlsplit(link).path).resolve()
        assert path.is_relative_to(ROOT / "charts"), f"Invalid chart path: {link}"
        assert path.is_file(), f"Missing chart: {link}"
        svg = ET.parse(path).getroot()
        assert svg.tag == "{http://www.w3.org/2000/svg}svg", link
        ns = {"svg": "http://www.w3.org/2000/svg"}
        points = svg.findall(".//svg:circle", ns)
        assert points, f"No rating points: {link}"
        numbers = []
        for point in points:
            title = point.find("svg:title", ns)
            match = re.match(r"Турнир (\d+): -?\d", title.text if title is not None else "")
            assert match, f"Point without a tournament title: {link}"
            numbers.append(int(match.group(1)))
        assert numbers == sorted(set(numbers)), f"Tournaments out of order: {link}"
        ticks = [t for t in svg.findall(".//svg:text", ns) if "tick-x" in (t.get("class") or "").split()]
        assert len(ticks) >= 2 and all(t.text.isdigit() for t in ticks), f"Missing axis labels: {link}"
        xs = [float(t.get("x")) for t in ticks]
        gaps = [b - a for a, b in zip(xs, xs[1:])]
        assert max(gaps) - min(gaps) < 0.5, f"Uneven axis labels: {link}"
    print(f"Checked {len(parser.links)} unique player charts.")


if __name__ == "__main__":
    main()
