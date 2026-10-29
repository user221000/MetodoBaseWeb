"""Opaque native35 ACK-control input; no service configuration or admission.

The historical test functions and real ACK reader stay unchanged. Only their
three profile-consuming controls receive this temporary input. An explicitly
selected migrated historical RAW remains available for Windows reproduction.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
from types import CodeType, FunctionType, SimpleNamespace

import pytest

SCOPE = "synthetic native35 controls; no services"
FUNCTIONS = frozenset({
    "test_actual_new_launcher_refuses_expired_before_fake_SQL_fixture_and_has_valid_control",
    "test_actual_file_bound_ACK_reader_accepts_pinned_control",
    "test_actual_file_bound_ACK_reader_refuses_drift",
})
HISTORICAL_SHA256 = "693631b8edeb9c714d06fb4833c1e3ebef45d1afe2b3db134fdf7742d70d3252"
PROFILE_BYTES = b'{"scope":"synthetic native35 controls; no services","connection":null}\n'
PROFILE_SHA256 = hashlib.sha256(PROFILE_BYTES).hexdigest()
LISTENER_FUNCTION = "test_actual_listener_observation_requires_the_exact_worker_and_loopback"
LAUNCHER_FUNCTION = "test_actual_new_launcher_refuses_expired_before_fake_SQL_fixture_and_has_valid_control"
LAUNCHER_NAME = "new_native35_admission"
LAUNCHER_BYTES = 25561
LAUNCHER_SHA256 = "e68fba7bf586e20ce8b0068500847230241ecd86801dd4c701e5f2038952e58f"


class _ListenerSubprocess:
    """Linux transport for the one pinned fake listener observation only."""

    CREATE_NO_WINDOW = 0

    def __init__(self, original_lambda):
        self._original_lambda = original_lambda
        self._initial_run = self._refuse
        self._callback = self._initial_run

    @staticmethod
    def _refuse(*_args, **_kwargs):
        raise ValueError("A real listener observation process is forbidden in synthetic controls")

    @property
    def run(self):
        return self._callback

    @run.setter
    def run(self, callback):
        if (callback is not self._initial_run
                and (not isinstance(callback, FunctionType) or callback.__code__ is not self._original_lambda)):
            raise ValueError("Only the pinned original listener fake may replace DENY")
        self._callback = callback


def _launcher_raw(path):
    if (not path.is_absolute() or path.resolve(strict=True) != path
            or any(part == ".." for part in path.parts)
            or any(item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & 0x400
                   for item in (path, *path.parents))):
        raise ValueError("The synthetic launcher source path is aliased")
    before = path.stat()
    if not path.is_file() or before.st_nlink != 1 or before.st_size != LAUNCHER_BYTES:
        raise ValueError("The pinned synthetic launcher source differs")
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_nlink)
    if identity(before) != identity(after) or hashlib.sha256(raw).hexdigest() != LAUNCHER_SHA256:
        raise ValueError("The pinned synthetic launcher source differs")
    return raw


class _LauncherLoader:
    def __init__(self, loader, path):
        self.loader, self.path = loader, path

    def create_module(self, spec):
        return self.loader.create_module(spec)

    def exec_module(self, module):
        if (module.__name__ != LAUNCHER_NAME or module.__file__ != str(self.path)
                or module.__spec__.loader is not self or module.__spec__.origin != str(self.path)):
            raise ValueError("Only the exact private synthetic launcher module may execute")
        raw = _launcher_raw(self.path)
        def code(fullname):
            if fullname != LAUNCHER_NAME:
                raise ValueError("An unreviewed synthetic launcher module was requested")
            return compile(raw, str(self.path), "exec", dont_inherit=True)
        # Delegate actual SourceFileLoader execution, with its private get_code
        # bound to the authenticated bytes rather than reopening source or pyc.
        self.loader.get_code = code
        self.loader.exec_module(module)
        _launcher_raw(self.path)
        module.os = SimpleNamespace(name="nt", environ={})


def _launcher_import(path):
    def spec_from_file_location(name, location, *args, **kwargs):
        if name != LAUNCHER_NAME or str(location) != str(path) or args or kwargs:
            raise ValueError("Only the exact pinned synthetic launcher load is permitted")
        _launcher_raw(path)
        spec = importlib.util.spec_from_file_location(name, path)
        spec.loader = _LauncherLoader(spec.loader, path)
        return spec
    return SimpleNamespace(util=SimpleNamespace(spec_from_file_location=spec_from_file_location,
                                               module_from_spec=importlib.util.module_from_spec))


def control_profile(directory, environment):
    selected = environment.get("METODOBASE_TEST_NATIVE35_V7_PROFILE")
    if selected is not None:
        path = Path(selected)
        if (not path.is_absolute()
                or not path.resolve(strict=True).is_relative_to(Path("E:/MetodoBaseWorkspace").resolve())
                or path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400
                or path.stat().st_nlink != 1 or path.stat().st_size != 424
                or hashlib.sha256(path.read_bytes()).hexdigest() != HISTORICAL_SHA256):
            raise ValueError("The explicit historical V7 profile RAW differs")
        return path, HISTORICAL_SHA256, "explicit authenticated historical RAW; pure controls only"
    path = directory / "native35-control-profile.json"
    with path.open("xb") as output:
        output.write(PROFILE_BYTES)
    if hashlib.sha256(path.read_bytes()).hexdigest() != PROFILE_SHA256:
        raise ValueError("The synthetic native35 control profile differs")
    return path, PROFILE_SHA256, SCOPE


@pytest.fixture(autouse=True)
def historical_profile_input(request, monkeypatch):
    if request.function.__name__ == LISTENER_FUNCTION and sys.platform == "linux":
        from tests import test_security_native35_v7_peer as original
        from tests.e2e import native35_guard_v7 as guard
        if request.function is not getattr(original, LISTENER_FUNCTION):
            raise ValueError("The synthetic listener input requires the original pinned function")
        callbacks = [item for item in request.function.__code__.co_consts
                     if isinstance(item, CodeType) and item.co_name == "<lambda>"]
        if len(callbacks) != 1:
            raise ValueError("The original listener fake lambda differs")
        monkeypatch.setattr(guard, "subprocess", _ListenerSubprocess(callbacks[0]))
        request.node.user_properties.append(("native35_listener_scope", "synthetic listener observation; no processes"))
        return
    if request.function.__name__ not in FUNCTIONS:
        return
    from tests.e2e import native35_guard_v7 as guard
    if request.function.__name__ == LAUNCHER_FUNCTION and sys.platform == "linux":
        from tests import test_security_native35_v7_peer as original
        if request.function is not getattr(original, LAUNCHER_FUNCTION):
            raise ValueError("The synthetic launcher input requires the original pinned function")
        monkeypatch.setattr(original, "importlib", _launcher_import(original.ROOT / "tests/e2e/run_native35_qa_v7.py"))
        request.node.user_properties.append(("native35_launcher_scope", "Windows ACK guard simulation; no services"))
    directory = request.getfixturevalue("tmp_path")
    path, expected, scope = control_profile(directory, os.environ)
    monkeypatch.setattr(guard, "PROFILE", path)
    monkeypatch.setattr(guard, "PROFILE_SHA", expected)
    request.node.user_properties.append(("native35_profile_scope", scope))
