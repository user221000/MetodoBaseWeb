"""Source-only legacy inspector in one isolated child, never PG234 execution.

Parent Items explicitly delegate the original nineteen identities. The unchanged
unit, provider identity checks and budget validators execute in the child only.
No historical source/pin or serial import/global namespace is modified.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "tests/ci_web41/fixtures/legacy-pg-unit-560.json"
MANIFEST_PIN = (22160, "4f2e283c091137ba736dee109b7bca583a758b6baf7b0df63a2b044d59b45c57")
SCHEMA = "legacy-pg-unit-child-v2"
PROJECT = frozenset({"tests", "web", "api", "config", "core", "src", "utils", "scripts"})
PHASES = ("setup", "call", "teardown")
_ISSUED = object()
CURRENT_REFERENCES = ("tests/test_ci_web37_pg_legacy.py", "tests/ci_web37/pg_legacy.py",
                      "tests/ci_web37/pg-legacy37.json", "tests/ci_web37/pg_rls_seed.py")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate capsule JSON field")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path.absolute():
        raise ValueError("Capsule directory is not canonical")
    for parent in (path, *path.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("Capsule directory alias")
    return path


def read_bounded(path, limit):
    path = Path(path)
    directory(path.parent)
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or getattr(before, "st_file_attributes", 0) & 1024
            or path.resolve(strict=True) != path.absolute() or not 0 <= before.st_size <= limit):
        raise ValueError("Capsule file identity or size differs")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (identity(opened)[:4] != identity(before)[:4]
                or os.name != "nt" and identity(opened) != identity(before)):
            raise ValueError("Capsule opened identity differs")
        raw = stream.read(limit + 1)
        if identity(os.fstat(stream.fileno())) != identity(opened):
            raise ValueError("Capsule opened file changed")
    after = path.lstat()
    if (identity(before) != identity(after) or after.st_nlink != 1
            or not stat.S_ISREG(after.st_mode) or len(raw) != before.st_size):
        raise ValueError("Capsule input changed")
    return raw


def pinned(path, pin, *, eol=False):
    raw = read_bounded(path, pin["bytes"] * (2 if eol else 1))
    lf = raw.replace(b"\r\n", b"\n") if eol else raw
    if eol and (b"\r" in lf or raw not in (lf, lf.replace(b"\n", b"\r\n"))):
        raise ValueError("Capsule source frame differs")
    blob = hashlib.sha1(b"blob " + str(len(lf)).encode() + b"\0" + lf, usedforsecurity=False).hexdigest()
    if (len(lf), digest(lf), blob) != (pin["bytes"], pin["sha256"], pin["Git_blob"]):
        raise ValueError("Capsule pinned source differs")
    return raw


def manifest(repository):
    repository = directory(repository)
    raw = read_bounded(repository / MANIFEST, MANIFEST_PIN[0])
    if (len(raw), digest(raw)) != MANIFEST_PIN:
        raise ValueError("Capsule manifest differs")
    value = decode(raw)
    if (set(value) != {"schema", "parent_commit", "historical", "current", "unit", "identities", "budgets_sha256"}
            or value["schema"] != "legacy-pg-unit-560-v1"
            or value["parent_commit"] != "560fd71f115cf4704073bc9e3f15577dee7a8c9f"
            or len(value["historical"]) != 45 or len(value["current"]) != 46
            or len(set(value["identities"])) != 19):
        raise ValueError("Capsule finite source contract differs")
    for name in CURRENT_REFERENCES:
        pinned(repository / name, value["historical"][name], eol=True)
    return value


def source_photo(repository, source, spec):
    expected = set(spec["historical"])
    directories = {"/".join(name.split("/")[:index]) for name in expected
                   for index in range(1, len(name.split("/")))}
    pending, observed = [source], set()
    while pending:
        for path in pending.pop().iterdir():
            name = path.relative_to(source).as_posix()
            info = path.lstat()
            if path.is_symlink() or getattr(info, "st_file_attributes", 0) & 1024:
                raise ValueError("Capsule source alias")
            if stat.S_ISDIR(info.st_mode) and name in directories:
                pending.append(path)
            elif stat.S_ISREG(info.st_mode) and name in expected:
                observed.add(name)
            else:
                raise ValueError("Additional capsule source is not admitted")
    if observed != expected:
        raise ValueError("Capsule historical source is incomplete")
    records = {}
    for role, base in (("historical", source), ("current", repository)):
        for name, pin in spec[role].items():
            records[role + "/" + name] = digest(pinned(base / name, pin, eol=role == "current"))
    for name in CURRENT_REFERENCES:
        records["current-reference/" + name] = digest(pinned(repository / name, spec["historical"][name], eol=True))
    return records


def _assert_windows_acl(control: int, entries: list, sid: str) -> None:
    if (type(control) is not int or control & 0x1004 != 0x1004 or len(entries) != 2
            or {row[3] for row in entries} != {sid, "S-1-5-18"}
            or any(type(value) is not int for row in entries for value in row[:3])
            or any(row[:3] != (0, 3, 0x1F01FF) for row in entries)):
        raise OSError("Private DACL principals, full-control rights or inheritance differ")


def _set_windows_private_acl(path: Path, sid: str) -> None:
    """Replace the fresh directory DACL; grants alone retain explicit ACEs."""
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(pointer), pointer]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    api.GetSecurityDescriptorDacl.argtypes = [pointer, ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(pointer), ctypes.POINTER(wintypes.BOOL)]
    api.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    api.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        pointer, pointer, pointer, pointer]
    api.SetNamedSecurityInfoW.restype = wintypes.DWORD
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    descriptor, acl = pointer(), pointer()
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"D:P(A;OICI;FA;;;{sid})(A;OICI;FA;;;SY)", 1, ctypes.byref(descriptor), None):
        raise OSError("Cannot construct private DACL")
    try:
        present, defaulted = wintypes.BOOL(), wintypes.BOOL()
        if (not api.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                ctypes.byref(acl), ctypes.byref(defaulted)) or not present or not acl
                or api.SetNamedSecurityInfoW(str(path), 1, 0x80000004,
                    None, None, acl, None) != 0):
            raise OSError("Cannot establish private DACL")
    finally:
        kernel.LocalFree(descriptor)


def _verify_private_boundary(path: Path, sid: str | None) -> None:
    if os.name != "nt":
        if path.stat().st_mode & 0o777 != 0o700 or path.stat().st_uid != os.getuid():
            raise OSError("Private boundary differs")
        return
    import ctypes
    import struct
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        pointer, pointer, ctypes.POINTER(pointer), pointer, ctypes.POINTER(pointer)]
    api.GetNamedSecurityInfoW.restype = wintypes.DWORD
    api.GetSecurityDescriptorControl.argtypes = [pointer, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    api.GetSecurityDescriptorControl.restype = wintypes.BOOL
    api.GetAclInformation.argtypes = [pointer, pointer, wintypes.DWORD, wintypes.DWORD]
    api.GetAclInformation.restype = wintypes.BOOL
    api.GetAce.argtypes = [pointer, wintypes.DWORD, ctypes.POINTER(pointer)]
    api.GetAce.restype = wintypes.BOOL
    api.ConvertSidToStringSidW.argtypes = [pointer, ctypes.POINTER(wintypes.LPWSTR)]
    api.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    descriptor, acl = pointer(), pointer()
    if api.GetNamedSecurityInfoW(str(path), 1, 4, None, None, ctypes.byref(acl), None,
                                 ctypes.byref(descriptor)) != 0:
        raise OSError("Cannot verify private DACL")
    try:
        control, revision = wintypes.WORD(), wintypes.DWORD()
        information = (wintypes.DWORD * 3)()
        if (not acl or not api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision))
                or not api.GetAclInformation(acl, information, ctypes.sizeof(information), 2)):
            raise OSError("Cannot inspect private DACL")
        entries = []
        for index in range(information[0]):
            ace = pointer()
            if not api.GetAce(acl, index, ctypes.byref(ace)):
                raise OSError("Cannot inspect private ACE")
            kind, flags, size, mask = struct.unpack("<BBHI", ctypes.string_at(ace, 8))
            text = wintypes.LPWSTR()
            if size < 16 or not api.ConvertSidToStringSidW(pointer(ace.value + 8), ctypes.byref(text)):
                raise OSError("Cannot inspect private principal")
            try:
                entries.append((kind, flags, mask, text.value))
            finally:
                kernel.LocalFree(ctypes.cast(text, pointer))
        _assert_windows_acl(control.value, entries, sid)
    finally:
        kernel.LocalFree(descriptor)


def fresh(path, repository):
    path = Path(path)
    directory(path.parent)
    if (not path.is_absolute() or path.resolve(strict=False) != path.absolute()
            or path.exists() or path.is_relative_to(repository)):
        raise ValueError("A new external private capsule directory is required")
    path.mkdir(mode=0o700)
    sid = None
    if os.name == "nt":
        result = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                                capture_output=True, text=True, check=True, timeout=10)
        sid = next(csv.reader(io.StringIO(result.stdout)))[1]
        _set_windows_private_acl(path, sid)
    _verify_private_boundary(path, sid)
    return path


def git_blob(repository, oid, size):
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1",
                       GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    with subprocess.Popen(["git", "--no-replace-objects", "-C", str(repository), "cat-file", "blob", oid],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment) as process:
        raw = process.stdout.read(size + 1)
        if len(raw) != size:
            process.kill()
            process.wait(timeout=10)
            raise ValueError("Capsule historical Git blob differs")
        try:
            status = process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            raise ValueError("Capsule historical Git process did not finish") from None
        if status != 0:
            raise ValueError("Capsule historical Git process failed")
    return raw


def materialize(repository, private, spec):
    source = private / "source"
    source.mkdir(mode=0o700)
    for name, pin in spec["historical"].items():
        raw = git_blob(repository, pin["Git_blob"], pin["bytes"])
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open("xb") as stream:
            stream.write(raw)
        pinned(target, pin)
    return source


class ClosedSources(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Only finite authenticated project source; no implicit pyc reader."""
    def __init__(self, repository, source, spec):
        self.repository, self.source, self.spec = repository, source, spec
        self.modules, self.namespaces, self.imported_current = {}, set(), set()
        for role in ("current", "historical"):
            for name in spec[role]:
                if not name.endswith(".py"):
                    continue
                parts = name[:-3].split("/")
                package = parts[-1] == "__init__"
                if package:
                    parts.pop()
                module = ".".join(parts)
                self.modules[module] = (role, name, package)
                self.namespaces.update(".".join(parts[:index]) for index in range(1, len(parts)))

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] not in PROJECT:
            return None
        if fullname in self.modules:
            role, name, package = self.modules[fullname]
            base = self.source if role == "historical" else self.repository
            return importlib.util.spec_from_file_location(fullname, base / name, loader=self,
                submodule_search_locations=[str((base / name).parent)] if package else None)
        if fullname in self.namespaces:
            result = importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
            result.submodule_search_locations = []
            return result
        raise ImportError("Project import outside finite capsule sources")

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        role, name, _package = self.modules[module.__name__]
        base = self.source if role == "historical" else self.repository
        raw = pinned(base / name, self.spec[role][name], eol=role == "current")
        if role == "current":
            self.imported_current.add(name)
        exec(compile(raw, str(base / name), "exec", dont_inherit=True), vars(module))  # noqa: S102 -- finite whole source authenticated before execution, no pyc


