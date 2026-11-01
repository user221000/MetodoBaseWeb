"""Opt-in, file-controlled ASGI admission barrier and process drain counter.

No database, framework, request identity, logging, or HTTP control mutations.
The operator must atomically replace a private local regular control file.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import stat
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


ASGIApp = Callable[[dict[str, Any], Callable[..., Awaitable[Any]],
                    Callable[..., Awaitable[Any]]], Awaitable[None]]
CONTROL_ENV = "METODOBASE_MAINTENANCE_FILE"
STATUS_PATH = "/__metodobase_maintenance"
TOKEN_HEADER = b"x-metodobase-maintenance"
MAX_CONTROL_BYTES = 4096
HEALTH_PATHS = frozenset(("/health", "/health/ready"))
_HEX_TOKEN = re.compile(r"[0-9a-fA-F]{64}\Z", re.ASCII)
_CONTROL_KEYS = frozenset(("version", "active", "token", "operation"))


@dataclass(frozen=True, repr=False)
class _Control:
    valid: bool
    active: bool
    token: bytes | None = field(default=None, repr=False)
    operation: str | None = None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate control key")
        result[key] = value
    return result


def _read_control(path: str) -> _Control:
    """Read at most 4 KiB, without following symlinks where OS supports it.

    Never preserve an earlier token after an invalid/deleted control file.
    Read errors have no diagnostic text, paths, or file content in responses.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return _Control(valid=False, active=True)
    try:
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CONTROL_BYTES:
                return _Control(valid=False, active=True)
            raw = stream.read(MAX_CONTROL_BYTES + 1)
        if len(raw) > MAX_CONTROL_BYTES:
            return _Control(valid=False, active=True)
        data = json.loads(raw.decode("utf8"), object_pairs_hook=_unique_object)
        if not isinstance(data, dict) or set(data) != _CONTROL_KEYS:
            return _Control(valid=False, active=True)
        if type(data["version"]) is not int or data["version"] != 1:
            return _Control(valid=False, active=True)
        if type(data["active"]) is not bool:
            return _Control(valid=False, active=True)
        token, operation = data["token"], data["operation"]
        if not isinstance(token, str) or not _HEX_TOKEN.fullmatch(token):
            return _Control(valid=False, active=True)
        if not isinstance(operation, str) or str(uuid.UUID(operation)) != operation:
            return _Control(valid=False, active=True)
        return _Control(valid=True, active=data["active"],
                        token=token.encode("ascii"), operation=operation)
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        return _Control(valid=False, active=True)


def _authorized(scope: dict[str, Any], state: _Control) -> bool:
    if scope.get("method") != "GET" or not state.valid or not state.token:
        return False
    values = [value for key, value in scope.get("headers", ())
              if key.lower() == TOKEN_HEADER]
    # Duplicate credentials are ambiguous and are never accepted.
    if len(values) != 1 or not isinstance(values[0], bytes) or len(values[0]) != 64:
        return False
    return hmac.compare_digest(values[0], state.token)


async def _respond(scope: dict[str, Any], send: Callable[..., Awaitable[Any]],
                   status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store, max-age=0"),
        (b"pragma", b"no-cache"),
        (b"expires", b"0"),
        (b"referrer-policy", b"no-referrer"),
        (b"x-content-type-options", b"nosniff"),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body",
                "body": b"" if scope.get("method") == "HEAD" else body})


