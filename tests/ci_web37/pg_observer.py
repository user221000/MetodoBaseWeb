"""Persist actual37 witness returns; never substitute an assertion or principal."""
from __future__ import annotations

import json
import os
from pathlib import Path


def record(kind, value):
    name = os.environ.get("CI_WEB37_PG_WITNESSES")
    if name is None:
        return
    path = Path(name)
    if not path.is_absolute() or not path.parent.is_dir() or path.is_symlink():
        raise ValueError("Actual37 witness output must stay in the existing private phase directory")
    row = {"kind": kind, "pid": os.getpid(), "test": os.environ.get("PYTEST_CURRENT_TEST"), "value": value}
    with path.open("ab") as output:
        output.write((json.dumps(row, separators=(",", ":")) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())


def pytest_configure(config):
    if not os.environ.get("CI_WEB37_PG_WITNESSES"):
        return
    from tests import account37_qa_pg_fixtures as qa

    original = qa.witness

    def measured(engine):
        value = original(engine)
        record("independent_qa37", value)
        return value

    qa.witness = measured
    config._web37_original_qa_witness = original


def pytest_unconfigure(config):
    original = getattr(config, "_web37_original_qa_witness", None)
    if original is not None:
        from tests import account37_qa_pg_fixtures as qa
        qa.witness = original
