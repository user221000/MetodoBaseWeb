"""Observe only an authenticated historical member run; keep its failure.

The original driver executes unchanged, including every check and finalizer.
Only builtin error types and authenticated source locations can be emitted.
Private paths are capabilities in RAM, never fields of the diagnostic JSON.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import sys
import tempfile
from pathlib import Path
from types import CodeType

SUPPORT_PIN = (23850, '1d6c6371b55fe55bd7b02ef4f99738697134d6081fee29482b151856df502178')
DRIVERS = {"31": "tests/e2e/run_member_link31_browser.py", "33": "tests/e2e/run_member_link33_browser.py"}


def load_support():
    import hashlib

    path = Path(__file__).absolute().with_name("historical_failure_metadata.py")
    before = path.lstat()
    if (path.resolve(strict=True) != path or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or getattr(before, "st_file_attributes", 0) & 1024 or before.st_size != SUPPORT_PIN[0]):
        raise ValueError("Diagnostic support identity differs")
    fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or fingerprint(opened)[:4] != fingerprint(before)[:4]
                or os.name != "nt" and fingerprint(opened) != fingerprint(before)):
            raise ValueError("Diagnostic opened support identity differs")
        raw = stream.read(SUPPORT_PIN[0] + 1)
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(opened):
            raise ValueError("Diagnostic opened support changed")
    after = path.lstat()
    if (fingerprint(before) != fingerprint(after) or after.st_nlink != 1
            or not stat.S_ISREG(after.st_mode) or getattr(after, "st_file_attributes", 0) & 1024
            or path.resolve(strict=True) != path or (len(raw), hashlib.sha256(raw).hexdigest()) != SUPPORT_PIN):
        raise ValueError("Diagnostic support source differs")
    spec = importlib.util.spec_from_file_location("historical_failure_metadata_support", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102 -- execute only whole pinned support bytes already read with a bound
    return module


class MemberObserver:
    """Trace one exact CodeType and one exact execution namespace only."""
    def __init__(self, support, registry, namespace):
        self.support, self.registry, self.namespace = support, registry, namespace
        self.driver = DRIVERS[registry.schema]
        self.code = next(code for code in registry.codes[self.driver] if code.co_name == "run")
        self.kind, self.frames, self.phase = "OTHER", [], None
        self.observed, self.rejected = False, False
        self.previous = None

    def __enter__(self):
        self.previous = sys.gettrace()
        if self.previous is not None:
            raise ValueError("An existing trace cannot be replaced")
        sys.settrace(self)
        return self

    def __exit__(self, _kind, _value, _traceback):
        sys.settrace(self.previous)
        return False

    def __call__(self, frame, event, argument):
        if (frame.f_code != self.code or frame.f_code.co_filename != self.code.co_filename
                or frame.f_globals is not self.namespace):
            return None
        if event == "exception":
            try:
                error = frame.f_locals.get("failure")
                if not isinstance(error, BaseException):
                    error = argument[1]
                self.kind = self.support.exception_kind(error)
                self.frames = self.registry.traceback(error)
                self.observed = True
                phase = frame.f_locals.get("phase")
                if (type(phase) is type(self.registry.root) and phase.is_absolute()
                        and phase.name.startswith("metodobase-member31-browser-")
                        and phase.is_relative_to(Path(tempfile.gettempdir()).resolve())):
                    self.phase = phase
            except (OSError, ValueError, TypeError, AttributeError, LookupError, RuntimeError, MemoryError):
                self.rejected = True
        return self

    def payload(self, failed):
        value = self.support.empty(self.registry, "runtime_observer")
        if failed:
            value["exception_type"], value["frames"] = self.kind, self.frames
            if not self.observed or not self.frames:
                value["issues"].append("unmapped_failure")
        else:
            value["issues"].append("no_exception_observed")
        if self.rejected:
            value["issues"].append("observer_rejected")
        if failed and self.phase is not None:
            try:
                self.support.private_directory(self.phase)
                for role, name in (("fixture_log", "fixture.private.log"), ("driver_log", "driver.private.log")):
                    path = self.phase / name
                    if path.exists():
                        raw, _ = self.support.read_bounded(path, self.support.MAX_PRIVATE)
                        value["private_artifacts"].append(self.support.artifact(self.registry, role, raw))
            except (OSError, ValueError, TypeError, MemoryError, RecursionError):
                value["issues"].append("private_log_unavailable")
        value["source_unchanged"] = self.registry.quiet()
        value["diagnostic_accepted"] = failed and not value["issues"]
        return value


def execute_member(source, schema, output, port, metadata_output):
    if any(name in sys.modules for name in ("tests", "config", "web")):
        raise ValueError("Historical member observation requires a standalone process")
    support = load_support()
    registry = support.SourceRegistry(source, schema)
    if schema not in DRIVERS or type(port) is not int or not 1024 < port < 65536:
        raise ValueError("Historical member invocation differs")
    for path in (Path(output), Path(metadata_output)):
        support.directory(path.parent)
        if (not path.is_absolute() or path.resolve(strict=False) != path.absolute()
                or path.is_relative_to(registry.root) or path.exists()):
            raise ValueError("Fresh external member outputs required")
    original = registry.raw[DRIVERS[schema]]
    filename = str(registry.root / DRIVERS[schema])
    code = compile(original, filename, "exec", dont_inherit=True)
    if not isinstance(code, CodeType) or code != registry.codes[DRIVERS[schema]][0]:
        raise ValueError("Historical member whole CodeType differs")
    namespace = {"__file__": filename, "__name__": "__main__", "__package__": None}
    observer = MemberObserver(support, registry, namespace)
    previous_path, previous_argv, previous_cwd = list(sys.path), list(sys.argv), Path.cwd()
    failed = False
    try:
        os.chdir(registry.root)
        sys.path.insert(0, str(registry.root))
        sys.argv = [filename, "--output", str(output), "--port", str(port)]
        with observer:
            exec(code, namespace)  # noqa: S102 -- complete pinned historical member source, no rewrite
    except BaseException:
        failed = True
        raise
    finally:
        sys.path[:] = previous_path
        sys.argv[:] = previous_argv
        os.chdir(previous_cwd)
        try:
            support.write_metadata(metadata_output, registry, observer.payload(failed))
        except BaseException:  # noqa: BLE001 -- diagnostic I/O must not replace an active historical failure
            if not failed:
                raise RuntimeError("Member diagnostic could not be retained") from None


def main():
    support = load_support()
    parser = support.PrivateParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--schema", choices=tuple(DRIVERS), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--failure-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    execute_member(args.source, args.schema, args.output, args.port, args.failure_metadata)


def quiet_exception(_kind, _value, _traceback):
    """Keep CPython's original nonzero status without printing private values."""


if __name__ == "__main__":
    sys.excepthook = quiet_exception
    main()