class MaintenanceGate:
    """One admission authority shared by a process's HTTP and explicit jobs."""

    def __init__(self, *, control_file: str | None = None) -> None:
        self._control_file = (os.environ.get(CONTROL_ENV, "")
                              if control_file is None else control_file)
        self._lock = threading.Lock()
        self._active_requests = 0
        self._active_jobs = 0
        self._background_probes: dict[str, Callable[[], int]] = {}

    def register_background_probe(self, name: str, probe: Callable[[], int]) -> None:
        """Attach a bounded read-only pending counter; never remove on close.

        Probes run under this Gate's lock and must not perform I/O or acquire
        the Gate themselves. Dispatcher callbacks must never take this lock.
        Callers use a non-personal name containing the dispatcher's identity
        and capture that exact object. Reentering lifespan may add another
        instance; retaining the old probe covers its still-running jobs.
        """
        if not isinstance(name, str) or not name or len(name) > 64 or not callable(probe):
            raise ValueError("Invalid background counter probe")
        with self._lock:
            self._background_probes[name] = probe

    def _job_count(self) -> int:
        # Caller holds Gate lock. Current probes only read Dispatcher.pending,
        # whose short lock is never held while acquiring the Gate elsewhere.
        count = self._active_jobs
        for probe in self._background_probes.values():
            value = probe()
            if type(value) is not int or value < 0:
                raise ValueError("Invalid background counter")
            count += value
        return count

    @contextmanager
    def background_admission(self):
        """Yield admission once, then count the entire explicitly guarded job.

        An already admitted job drains normally when the file becomes active.
        A paused/invalid-file job yields False: callers MUST skip all writes.
        The context manager does not cancel work or open a database session.
        """
        if not self._control_file:
            yield True
            return
        with self._lock:
            state = _read_control(self._control_file)
            admitted = state.valid and not state.active
            if admitted:
                self._active_jobs += 1
        try:
            yield admitted
        finally:
            if admitted:
                with self._lock:
                    self._active_jobs -= 1


class MaintenanceMiddleware:
    """Track admitted HTTP until the complete inner ASGI call has ended.

    Register last with ``app.add_middleware`` so every existing user
    middleware and its background work remain inside this await boundary.
    Counter is process-local, not a distributed quiescence assertion.
    """

    def __init__(self, app: ASGIApp, *, gate: MaintenanceGate | None = None,
                 control_file: str | None = None) -> None:
        if gate is not None and control_file is not None:
            raise ValueError("Use one shared gate or a control file, not both")
        self.app = app
        self.gate = gate if gate is not None else MaintenanceGate(control_file=control_file)

    async def __call__(self, scope: dict[str, Any],
                       receive: Callable[..., Awaitable[Any]],
                       send: Callable[..., Awaitable[Any]]) -> None:
        gate = self.gate
        if scope.get("type") != "http" or not gate._control_file:
            await self.app(scope, receive, send)
            return

        diagnostic = scope.get("path") == STATUS_PATH
        # Read and admission increment share the same short lock. A diagnostic
        # cannot overtake an admission that already read the inactive file.
        # This is a bounded local file read; no await or application call here.
        with gate._lock:
            state = _read_control(gate._control_file)
            if diagnostic:
                allowed = _authorized(scope, state)
                snapshot = None
                if allowed:
                    try:
                        jobs = gate._job_count()
                        snapshot = {"active": state.active,
                                    "active_requests": gate._active_requests,
                                    "active_jobs": jobs,
                                    "pid": os.getpid(), "operation": state.operation,
                                    "drained": (state.valid and state.active
                                                and gate._active_requests == 0
                                                and jobs == 0)}
                    except Exception:
                        # Do not expose probe errors or certify quiescence
                        # when a real queued/running counter cannot be read.
                        snapshot = None
                admitted = False
            else:
                health = (scope.get("method") in {"GET", "HEAD"}
                          and scope.get("path") in HEALTH_PATHS)
                admitted = state.valid and (not state.active or health)
                if admitted:
                    gate._active_requests += 1

        if diagnostic:
            if not allowed:
                await _respond(scope, send, 404, {"detail": "Not Found"})
            elif snapshot is None:
                await _respond(scope, send, 503, {"detail": "No se pudo confirmar el drenaje"})
            else:
                await _respond(scope, send, 200, snapshot)
            return
        if not admitted:
            await _respond(scope, send, 503, {"detail": "Servicio en mantenimiento"})
            return
        try:
            # Do not end accounting at response.start/body. ASGI BackgroundTasks
            # and streaming finalizers can still perform writes after them.
            await self.app(scope, receive, send)
        finally:
            with gate._lock:
                gate._active_requests -= 1