class TrustedExternal(importlib.abc.MetaPathFinder):
    """External packages resolve only inside the isolated interpreter prefixes."""
    def __init__(self, repository, source):
        self.roots = tuple({Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()})
        self.excluded = (repository, source, Path.cwd().resolve(), Path(__file__).resolve().parent)

    def allowed(self, name):
        path = Path(name)
        if not path.is_absolute():
            return False
        path = path.resolve()
        return (any(path.is_relative_to(root) for root in self.roots)
                and not any(path.is_relative_to(root) for root in self.excluded))

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in PROJECT:
            raise ImportError("Project import escaped its authenticated loader")
        search = list(sys.path if path is None else path)
        if any(not self.allowed(entry) for entry in search):
            raise ImportError("External import path is outside trusted interpreter roots")
        spec = importlib.machinery.PathFinder.find_spec(fullname, search, target)
        if spec is not None and (spec.origin is not None and not self.allowed(spec.origin)
                or any(not self.allowed(entry) for entry in spec.submodule_search_locations or ())):
            raise ImportError("External module origin is outside trusted interpreter roots")
        return spec


def validate_snapshot(value, spec, helper_sha):
    fields = {"schema", "manifest_sha256", "helper_sha256", "parent_commit", "cases", "budgets",
              "child_exit", "blocked_attempts", "inputs_quiet", "imported_current", "source_photo_sha256",
              "isolated_bootstrap", "external_project_search_paths"}
    if (type(value) is not dict or set(value) != fields or value["schema"] != SCHEMA
            or value["manifest_sha256"] != MANIFEST_PIN[1] or value["helper_sha256"] != helper_sha
            or value["parent_commit"] != spec["parent_commit"] or value["inputs_quiet"] is not True
            or value["isolated_bootstrap"] is not True or value["external_project_search_paths"] is not False
            or type(value["blocked_attempts"]) is not int or value["blocked_attempts"] != 0
            or value["imported_current"] != sorted(spec["current"])
            or type(value["child_exit"]) is not int or value["child_exit"] not in (0, 1)
            or type(value["source_photo_sha256"]) is not str
            or re.fullmatch("[0-9a-f]{64}", value["source_photo_sha256"]) is None):
        raise ValueError("Capsule child authority differs")
    if type(value["cases"]) is not list or [case.get("identity") for case in value["cases"]] != spec["identities"]:
        raise ValueError("Capsule exact nineteen identities differ")
    all_passed = True
    for case in value["cases"]:
        if set(case) != {"identity", "phases"} or set(case["phases"]) != set(PHASES):
            raise ValueError("Capsule child case fields differ")
        phases = case["phases"]
        if (phases["setup"] not in {"passed", "failed", "skipped"}
                or phases["teardown"] not in {"passed", "failed", "skipped"}
                or (phases["call"] not in {"passed", "failed", "skipped"} if phases["setup"] == "passed"
                    else phases["call"] is not None)):
            raise ValueError("Capsule child phases differ")
        all_passed = all_passed and all(outcome == "passed" for outcome in phases.values())
    if (value["child_exit"] == 0) != all_passed:
        raise ValueError("Capsule child exit does not match original outcomes")
    if (type(value["budgets"]) is not list or digest(canonical(value["budgets"])) != spec["budgets_sha256"]
            or len(value["budgets"]) != 29 or sum(row["cases"] for row in value["budgets"]) != 429
            or sum(row["UUIDs"] for row in value["budgets"]) != 69):
        raise ValueError("Capsule original budget rows differ")
    return value


