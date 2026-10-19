"""Compatibility build command; all packaging is owned by build.py."""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from build import main as build_main
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["build"]:
        arguments.pop(0)
    return build_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
