"""Require a complete, typed report from a maintained frontend acceptance driver."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(report: object, kind: str, minimum: int, minimum_screens: int = 0) -> None:
    if not isinstance(report, dict) or minimum < 1 or minimum_screens < 0:
        raise ValueError("Invalid report or acceptance minimum")
    if kind == "counts":
        total, passed, rows = report.get("total"), report.get("passed"), report.get("results")
        if (type(total) is not int or type(passed) is not int or total < minimum
                or passed != total or not isinstance(rows, list) or len(rows) != total):
            raise ValueError("Missing, inconsistent or unsuccessful contract results")
        names = []
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get("case"), str)
                    or not row["case"].strip() or row.get("passed") is not True):
                raise ValueError("Invalid contract case")
            names.append(row["case"])
    elif kind in ("strings", "named"):
        rows, errors = report.get("checks"), report.get("pageErrors")
        if not isinstance(rows, list) or len(rows) < minimum or not isinstance(errors, list) or errors:
            raise ValueError("Missing browser checks or browser errors")
        names = []
        for row in rows:
            name = row if kind == "strings" else row.get("name") if isinstance(row, dict) else None
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Invalid browser check")
            if isinstance(row, dict) and "passed" in row and row["passed"] is not True:
                raise ValueError("Unsuccessful browser check")
            names.append(name)
        if minimum_screens:
            screens = report.get("screens")
            if (not isinstance(screens, list) or len(screens) < minimum_screens
                    or any(not isinstance(name, str) or not name.strip() for name in screens)
                    or len(set(screens)) != len(screens)):
                raise ValueError("Missing or invalid browser screens")
    else:
        raise ValueError("Unknown report format")
    if len(set(names)) != len(names):
        raise ValueError("Repeated checks cannot satisfy acceptance minimum")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--format", choices=("strings", "named", "counts"), required=True)
    parser.add_argument("--minimum", type=int, required=True)
    parser.add_argument("--minimum-screens", type=int, default=0)
    args = parser.parse_args()
    try:
        validate(json.loads(args.report.read_text(encoding="utf-8")), args.format,
                 args.minimum, args.minimum_screens)
    except (OSError, UnicodeError, ValueError):
        parser.exit(1, "Frontend acceptance report is missing, invalid or unsuccessful\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