def deny_transports():
    """Installed only in the isolated child; attempted transport fails closed."""
    blocked = []
    def refuse(*_args, **_kwargs):
        blocked.append(True)
        raise RuntimeError("Capsule forbids SQL and service transport")
    def audit(event, _args):
        if event in {"sqlite3.connect", "socket.connect", "socket.bind", "subprocess.Popen"}:
            refuse()
    sys.addaudithook(audit)
    import psycopg2
    import sqlalchemy.engine
    sqlalchemy.engine.Engine.connect = refuse
    psycopg2.connect = refuse
    return blocked


def child(repository, source, private, helper_sha):
    if not sys.flags.isolated or not sys.flags.ignore_environment or not sys.flags.no_user_site:
        raise ValueError("The child requires an isolated interpreter from startup")
    if any(name in sys.modules for name in ("tests", "web", "config")):
        raise ValueError("Capsule child inherited project imports")
    spec = manifest(repository)
    helper_raw = read_bounded(Path(__file__).absolute(), 98304)
    if digest(helper_raw) != helper_sha:
        raise ValueError("Capsule child helper differs")
    before = source_photo(repository, source, spec)
    finder = ClosedSources(repository, source, spec)
    external = TrustedExternal(repository, source)
    if any(not external.allowed(entry) for entry in sys.path):
        raise ValueError("The isolated bootstrap has an untrusted search path")
    # Project source is served solely by the pinned loader. Preserve only the
    # builtin/frozen mechanisms and the bounded external path resolver.
    sys.meta_path[:] = [finder, external, importlib.machinery.BuiltinImporter,
                        importlib.machinery.FrozenImporter]
    from tests.isolation import block_external_sockets, prepare_environment
    prepare_environment()
    block_external_sockets()
    blocked = deny_transports()
    import pytest
    reports = {}
    class Reports:
        def pytest_runtest_logreport(self, report):
            prefix = spec["unit"] + "::"
            if not report.nodeid.startswith(prefix) or report.when not in PHASES:
                raise ValueError("Capsule unreviewed report")
            name = report.nodeid.removeprefix(prefix)
            if name not in spec["identities"] or report.when in reports.setdefault(name, {}):
                raise ValueError("Capsule duplicate or foreign report")
            reports[name][report.when] = report.outcome
    code = int(pytest.main(["--noconftest", "--import-mode=importlib", "--assert=plain", "--rootdir", str(source),
        "-q", "--tb=short", str(source / spec["unit"]),
        "-o", "cache_dir=" + str(private / "cache"), "--basetemp=" + str(private / "pytest-data")], plugins=[Reports()]))
    from tests.ci_web37 import pg_lease
    budgets = pg_lease.budgets()
    after = source_photo(repository, source, spec)
    cases = [{"identity": name, "phases": {phase: reports.get(name, {}).get(phase) for phase in PHASES}}
             for name in spec["identities"]]
    result = {"schema": SCHEMA, "manifest_sha256": MANIFEST_PIN[1], "helper_sha256": helper_sha,
              "parent_commit": spec["parent_commit"], "cases": cases, "budgets": budgets, "child_exit": code,
              "blocked_attempts": len(blocked), "inputs_quiet": before == after,
              "isolated_bootstrap": bool(sys.flags.isolated),
              "external_project_search_paths": any(not external.allowed(entry) for entry in sys.path),
              "imported_current": sorted(finder.imported_current), "source_photo_sha256": digest(canonical(after))}
    validate_snapshot(result, spec, helper_sha)
    with (private / "snapshot.json").open("xb") as stream:
        stream.write(canonical(result) + b"\n")
    return code


