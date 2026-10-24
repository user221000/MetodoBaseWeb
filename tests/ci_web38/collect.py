"""Collection-only current source oracle; no fixtures, SQL, Chrome or providers."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_web38.reports import CollectionOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-output", type=Path)
    args, selectors = parser.parse_known_args()
    if not selectors or args.output.exists() or (args.fixture_output and args.fixture_output.exists()):
        parser.error("Explicit selectors and an unused output path are required")
    from tests.isolation import block_external_sockets, prepare_environment
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    import pytest
    return pytest.main(["--collect-only", "-q", *selectors],
                       plugins=[CollectionOracle(args.output, args.fixture_output)])


if __name__ == "__main__":
    raise SystemExit(main())
