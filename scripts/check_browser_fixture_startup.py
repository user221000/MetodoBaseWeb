"""Check a fixture's structured post-registration metadata, without evaluating log text."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(log: str, fixture: str, tables: int, revision: str) -> None:
    markers = []
    for line in log.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and value.get("fixture") == fixture:
            markers.append(value)
    if len(markers) != 1:
        raise ValueError("Missing or ambiguous fixture marker")
    value = markers[0]
    if (type(value.get("tables")) is not int or value["tables"] != tables
            or value.get("model_target_revision") != revision):
        raise ValueError("Unexpected fixture metadata target")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--tables", required=True, type=int)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    try:
        validate(args.log.read_text(encoding="utf8"), args.fixture, args.tables, args.revision)
    except (OSError, UnicodeError, ValueError):
        parser.exit(1, "Fixture startup metadata is missing, invalid or unexpected\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
