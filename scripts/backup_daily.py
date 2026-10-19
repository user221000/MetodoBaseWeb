"""Daily backup entry point; requires explicit sources and encryption.

Use ``python scripts/backup_daily.py --help``. No-source invocations fail rather
than claiming a successful backup of absent historical SQLite files. Scheduling
and retention remain explicit deployment policies; this script sends no email.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backup_restore import main


if __name__ == "__main__":
    raise SystemExit(main(["backup", *sys.argv[1:]]))
