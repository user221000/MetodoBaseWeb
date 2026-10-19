"""Run pytest or the real web runtime with temporary data and providers off.

Examples: python -X utf8 tests/run_isolated.py tests -q
          python -X utf8 tests/run_isolated.py --serve-web
"""
from pathlib import Path
import argparse
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.isolation import block_external_sockets, prepare_environment


def main() -> int:
    """Configure isolation before loading pytest or web.main_web."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--serve-web", action="store_true")
    parser.add_argument("--shuffle-seed", type=int)
    parser.add_argument("--reverse-order", action="store_true")
    options, pytest_args = parser.parse_known_args(sys.argv[1:])
    os.environ["_METODOBASE_TEST_REVERSE"] = "1" if options.reverse_order else "0"
    os.environ["_METODOBASE_TEST_SHUFFLE_SEED"] = "" if options.shuffle_seed is None else str(options.shuffle_seed)
    root = prepare_environment(discard_inherited=True)
    block_external_sockets()
    if options.serve_web:
        import uvicorn
        from web.database.engine import get_engine
        from web.database.models import Base

        # The browser fixture prepares SQLite explicitly; the product factory
        # verifies existing schema and never performs implicit startup DDL.
        engine = get_engine()
        if engine.dialect.name == "sqlite":
            Base.metadata.create_all(engine)
        from web.main_web import create_app
        uvicorn.run(create_app(), host="127.0.0.1", port=8765, log_level="warning")
        return 0
    import pytest

    return pytest.main(pytest_args + ["-o", "cache_dir=" + str(root / ".pytest_cache")])


if __name__ == "__main__":
    raise SystemExit(main())
