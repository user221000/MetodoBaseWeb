"""Write a private source/profile/29-phase PG429 contract without SQL."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_web37.evidence import boundary_before_payload, write
from tests.ci_web37.pg_lease import contract, digest
from tests.ci_web37.pg_plan import phases
from tests.ci_web37.prepare_collection import source_photo


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--pg-profile", type=Path, required=True)
    parser.add_argument("--groups", nargs="+", choices=[row["key"] for row in phases()])
    args = parser.parse_args()
    private = private_directory(args.private)
    boundary_before_payload(private)
    before = source_photo()
    value = contract(ROOT, before, args.pg_profile, args.groups or [row["key"] for row in phases()])
    write(private / "contract.json", value)
    if source_photo() != before:
        raise ValueError("The PG429 contract source changed during preflight")
    print(digest(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