class Snapshot:
    """Opaque process receipt; the public API never accepts a fabricated dict."""
    def __init__(self, value, private, helper_sha, *, issued):
        if issued is not _ISSUED:
            raise ValueError("An actual child invocation must issue the snapshot")
        self._sha256 = digest(canonical(value) + b"\n")
        self._private, self._helper_sha = private, helper_sha

    def checked(self, repository, spec):
        if digest(read_bounded(Path(__file__).absolute(), 98304)) != self._helper_sha:
            raise ValueError("Snapshot helper source changed")
        raw = read_bounded(self._private / "snapshot.json", 65536)
        if digest(raw) != self._sha256:
            raise ValueError("Original child snapshot changed")
        value = validate_snapshot(decode(raw), spec, self._helper_sha)
        photos = source_photo(Path(repository), self._private / "source", spec)
        if digest(canonical(photos)) != value["source_photo_sha256"]:
            raise ValueError("Reused snapshot current source differs")
        return value


def child_command(helper, repository, source, private, helper_sha):
    """-I removes script directory, cwd, PYTHONPATH and user site before imports."""
    return [sys.executable, "-I", "-B", "-X", "utf8", str(helper), "--child",
            "--repository", str(repository), "--source", str(source), "--private", str(private),
            "--helper-sha", helper_sha]


