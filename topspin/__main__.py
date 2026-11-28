"""Command line: ``python -m topspin build [--out DIR]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import OUTPUT, ROOT, build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topspin", description="Build the League of Roses site.")
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build", help="recalculate ratings and write the site")
    build_cmd.add_argument("--out", type=Path, default=OUTPUT, help=f"output folder (default: {OUTPUT.name}/)")
    args = parser.parse_args(argv)

    output = args.out
    try:
        charts = build(output)
    except (ValueError, OSError) as error:  # report invalid data/paths and failed writes without a traceback
        print(f"error: {error}", file=sys.stderr)
        return 1
    output = output.resolve()
    shown = output.relative_to(ROOT) if output.is_relative_to(ROOT) else output
    print(f"Built the standings and {charts} player charts in {shown}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
