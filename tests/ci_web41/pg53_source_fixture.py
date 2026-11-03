"""Explicit historical source inputs for PG53 unit tests; never a SQL runner.

The unchanged phase validator still rejects the evolved working tree. Only four
exact, authenticated historical Git blobs replace their explicitly measured
current counterparts in a separate new fixture directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

from tests.ci_web37 import pg53

DESCRIPTOR = "tests/ci_web37/pg-r30-ppl53.json"
DESCRIPTOR_PIN = (11650, "8bb843786a81aeadf295b1a026877d2f4ef73fec8f473f85ec325075362e27dc")
MAX_BYTES = 128 * 1024
CURRENT_FOUR = {
    "core/routine_catalog.py": (46152, "d9f17ccc297b829c728ecbed22892ebfd6b8fb4eb77d27daefe2043a470bdc97"),
    "tests/test_routine_catalog.py": (12433, "ca4283f6237d73e0ce26e620151f0e2291edb7fabe35865292be49cedf4aea5b"),
    "tests/test_security_routines_http_peer.py": (9817, "e22258a8fe08a8d0caa76f4bb2899f5dd4cf0db98f179f56ce5fbf5a608eeca5"),
    "tests/integration_provider_subjects.py": (10350, "6a9657cc32bc044a5c3cd6e0a4bfd0d6c678f0d874b3559f4dd6504b41345ccf"),
}
_LEGACY_SNAPSHOT = pytest.StashKey()


@pytest.fixture
def original_legacy_budgets(request, tmp_path_factory):
    """Share only the Snapshot; revalidate and copy rows for every consumer."""
    from tests.ci_web41 import legacy_pg_unit_capsule

    cached = request.config.stash.get(_LEGACY_SNAPSHOT, None)
    if cached is None:
        base = tmp_path_factory.mktemp("metodobase-test-pg53-original-budgets")
        cached = legacy_pg_unit_capsule.snapshot(pg53.ROOT, base / "capsule")
        request.config.stash[_LEGACY_SNAPSHOT] = cached
    return legacy_pg_unit_capsule.historical_budget_rows(pg53.ROOT, None, snapshot=cached)


def record(raw):
    return len(raw), hashlib.sha256(raw).hexdigest()


def _root(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_dir():
        raise ValueError("An existing canonical absolute source directory is required")
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError("Source directory links are refused")
    return path


def _read(root, name):
    path = root / name
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError("Fixture source links are refused")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
        raise ValueError("A bounded regular single-link source is required")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(MAX_BYTES + 1)
        finished = os.fstat(stream.fileno())
    after = path.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink")
    if (len(raw) > MAX_BYTES or len(raw) != before.st_size
            or any(getattr(before, key) != getattr(after, key) for key in fields)
            or any(getattr(opened, key) != getattr(finished, key) for key in fields)
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)):
        raise ValueError("Fixture source changed while being read")
    return raw


def _descriptor(raw):
    if record(raw) != DESCRIPTOR_PIN:
        raise ValueError("The immutable historical53 descriptor differs")
    return json.loads(raw)


def _original(raw, pin):
    observed = record(raw)
    if observed not in {(pin["captured_bytes"], pin["captured_raw_sha256"]),
                        (pin["git_raw_bytes"], pin["git_raw_sha256"])}:
        raise ValueError("A historical53 source payload differs")
    if observed == (pin["git_raw_bytes"], pin["git_raw_sha256"]):
        oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()
        if oid != pin["Git_blob"]:
            raise ValueError("The historical53 Git object differs")


def _current(raw, pin):
    lf = raw.replace(b"\r\n", b"\n")
    if record(lf) != pin or raw not in (lf, lf.replace(b"\n", b"\r\n")):
        raise ValueError("An explicitly measured current53 source differs")


def git_blob(repository, oid, size):
    if re.fullmatch("[0-9a-f]{40}", oid) is None or type(size) is not int or not 0 < size <= MAX_BYTES:
        raise ValueError("A bounded original Git blob identity is required")
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    command = ["git", "--no-replace-objects", "-C", str(repository), "cat-file"]
    measured = subprocess.run([*command, "-s", oid], env=environment, capture_output=True,
                              check=True, timeout=15).stdout
    if measured != str(size).encode() + b"\n":
        raise ValueError("The original Git blob size differs")
    return subprocess.run([*command, "blob", oid], env=environment, capture_output=True,
                          check=True, timeout=15).stdout


def validate_payloads(payloads):
    """Reject namespace drift and authenticate every historical/current binding."""
    if type(payloads) is not dict or DESCRIPTOR not in payloads:
        raise ValueError("The exact historical53 fixture namespace is required")
    value = _descriptor(payloads[DESCRIPTOR])
    original = value["source_bindings"]
    current = value["current_fixture_bindings"]
    if set(payloads) != {DESCRIPTOR, *original, *current}:
        raise ValueError("The exact historical53 fixture namespace is required")
    for name, pin in original.items():
        if name not in current:
            _original(payloads[name], pin)
    for name, pin in current.items():
        if record(payloads[name]) != (pin["bytes"], pin["sha256"]):
            raise ValueError("A current53 fixture binding differs")
    return value


def source_payloads(repository):
    """Authenticate current inputs first, then recover only four original blobs."""
    repository = _root(repository)
    raw = _read(repository, DESCRIPTOR)
    value = _descriptor(raw)
    original = value["source_bindings"]
    current = value["current_fixture_bindings"]
    actual = {DESCRIPTOR: raw, **{name: _read(repository, name) for name in set(original) | set(current)}}
    for name, data in actual.items():
        if name == DESCRIPTOR:
            continue
        if name in current:
            if record(data) != (current[name]["bytes"], current[name]["sha256"]):
                raise ValueError("A current53 fixture binding differs")
        elif name in CURRENT_FOUR:
            _current(data, CURRENT_FOUR[name])
        else:
            _original(data, original[name])
    historical = dict(actual)
    for name in CURRENT_FOUR:
        pin = original[name]
        historical[name] = git_blob(repository, pin["Git_blob"], pin["git_raw_bytes"])
    validate_payloads(historical)
    if any(_read(repository, name) != data for name, data in actual.items()):
        raise ValueError("A source changed during historical53 fixture preparation")
    return historical


def validate_fixture(root):
    root = _root(root)
    value = _descriptor(_read(root, DESCRIPTOR))
    names = {DESCRIPTOR, *value["source_bindings"], *value["current_fixture_bindings"]}
    entries = list(root.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("Fixture source links are refused")
    present = {path.relative_to(root).as_posix() for path in entries if not path.is_dir()}
    if present != names:
        raise ValueError("The exact historical53 fixture namespace is required")
    validate_payloads({name: _read(root, name) for name in names})
    return pg53.phase(root)


def materialize(repository, destination):
    """Create a new explicit unit fixture after all source admission succeeds."""
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists()
            or _root(destination.parent) / destination.name != destination):
        raise ValueError("A new canonical absolute fixture destination is required")
    payloads = source_payloads(repository)
    destination.mkdir(mode=0o700)
    for name, raw in payloads.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    validate_fixture(destination)
    return destination