def snapshot(repository, new_absolute_private):
    repository = directory(repository)
    spec = manifest(repository)
    # Authenticate current dependencies before creating or executing the child.
    current_before = {name: digest(pinned(repository / name, pin, eol=True)) for name, pin in spec["current"].items()}
    private = fresh(new_absolute_private, repository)
    source = materialize(repository, private, spec)
    before = source_photo(repository, source, spec)
    helper = Path(__file__).absolute()
    helper_raw = read_bounded(helper, 98304)
    helper_sha = digest(helper_raw)
    environment = {key: value for key, value in os.environ.items()
        if not key.startswith(("PYTEST_", "COVERAGE_")) and key not in {"PYTHONPATH", "PYTHONSTARTUP"}}
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONNOUSERSITE="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONPATH="", _METODOBASE_TEST_ROOT=str(private / "metodobase-test-data"))
    environment.update({key: str(private) for key in ("TEMP", "TMP", "TMPDIR")})
    with (private / "child.private.log").open("xb") as stream:
        process = subprocess.run(child_command(helper, repository, source, private, helper_sha),
            cwd=source, env=environment, stdout=stream,
            stderr=subprocess.STDOUT, timeout=90, check=False)
    after = source_photo(repository, source, spec)
    if (before != after or current_before != {name: after["current/" + name] for name in spec["current"]}
            or read_bounded(helper, 98304) != helper_raw):
        raise ValueError("Capsule source changed during child execution")
    value = validate_snapshot(decode(read_bounded(private / "snapshot.json", 65536)), spec, helper_sha)
    if value["child_exit"] != process.returncode or value["source_photo_sha256"] != digest(canonical(after)):
        raise ValueError("Capsule child receipt differs from actual process")
    return Snapshot(value, private, helper_sha, issued=_ISSUED)


