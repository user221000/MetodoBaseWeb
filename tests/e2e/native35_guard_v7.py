"""New finite admission and own-instance stop ports; no SQL or process on import."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = Path("C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-pg-cluster-private-20261021-v1/env.private.json")
PROFILE_SHA = "693631b8edeb9c714d06fb4833c1e3ebef45d1afe2b3db134fdf7742d70d3252"
SOURCE = "50325b464169fc750d9f39e339d874a716030797"
GENERATION = re.compile(r"[0-9a-f]{32}\Z")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate private control key")
        value[key] = item
    return value


def private_json(path, limit=65536):
    path = Path(path)
    if (not path.is_file() or path.is_symlink()
            or getattr(path.lstat(), "st_file_attributes", 0) & 0x400
            or path.stat().st_size > limit):
        raise ValueError("Private control is not a bounded regular file")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Private control exceeded its bound")
    return json.loads(raw, object_pairs_hook=unique)


def validate_ack(value, expected, now=None):
    """Pure typed finite contract; cleanup deliberately does not call this."""
    if set(value) != set(expected) | {"granted", "expires_at_UTC"}:
        raise ValueError("Unexpected Root ACK fields")
    if value["granted"] is not True:
        raise ValueError("Root ACK not granted")
    if type(value.get("UUIDs")) is not int or value["UUIDs"] != 1:
        raise ValueError("Root UUID budget differs")
    if (type(value.get("expected_groups")) is not list
            or any(type(item) is not int for item in value["expected_groups"])):
        raise ValueError("Root group contract is not typed")
    for key, item in expected.items():
        if value[key] != item:
            raise ValueError("Root ACK binding differs")
    if not isinstance(value["expires_at_UTC"], str):
        raise TypeError("Root ACK expiry is not explicit")
    expiry = datetime.fromisoformat(value["expires_at_UTC"])
    instant = datetime.now(UTC) if now is None else now
    if expiry.tzinfo is None or instant.tzinfo is None:
        raise ValueError("Root ACK expiry must be timezone aware")
    if not 0 < (expiry - instant).total_seconds() <= 4 * 3600:
        raise ValueError("Root ACK expired or exceeds four hours")
    return value


def source_context():
    head = subprocess.check_output(["git", "--no-replace-objects", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "--no-replace-objects", "diff", "--quiet", SOURCE, "--",
                    "web", "api", "core", "config", "utils", "src", "static", "fonts"], cwd=ROOT, check=True)
    return head


def require_ack(task, phase, now=None):
    if phase not in {"sql", "chrome"}:
        raise ValueError("Unknown native35 admission phase")
    task = Path(task).resolve()
    preflight_path = task / "native-preflight.json"
    preflight = private_json(preflight_path, 8 * 1024 * 1024)
    if (preflight["schema"] != "native35-v7" or preflight["product_source"] != SOURCE
            or preflight["source_head"] != source_context()
            or preflight["profile_path"] != str(PROFILE)
            or preflight["profile_sha256"] != PROFILE_SHA
            or digest(PROFILE.read_bytes()) != PROFILE_SHA):
        raise ValueError("Native35 source/profile context differs")
    expected = {"scope": "native35-v7-" + phase, "source_head": preflight["source_head"],
                "product_source": SOURCE, "selection": "current35", "expected_groups": [15, 18, 2],
                "UUIDs": 1, "preflight_sha256": digest(preflight_path.read_bytes()),
                "profile_sha256": PROFILE_SHA,
                "launcher_sha256": digest((ROOT / "tests/e2e/run_native35_qa_v7.py").read_bytes()),
                "fixture_sha256": digest((ROOT / "tests/e2e/native35_postgres_server_v7.py").read_bytes()),
                "guard_sha256": digest(Path(__file__).read_bytes())}
    if phase == "chrome":
        expected["startup_sha256"] = digest((task / "private/startup.json").read_bytes())
    path = task / ("native-" + phase + "-ack.json")
    validate_ack(private_json(path), expected, now)
    return digest(path.read_bytes())


def admitted_phase(check, launch):
    """Readmission occurs immediately before each new child; no finally guard."""
    check()
    return launch()


def require_chrome_phase(task):
    # The new browser may cause real SQL through HTTP, so both leases must hold.
    return {phase: require_ack(task, phase) for phase in ("sql", "chrome")}


class PrivateStop:
    """Exactly four instance-bound keys, with own process birth checked locally."""

    def __init__(self, private, pid, generation, source_commit, birth, identity):
        if (type(pid) is not int or pid <= 0 or not GENERATION.fullmatch(generation)
                or not re.fullmatch(r"[0-9a-f]{40}", source_commit)):
            raise ValueError("Invalid own stop identity")
        self.path = Path(private) / "stop-request.private.json"
        self.pid, self.generation, self.source = pid, generation, source_commit
        self.birth, self.identity = birth, identity
        self.accepted = False
        self.refusals = 0
        self.last_error_class = None

    def inspect(self):
        if not self.path.exists():
            return False
        try:
            value = private_json(self.path, 4096)
            if (type(value) is not dict or set(value) != {"action", "pid", "generation", "source_commit"}
                    or value["action"] != "stop" or type(value["pid"]) is not int
                    or value["pid"] != self.pid or value["generation"] != self.generation
                    or value["source_commit"] != self.source
                    or self.identity() != (self.pid, self.birth)):
                raise ValueError("Private stop identity mismatch")
            self.accepted = True
            return True
        except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
            self.refusals = min(1000, self.refusals + 1)
            self.last_error_class = type(error).__name__
            return False


def stop_receipt(closed, started, returned, joined, guard, error_class):
    accepted = guard is not None and guard.accepted is True
    return {"server_started": started is True, "normal_return": returned is True,
            "watcher_stopped_joined": joined is True, "stop_request_accepted": accepted,
            "stop_refusals": guard.refusals if guard is not None else 0,
            "error_class": error_class,
            "normal_shutdown_accepted": all(item is True for item in (closed, started, returned, joined, accepted)) and error_class is None}


def _api():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    api.OpenProcess.restype = ctypes.c_void_p
    api.CloseHandle.argtypes = [ctypes.c_void_p]
    api.GetProcessTimes.argtypes = [ctypes.c_void_p, *([ctypes.c_void_p] * 4)]
    return api


def _birth(handle):
    times = [ctypes.c_ulonglong() for _ in range(4)]
    if not _api().GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
        raise ValueError("Owned process birth unavailable")
    return times[0].value


def _fact(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("Owned PID invalid")
    code = "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(pid) + "';if($null -eq $p){throw 'Owned process absent'};$p|Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate|ConvertTo-Json -Compress"
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
                            capture_output=True, check=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.stderr.strip():
        raise ValueError("Owned process observation failed")
    value = json.loads(result.stdout.decode("utf-8-sig"))
    value["executable_sha256"] = digest(Path(value["ExecutablePath"]).read_bytes())
    return value


def _argv(command):
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not pointer:
        raise ValueError("Owned argument vector unavailable")
    try:
        return [pointer[index] for index in range(count.value)]
    finally:
        api = _api()
        api.LocalFree.argtypes = [ctypes.c_void_p]
        api.LocalFree(ctypes.cast(pointer, ctypes.c_void_p))


def verify_listener(pid):
    code = "[pscustomobject]@{rows=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object {$_.LocalPort -eq 8802}|Select-Object LocalAddress,LocalPort,OwningProcess)}|ConvertTo-Json -Depth 5 -Compress"
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
                            capture_output=True, check=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    value = json.loads(result.stdout.decode("utf-8-sig"))["rows"]
    if (result.stderr.strip() or not value
            or any(row != {"LocalAddress": "127.0.0.1", "LocalPort": 8802, "OwningProcess": pid} for row in value)):
        raise ValueError("Actual listener is not the owned fixture worker")
    return value


class OwnedWorker:
    """Retain the worker kernel object, then revalidate birth/argv before stop."""

    def __init__(self, startup, expected_args, wrapper_pid, base_executable):
        self.startup = startup
        self.handle = _api().OpenProcess(0x00100000 | 0x1000, False, startup["pid"])
        if not self.handle:
            raise ValueError("Cannot retain own worker HANDLE")
        try:
            self.fact = _fact(startup["pid"])
            if (_birth(self.handle) != startup["process_birth"]
                    or Path(self.fact["ExecutablePath"]).resolve() not in {Path(expected_args[0]).resolve(), Path(base_executable).resolve()}
                    or _argv(self.fact["CommandLine"])[1:] != expected_args[1:]
                    or (self.fact["ProcessId"] != wrapper_pid and self.fact["ParentProcessId"] != wrapper_pid)):
                raise ValueError("Own worker generation/executable/argv/parent differs")
        except BaseException:
            self.close()
            raise

    def request_stop(self, private):
        # No start-lease/expiry check: closing this exact owned instance is allowed.
        private = Path(private)
        if _birth(self.handle) != self.startup["process_birth"] or _fact(self.startup["pid"]) != self.fact:
            raise ValueError("Owned worker identity changed before cleanup")
        identity = private_json(private / "native35-instance.private.json")
        for key in ("pid", "process_birth", "generation", "source_commit"):
            if identity[key] != self.startup[key]:
                raise ValueError("Owned metadata generation changed")
        packet = {"action": "stop", "pid": identity["pid"], "generation": identity["generation"],
                  "source_commit": identity["source_commit"]}
        pending, target = private / "stop-request.pending.private.json", private / "stop-request.private.json"
        if target.exists():
            raise ValueError("Own stop request already exists")
        with pending.open("xb") as stream:
            stream.write((json.dumps(packet) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        pending.rename(target)

    def close(self):
        if self.handle:
            _api().CloseHandle(self.handle)
            self.handle = None
