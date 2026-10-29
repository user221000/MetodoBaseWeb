"""Restore only explicit39 authority after ordinary test isolation clears PG*.

No inherited PG39 environment can admit a test. The three private paths and
phase must be supplied as explicit pytest options and validated without SQL
after conftest has installed the existing provider/network isolation.
"""
import os
from pathlib import Path

import pytest

OPTIONS = {"PG39_PHASE": "pg39_phase", "PG39_PROFILE": "pg39_profile",
           "PG39_GENERATION": "pg39_generation", "PG39_ACK": "pg39_ack"}


def pytest_addoption(parser):
    group = parser.getgroup("current39-postgres")
    group.addoption("--pg39-phase", choices=("core", "restore"))
    for name in ("profile", "generation", "ack"):
        group.addoption("--pg39-" + name, type=Path)


def pytest_configure(config):
    values = {key: config.getoption(option) for key, option in OPTIONS.items()}
    if all(value is None for value in values.values()):
        return
    if any(value is None for value in values.values()):
        raise pytest.UsageError("All explicit current39 phase/profile/generation/ACK options are required")
    if any(not values[key].is_absolute() for key in OPTIONS if key != "PG39_PHASE"):
        raise pytest.UsageError("Current39 authority paths must be absolute")
    os.environ.update({key: str(value) for key, value in values.items()})
    from tests.ci_web39.pg_contract import checked_runtime
    checked_runtime(values["PG39_PHASE"])