def historical_budget_rows(repository, new_absolute_private, *, snapshot=None):
    """Return real original29 rows; never a constant or a serial-global patch."""
    if snapshot is None:
        snapshot = globals()["snapshot"](repository, new_absolute_private)
    if type(snapshot) is not Snapshot:
        raise ValueError("An original child process snapshot is required")
    value = snapshot.checked(repository, manifest(repository))
    if value["child_exit"] != 0:
        raise ValueError("Original legacy unit did not pass")
    return deepcopy(value["budgets"])


def collector(module_path, parent):
    """Delegate nineteen IDs without importing the failing serial unit."""
    import pytest
    class LegacyFile(pytest.File):
        value = None
        attempted = False
        failed = False
        def result(self):
            if not self.attempted:
                self.attempted = True
                temporary = directory(Path(tempfile.gettempdir()).resolve())
                private = Path(tempfile.mkdtemp(prefix="metodobase-legacy-parent-", dir=temporary)) / "capsule"
                try:
                    self.value = snapshot(ROOT, private)
                except (ValueError, OSError, ImportError, KeyError, TypeError, subprocess.SubprocessError):
                    self.failed = True
                self.config._web41_bindings.append({"module": "tests.test_ci_web37_pg_legacy",
                    "validation_scope": "original_unit19_and_budget_validators_in_isolated_historical_child",
                    "delegation_explicit": True, "original_source_modified_by_dispatch": False,
                    "child_receipt_verified": not self.failed,
                    "manifest_sha256": MANIFEST_PIN[1], "original_identities_retained": 19})
            if self.failed:
                raise ValueError("Isolated legacy child did not yield a verified receipt")
            return self.value.checked(ROOT, manifest(ROOT))
        def collect(self):
            for name in manifest(ROOT)["identities"]:
                yield LegacyItem.from_parent(self, name=name)
    class LegacyItem(pytest.Item):
        def phase(self, phase):
            value = next(case for case in self.parent.result()["cases"] if case["identity"] == self.name)
            outcome = value["phases"][phase]
            if outcome == "failed":
                raise AssertionError("Original isolated legacy unit failed in " + phase)
            if outcome == "skipped":
                pytest.skip("Original isolated legacy unit skipped in " + phase)
            if outcome != "passed":
                raise ValueError("Isolated legacy unit phase was not executed")
        def setup(self):
            self.phase("setup")
        def runtest(self):
            self.phase("call")
        def teardown(self):
            self.phase("teardown")
        def reportinfo(self):
            return self.parent.path, 0, self.name
    return LegacyFile.from_parent(parent, path=module_path)


class QuietParser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("Invalid capsule CLI")


def main():
    parser = QuietParser(allow_abbrev=False)
    parser.add_argument("--child", action="store_true", required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--helper-sha", required=True)
    args = parser.parse_args()
    return child(directory(args.repository), directory(args.source), directory(args.private), args.helper_sha)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError, KeyError, TypeError):
        raise SystemExit(2) from None
