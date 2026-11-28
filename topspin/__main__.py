"""Command line: ``python -m topspin build [--check]``."""

from __future__ import annotations

import argparse
import sys

from .build import ROOT, build, stale_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topspin", description="Build the League of Roses site.")
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build", help="recalculate ratings and regenerate charts and the table")
    build_cmd.add_argument("--check", action="store_true", help="only verify that the generated files are up to date")
    args = parser.parse_args(argv)

    if args.check:
        stale = stale_files()
        for path in stale:
            print(f"out of date: {path.relative_to(ROOT)}", file=sys.stderr)
        if stale:
            print("Run `python -m topspin build` and commit the result.", file=sys.stderr)
            return 1
        print("Generated files are up to date.")
        return 0

    print(f"Built {build()} player charts and the standings table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
