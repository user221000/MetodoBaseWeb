"""Exact historical lock inputs for the original container37 peer criteria.

Authenticate all current19 inputs and every restored13 payload before exposing
the three original inputs in a new private test directory. This is fixture data,
not acceptance of current packages, build, runtime or scanner findings. The
current19/current57 gates remain required independently. No APT inverse or
historical source modification is performed; the checkout must remain quiet.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from tests.ci_image57 import technical_child
from tests.ci_web37.container_inputs import verify_current_lock

LOCK_FILES = ("requirements_web.lock", "requirements-container.lock",
              "runtime-source/container37-contract.json")
PEER_MODULES = frozenset({"tests.test_security_container37_count57_peer",
                          "tests.test_security_container37_extras_peer"})


def _single_link_sources(root):
    for name in technical_child.PINS:
        info = (Path(root) / name).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("Historical fixture inputs must be single-link regular sources")


def historical_lock_payloads(root):
    """Recover the complete authenticated parent before selecting fixture data."""
    _single_link_sources(root)
    actual = technical_child.read_payloads(root)
    _single_link_sources(root)
    if type(actual) is not dict or len(actual) != 19 or set(actual) != set(technical_child.PINS):
        raise ValueError("Exactly nineteen authenticated current inputs are required")
    restored = technical_child.inverse(actual)
    expected = {**technical_child.PARENT_PINS,
                "requirements_web.lock": technical_child.LOCK_INVERSES["requirements_web.lock"]["parent_pin"]}
    if (type(restored) is not dict or len(expected) != 13 or set(restored) != set(expected)
            or any(type(restored[name]) is not bytes or technical_child.record(restored[name]) != pin
                   for name, pin in expected.items())):
        raise ValueError("Every one of thirteen historical parent inputs must authenticate")
    return {name: restored[name] for name in LOCK_FILES}


def materialize_lock_inputs(root, destination):
    """Create only three verified historical files, outside the current source."""
    root, destination = Path(root), Path(destination)
    if (not root.is_absolute() or root.resolve(strict=True) != root.absolute()
            or not destination.is_absolute() or destination.resolve(strict=False) != destination.absolute()
            or destination.is_relative_to(root) or destination.exists() or destination.is_symlink()
            or destination.parent.resolve(strict=True) != destination.parent.absolute()
            or not stat.S_ISDIR(destination.parent.lstat().st_mode)):
        raise ValueError("A fresh unaliased historical fixture destination is required")
    payloads = historical_lock_payloads(root)
    # Preserve the original parser and its complete name/version/hash/count
    # checks. Only its historical data input is supplied by this fixture.
    from tests.ci_image57.context import json_object

    verify_current_lock(payloads[LOCK_FILES[0]], payloads[LOCK_FILES[1]],
                        json_object(payloads[LOCK_FILES[2]]))
    destination.mkdir(mode=0o700)
    for name, raw in payloads.items():
        path = destination / name
        if path.parent != destination:
            path.parent.mkdir(mode=0o700)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
    return destination


@pytest.fixture(autouse=True)
def historical_container37_inputs(request, tmp_path, monkeypatch):
    """Only the two original peer modules receive these historical inputs."""
    module = request.module
    if module.__name__ not in PEER_MODULES:
        raise ValueError("Only the two declared historical lock peers may use this fixture")
    private = materialize_lock_inputs(module.ROOT, tmp_path / "historical-container37")
    monkeypatch.setattr(module, "ROOT", private)
