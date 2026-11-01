"""Local focused ASGI tests; no database, accounts, network or production."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import secrets
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from web.middleware.maintenance import MaintenanceGate, MaintenanceMiddleware, STATUS_PATH, TOKEN_HEADER


TOKEN = secrets.token_hex(32)  # Per-process synthetic credential; never logged.
OPERATION = "75241c7c-2078-4f45-a869-979fb1906806"


def scope(path="/api/example", method="POST", headers=None):
    return {"type": "http", "asgi": {"version": "3.0"},
            "http_version": "1.1", "scheme": "https", "method": method,
            "path": path, "raw_path": path.encode(), "query_string": b"",
            "root_path": "", "server": ("test.invalid", 443),
            "client": ("127.0.0.1", 1), "headers": headers or []}


async def response(app, request_scope=None, events=None):
    collected = [] if events is None else events

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        collected.append(message)

    await app(scope() if request_scope is None else request_scope, receive, send)
    return collected


def result(events):
    head = next(event for event in events if event["type"] == "http.response.start")
    raw = b"".join(event.get("body", b"") for event in events
                   if event["type"] == "http.response.body")
    return head["status"], (json.loads(raw) if raw else None), dict(head["headers"])


async def inner_ok(request_scope, receive, send):
    await send({"type": "http.response.start", "status": 201, "headers": []})
    await send({"type": "http.response.body", "body": b'{"ok":true}'})


class MaintenanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(prefix="maintenance-unit-")
        self.addCleanup(self.sandbox.cleanup)
        self.path = Path(self.sandbox.name) / "control.json"

    def control(self, active=False, **overrides):
        data = {"version": 1, "active": active, "token": TOKEN,
                "operation": OPERATION}
        data.update(overrides)
        staged = self.path.with_suffix(".replacement")
        staged.write_text(json.dumps(data), encoding="utf8")
        os.replace(staged, self.path)

    def wrapped(self, app=inner_ok):
        return MaintenanceMiddleware(app, control_file=str(self.path))

    async def status(self, app, token=TOKEN, method="GET", headers=None):
        credentials = [(TOKEN_HEADER, token.encode())] if headers is None else headers
        return result(await response(app, scope(STATUS_PATH, method, credentials)))

    async def test_unset_is_exact_passthrough_without_diagnostic(self):
        seen = []

        async def app(request_scope, receive, send):
            seen.append(request_scope)
            await inner_ok(request_scope, receive, send)

        with patch.dict(os.environ, {}, clear=True):
            wrapped = MaintenanceMiddleware(app)
        request_scope = scope(STATUS_PATH, "GET")
        self.assertEqual(result(await response(wrapped, request_scope))[0], 201)
        self.assertIs(seen[0], request_scope)

    async def test_empty_optin_is_disabled(self):
        wrapped = MaintenanceMiddleware(inner_ok, control_file="")
        self.assertEqual(result(await response(wrapped))[0], 201)

    async def test_configured_missing_file_denies_without_diagnostic_authority(self):
        wrapped = self.wrapped()
        self.assertEqual(result(await response(wrapped))[0], 503)
        self.assertEqual(result(await response(wrapped, scope("/health", "GET")))[0], 503)
        self.assertEqual((await self.status(wrapped))[0], 404)

    async def test_explicit_none_with_env_unset_is_exact_passthrough(self):
        with patch.dict(os.environ, {}, clear=True):
            wrapped = MaintenanceMiddleware(inner_ok, control_file=None)
        self.assertEqual(result(await response(wrapped))[0], 201)
        self.assertEqual(result(await response(wrapped, scope(STATUS_PATH, "GET")))[0], 201)

    async def test_inactive_authenticated_snapshot_exact_safe_fields(self):
        self.control()
        status, body, headers = await self.status(self.wrapped())
        self.assertEqual(status, 200)
        self.assertEqual(body, {"active": False, "active_requests": 0,
                                "active_jobs": 0, "drained": False,
                                "pid": os.getpid(), "operation": OPERATION})
        self.assertNotIn(TOKEN, json.dumps([body, list(headers.items())], default=str))
        self.assertEqual(headers[b"cache-control"], b"no-store, max-age=0")

    async def test_env_captured_at_construction(self):
        self.control(active=True)
        with patch.dict(os.environ, {"METODOBASE_MAINTENANCE_FILE": str(self.path)}):
            wrapped = MaintenanceMiddleware(inner_ok)
        with patch.dict(os.environ, {"METODOBASE_MAINTENANCE_FILE": ""}):
            self.assertEqual(result(await response(wrapped))[0], 503)

    async def test_active_blocks_all_methods_and_paths_except_exact_health(self):
        self.control(active=True)
        wrapped = self.wrapped()
        for method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            for path in ("/", "/api/auth/login", "/static/example.js", "/health/", "/health/ready/extra"):
                with self.subTest(method=method, path=path):
                    status, body, headers = result(await response(wrapped, scope(path, method)))
                    self.assertEqual(status, 503)
                    self.assertEqual(headers[b"pragma"], b"no-cache")
                    self.assertEqual(headers[b"referrer-policy"], b"no-referrer")
                    self.assertIsNone(body) if method == "HEAD" else self.assertEqual(
                        body, {"detail": "Servicio en mantenimiento"})

    async def test_health_allowlist_is_readonly_methods_only(self):
        self.control(active=True)
        seen = []

        async def health(request_scope, receive, send):
            seen.append((request_scope["method"], request_scope["path"]))
            await inner_ok(request_scope, receive, send)

        wrapped = self.wrapped(health)
        for path in ("/health", "/health/ready"):
            for method in ("GET", "HEAD"):
                self.assertEqual(result(await response(wrapped, scope(path, method)))[0], 201)
            for method in ("POST", "PUT", "DELETE", "OPTIONS"):
                self.assertEqual(result(await response(wrapped, scope(path, method)))[0], 503)
        self.assertEqual(len(seen), 4)
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_wrong_missing_duplicate_query_or_other_method_secret_is_404(self):
        self.control(active=True)
        wrapped = self.wrapped()
        for token in ("", "b0" * 32, TOKEN[:-1], "z" * 65):
            with self.subTest(token_length=len(token)):
                self.assertEqual((await self.status(wrapped, token=token))[0], 404)
        for method in ("HEAD", "POST", "PUT", "DELETE", "OPTIONS"):
            self.assertEqual((await self.status(wrapped, method=method))[0], 404)
        self.assertEqual((await self.status(wrapped, headers=[]))[0], 404)
        duplicate = [(TOKEN_HEADER, TOKEN.encode()), (TOKEN_HEADER, TOKEN.encode())]
        self.assertEqual((await self.status(wrapped, headers=duplicate))[0], 404)
        request_scope = scope(STATUS_PATH, "GET")
        request_scope["query_string"] = b"token=" + TOKEN.encode()
        self.assertEqual(result(await response(wrapped, request_scope))[0], 404)

    async def test_mixed_case_header_name_is_accepted(self):
        self.control()
        headers = [(b"X-Metodobase-Maintenance", TOKEN.encode())]
        self.assertEqual((await self.status(self.wrapped(), headers=headers))[0], 200)

    async def test_token_rotation_and_file_deletion_revoke_old_authority(self):
        self.control()
        wrapped = self.wrapped()
        self.assertEqual((await self.status(wrapped))[0], 200)
        replacement = "b1" * 32
        self.control(token=replacement)
        self.assertEqual((await self.status(wrapped))[0], 404)
        self.assertEqual((await self.status(wrapped, token=replacement))[0], 200)
        self.path.unlink()
        self.assertEqual((await self.status(wrapped, token=replacement))[0], 404)
        self.assertEqual(result(await response(wrapped))[0], 503)

    async def test_pause_then_unlink_keeps_http_health_and_jobs_blocked(self):
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        self.assertTrue((await self.status(wrapped))[1]["drained"])
        self.path.unlink()
        self.assertEqual(result(await response(wrapped))[0], 503)
        for path in ("/health", "/health/ready"):
            for method in ("GET", "HEAD"):
                self.assertEqual(result(await response(wrapped, scope(path, method)))[0], 503)
        self.assertEqual((await self.status(wrapped))[0], 404)
        with gate.background_admission() as admitted:
            self.assertFalse(admitted)
        self.control(active=False)
        self.assertEqual(result(await response(wrapped))[0], 201)

    async def test_malformed_present_file_fails_closed_with_no_authority(self):
        malformed = [b"", b"{", b"[]", b"null", b"\xff", b" " * 4097,
                     ("[" * 1500).encode(),
                     b'{"version":1,"version":1,"active":true,"token":"' +
                     TOKEN.encode() + b'","operation":"' + OPERATION.encode() + b'"}']
        wrapped = self.wrapped()
        for raw in malformed:
            with self.subTest(size=len(raw)):
                self.path.write_bytes(raw)
                self.assertEqual(result(await response(wrapped))[0], 503)
                self.assertEqual(result(await response(wrapped, scope("/health", "GET")))[0], 503)
                self.assertEqual((await self.status(wrapped))[0], 404)

    async def test_strict_schema_types_exact_fields_and_bounds(self):
        invalid = [{"extra": True}, {"version": True}, {"version": 2},
                   {"version": 1.0}, {"active": 1}, {"active": "false"},
                   {"token": None}, {"token": TOKEN[:-1]}, {"token": "g" * 64},
                   {"operation": "invalid"}, {"operation": None},
                   {"operation": OPERATION.replace("-", "")}]
        wrapped = self.wrapped()
        for overrides in invalid:
            with self.subTest(fields=list(overrides)):
                self.control(**overrides)
                self.assertEqual(result(await response(wrapped))[0], 503)
        self.control()
        data = json.loads(self.path.read_bytes())
        for key in list(data):
            self.path.write_text(json.dumps({k: v for k, v in data.items() if k != key}))
            self.assertEqual(result(await response(wrapped))[0], 503)

    async def test_exact_4096_byte_control_is_allowed(self):
        self.control()
        raw = self.path.read_bytes()
        self.path.write_bytes(raw + b" " * (4096 - len(raw)))
        self.assertEqual(result(await response(self.wrapped()))[0], 201)

    async def test_directory_and_read_error_fail_closed(self):
        self.path.mkdir()
        self.assertEqual(result(await response(self.wrapped()))[0], 503)
        self.path.rmdir()
        with patch("web.middleware.maintenance.os.open", side_effect=PermissionError):
            self.assertEqual(result(await response(self.wrapped()))[0], 503)

    async def test_before_pause_drains_after_new_requests_are_blocked(self):
        self.control()
        entered, finish = asyncio.Event(), asyncio.Event()
        seen = []

        async def controlled(request_scope, receive, send):
            seen.append(request_scope["path"])
            entered.set()
            await finish.wait()
            await inner_ok(request_scope, receive, send)

        wrapped = self.wrapped(controlled)
        accepted = asyncio.create_task(response(wrapped, scope("/before")))
        try:
            await entered.wait()
            self.assertEqual((await self.status(wrapped))[1]["active_requests"], 1)
            self.control(active=True)
            paused = (await self.status(wrapped))[1]
            self.assertTrue(paused["active"])
            self.assertEqual(paused["active_requests"], 1)
            queued = await asyncio.gather(*[response(wrapped, scope("/after")) for _ in range(20)])
            self.assertTrue(all(result(events)[0] == 503 for events in queued))
            self.assertEqual(seen, ["/before"])
            self.assertEqual((await self.status(wrapped))[1]["active_requests"], 1)
            finish.set()
            self.assertEqual(result(await accepted)[0], 201)
            self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)
        finally:
            finish.set()
            await accepted

    async def test_control_removed_during_admitted_request_remains_closed_and_counts_it(self):
        self.control()
        entered, finish = asyncio.Event(), asyncio.Event()

        async def controlled(request_scope, receive, send):
            entered.set()
            await finish.wait()
            await inner_ok(request_scope, receive, send)

        wrapped = self.wrapped(controlled)
        task = asyncio.create_task(response(wrapped))
        try:
            await entered.wait()
            self.path.unlink()
            self.assertEqual(result(await response(wrapped))[0], 503)
            self.assertEqual((await self.status(wrapped))[0], 404)
            self.control(active=True)
            self.assertEqual((await self.status(wrapped))[1]["active_requests"], 1)
        finally:
            finish.set()
            await task
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_background_tasks_count_after_response_until_complete(self):
        # Real framework BackgroundTasks, not a handwritten substitute.
        from starlette.background import BackgroundTasks
        from starlette.responses import JSONResponse
        self.control()
        background_entered, finish_background = asyncio.Event(), asyncio.Event()

        async def background():
            background_entered.set()
            await finish_background.wait()

        async def app(request_scope, receive, send):
            tasks = BackgroundTasks()
            tasks.add_task(background)
            await JSONResponse({"ok": True}, background=tasks)(request_scope, receive, send)

        wrapped = self.wrapped(app)
        events = []
        task = asyncio.create_task(response(wrapped, events=events))
        try:
            await background_entered.wait()
            self.assertEqual(result(events)[0], 200)
            self.assertFalse(task.done())
            self.control(active=True)
            self.assertEqual((await self.status(wrapped))[1]["active_requests"], 1)
            self.assertEqual(result(await response(wrapped))[0], 503)
        finally:
            finish_background.set()
            await task
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_streaming_scope_receive_send_and_body_events_unchanged(self):
        self.control()
        request_scope = scope("/stream", "POST", [(b"authorization", b"synthetic")])
        incoming = [{"type": "http.request", "body": b"first", "more_body": True},
                    {"type": "http.request", "body": b"last", "more_body": False}]
        outgoing = [{"type": "http.response.start", "status": 206,
                     "headers": [(b"x-test", b"exact"), (b"set-cookie", b"unchanged")]},
                    {"type": "http.response.body", "body": b"part1", "more_body": True},
                    {"type": "http.response.body", "body": b"part2", "more_body": False}]
        received, sent = [], []

        async def receive():
            return incoming[len(received)]

        async def send(event):
            sent.append(event)

        async def app(current_scope, current_receive, current_send):
            self.assertIs(current_scope, request_scope)
            self.assertIs(current_receive, receive)
            self.assertIs(current_send, send)
            received.append(await current_receive())
            received.append(await current_receive())
            for event in outgoing:
                await current_send(event)

        await self.wrapped(app)(request_scope, receive, send)
        self.assertEqual(received, incoming)
        self.assertEqual(sent, outgoing)
        for original, actual in zip(outgoing, sent):
            self.assertIs(original, actual)

    async def test_application_exception_decrements_and_propagates(self):
        self.control()

        async def failing(request_scope, receive, send):
            raise RuntimeError("synthetic")

        wrapped = self.wrapped(failing)
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            await response(wrapped)
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_cancellation_decrements_and_propagates(self):
        self.control()
        entered = asyncio.Event()

        async def waiting(request_scope, receive, send):
            entered.set()
            await asyncio.Event().wait()

        wrapped = self.wrapped(waiting)
        task = asyncio.create_task(response(wrapped))
        await entered.wait()
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_lifespan_websocket_and_non_http_pass_through_even_if_paused(self):
        self.control(active=True)
        seen = []

        async def app(request_scope, receive, send):
            seen.append(request_scope)

        wrapped = self.wrapped(app)
        for kind in ("lifespan", "websocket", "custom"):
            current_scope = {"type": kind}
            await response(wrapped, current_scope)
            self.assertIs(seen[-1], current_scope)
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_multiple_concurrent_admitted_requests_are_all_counted(self):
        self.control()
        gate = asyncio.Event()
        all_entered = asyncio.Event()
        entered = 0

        async def app(request_scope, receive, send):
            nonlocal entered
            entered += 1
            if entered == 10:
                all_entered.set()
            await gate.wait()
            await inner_ok(request_scope, receive, send)

        wrapped = self.wrapped(app)
        tasks = [asyncio.create_task(response(wrapped)) for _ in range(10)]
        try:
            await all_entered.wait()
            self.control(active=True)
            self.assertEqual((await self.status(wrapped))[1]["active_requests"], 10)
        finally:
            gate.set()
            await asyncio.gather(*tasks)
        self.assertEqual((await self.status(wrapped))[1]["active_requests"], 0)

    async def test_paused_and_malformed_background_admission_skip_writes(self):
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        writes = []
        with gate.background_admission() as admitted:
            if admitted:
                writes.append("unexpected")
        status = (await self.status(wrapped))[1]
        self.assertEqual(status["active_jobs"], 0)
        self.assertTrue(status["drained"])
        self.path.write_bytes(b"invalid")
        with gate.background_admission() as admitted:
            if admitted:
                writes.append("unexpected")
        self.assertFalse(writes)

    async def test_shared_gate_counts_background_job_through_pause_until_finally(self):
        self.control()
        gate = MaintenanceGate(control_file=str(self.path))
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        with gate.background_admission() as admitted:
            self.assertTrue(admitted)
            self.control(active=True)
            status = (await self.status(wrapped))[1]
            self.assertEqual(status["active_requests"], 0)
            self.assertEqual(status["active_jobs"], 1)
            self.assertFalse(status["drained"])
            with gate.background_admission() as nested:
                self.assertFalse(nested)
            self.assertEqual((await self.status(wrapped))[1]["active_jobs"], 1)
        status = (await self.status(wrapped))[1]
        self.assertEqual(status["active_jobs"], 0)
        self.assertTrue(status["drained"])

    async def test_background_job_exception_releases_counter(self):
        self.control()
        gate = MaintenanceGate(control_file=str(self.path))
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        with self.assertRaisesRegex(RuntimeError, "synthetic-job"):
            with gate.background_admission() as admitted:
                self.assertTrue(admitted)
                self.assertEqual((await self.status(wrapped))[1]["active_jobs"], 1)
                raise RuntimeError("synthetic-job")
        self.assertEqual((await self.status(wrapped))[1]["active_jobs"], 0)

    async def test_background_context_disabled_keeps_working(self):
        gate = MaintenanceGate(control_file="")
        with gate.background_admission() as admitted:
            self.assertTrue(admitted)

    async def test_background_context_configured_missing_file_declines_work(self):
        gate = MaintenanceGate(control_file=str(self.path))
        with gate.background_admission() as admitted:
            self.assertFalse(admitted)

    async def test_http_and_independent_background_job_both_must_drain(self):
        self.control()
        entered, finish = asyncio.Event(), asyncio.Event()

        async def app(request_scope, receive, send):
            entered.set()
            await finish.wait()
            await inner_ok(request_scope, receive, send)

        gate = MaintenanceGate(control_file=str(self.path))
        wrapped = MaintenanceMiddleware(app, gate=gate)
        with gate.background_admission() as admitted:
            self.assertTrue(admitted)
            task = asyncio.create_task(response(wrapped))
            try:
                await entered.wait()
                self.control(active=True)
                status = (await self.status(wrapped))[1]
                self.assertEqual((status["active_requests"], status["active_jobs"]), (1, 1))
                self.assertFalse(status["drained"])
            finally:
                finish.set()
                await task
            self.assertFalse((await self.status(wrapped))[1]["drained"])
        self.assertTrue((await self.status(wrapped))[1]["drained"])

    async def test_base_http_middleware_stack_counts_framework_background_tasks(self):
        from fastapi import FastAPI
        from starlette.background import BackgroundTasks
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse
        self.control()
        background_entered, finish_background = asyncio.Event(), asyncio.Event()

        class PassThrough(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                return await call_next(request)

        async def background():
            background_entered.set()
            await finish_background.wait()

        app = FastAPI()

        @app.post("/api/example")
        async def endpoint():
            tasks = BackgroundTasks()
            tasks.add_task(background)
            return JSONResponse({"ok": True}, background=tasks)

        app.add_middleware(PassThrough)
        app.add_middleware(PassThrough)
        gate = MaintenanceGate(control_file=str(self.path))
        app.add_middleware(MaintenanceMiddleware, gate=gate)
        events = []
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await asyncio.Event().wait()

        async def send(event):
            events.append(event)

        task = asyncio.create_task(app(scope(), receive, send))
        entered_wait = asyncio.create_task(background_entered.wait())
        try:
            completed, _ = await asyncio.wait((task, entered_wait),
                                              return_when=asyncio.FIRST_COMPLETED)
            if task in completed:
                await task
                self.fail("Application exited before its background task began")
            self.assertEqual(result(events)[0], 200)
            self.assertFalse(task.done())
            self.control(active=True)
            status = (await self.status(app))[1]
            self.assertEqual(status["active_requests"], 1)
            self.assertFalse(status["drained"])
        finally:
            finish_background.set()
            await task
            entered_wait.cancel()
        self.assertTrue((await self.status(app))[1]["drained"])

    async def test_readonly_pending_probes_contribute_to_active_jobs(self):
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))
        pending = {"recovery": 2, "links": 3}
        gate.register_background_probe("password_recovery", lambda: pending["recovery"])
        gate.register_background_probe("member_links", lambda: pending["links"])
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        self.assertEqual((await self.status(wrapped))[1]["active_jobs"], 5)
        self.assertFalse((await self.status(wrapped))[1]["drained"])
        pending.update(recovery=0, links=0)
        self.assertTrue((await self.status(wrapped))[1]["drained"])

    async def test_invalid_pending_probe_fails_diagnostic_closed(self):
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        for value in (True, False, -1, 1.0, None, "0"):
            with self.subTest(value=value):
                gate.register_background_probe("password_recovery", lambda: value)
                status, body, _ = await self.status(wrapped)
                self.assertEqual(status, 503)
                self.assertNotIn("drained", body)

    async def test_probe_exception_does_not_expose_error_or_certify_drain(self):
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))

        def failure():
            raise RuntimeError("synthetic-private-exception")

        gate.register_background_probe("password_recovery", failure)
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        status, body, _ = await self.status(wrapped)
        self.assertEqual(status, 503)
        self.assertNotIn("synthetic-private", json.dumps(body))
        self.assertEqual((await self.status(wrapped, token="wrong"))[0], 404)

    async def test_real_dispatcher_queued_running_cancel_close_remain_counted(self):
        # The actual dispatcher module uses only the standard library.
        from web.services.recovery_dispatcher import RecoveryDispatcher
        dispatcher = RecoveryDispatcher(workers=1, capacity=3)
        entered, finish = threading.Event(), threading.Event()

        def work():
            entered.set()
            if not finish.wait(5):
                raise RuntimeError("Synthetic test synchronization timed out")

        self.control()
        gate = MaintenanceGate(control_file=str(self.path))
        gate.register_background_probe("password_recovery", lambda: dispatcher.pending)
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        try:
            self.assertTrue(dispatcher.submit(work))
            self.assertTrue(entered.wait(5))
            self.assertTrue(dispatcher.submit(lambda: None))
            self.control(active=True)
            status = (await self.status(wrapped))[1]
            self.assertEqual(status["active_jobs"], 2)
            self.assertFalse(status["drained"])
            dispatcher.close()  # queued cancels; running is deliberately alive.
            self.assertEqual((await self.status(wrapped))[1]["active_jobs"], 1)
            self.assertFalse((await self.status(wrapped))[1]["drained"])
        finally:
            finish.set()
            dispatcher._executor.shutdown(wait=True)
        self.assertTrue((await self.status(wrapped))[1]["drained"])

    async def test_old_dispatcher_instance_probe_is_retained_when_replaced(self):
        from types import SimpleNamespace
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))
        old = SimpleNamespace(pending=2)
        new = SimpleNamespace(pending=0)
        for dispatcher in (old, new):
            gate.register_background_probe(f"recovery:{id(dispatcher)}",
                                            lambda dispatcher=dispatcher: dispatcher.pending)
        wrapped = MaintenanceMiddleware(inner_ok, gate=gate)
        status = (await self.status(wrapped))[1]
        self.assertEqual(status["active_jobs"], 2)
        self.assertFalse(status["drained"])
        old.pending = 0
        self.assertTrue((await self.status(wrapped))[1]["drained"])

    async def test_same_dispatcher_registration_does_not_duplicate_pending(self):
        from types import SimpleNamespace
        self.control(active=True)
        gate = MaintenanceGate(control_file=str(self.path))
        dispatcher = SimpleNamespace(pending=1)
        for _ in range(2):
            gate.register_background_probe(f"recovery:{id(dispatcher)}",
                                            lambda dispatcher=dispatcher: dispatcher.pending)
        status = (await self.status(MaintenanceMiddleware(inner_ok, gate=gate)))[1]
        self.assertEqual(status["active_jobs"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
