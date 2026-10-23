"""Portable inert guards for the common PG close adapter; no SDK or SQL."""
import gc
import json
import unittest
import weakref
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.ci_web37 import pg_close as module

OUTPUT = None


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    """Override the root application's DB bootstrap for these inert guards."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    """No application DB cleanup: this module creates only synthetic metadata."""
    yield


@pytest.fixture(autouse=True)
def close_output_root(tmp_path, monkeypatch):
    monkeypatch.setitem(globals(), "OUTPUT", tmp_path)


class Connection:
    def __init__(self, pid=101, **values):
        self.closed, self.pid = 0, pid
        self.values = {"dbname": "own", "host": "127.0.0.1", "port": "55483", "user": "app", **values}

    def get_dsn_parameters(self):
        return self.values

    def get_backend_pid(self):
        return self.pid


class Pool:
    def __init__(self, idle=()):
        self.counter, self.disposes, self.idle = 0, 0, list(idle)

    def checkedout(self):
        return self.counter

    def dispose(self):
        self.disposes += 1
        self.counter = 0  # Model the installed QueuePool's reset; not a native-PG claim.
        for connection in self.idle:
            connection.closed = 1


class Record:
    pass


class Cursor:
    def __init__(self, rows):
        self.rows, self.calls, self.current = list(rows), [], None

    def execute(self, statement, parameters=None):
        self.calls.append((statement, parameters))
        self.current = self.rows.pop(0)

    def fetchone(self):
        return self.current

    def fetchall(self):
        return self.current


class Guards(unittest.TestCase):
    def test_ledger_old_pool_lifetimes_detach_and_raw_connection(self):
        ledger, connection, record = module._Ledger(), Connection(), Record()
        pool = Pool([connection])
        ledger.event("connect", record, pool, connection, 101)
        ledger.event("checkout", record, pool, connection, 101)
        ledger.before_dispose(pool, "model_original_dispose")
        pool.counter = 0  # Even a reset/post-dispose zero must not hide the loan.
        with self.assertRaises(ValueError):
            ledger.dispose_idle()
        self.assertEqual(pool.disposes, 0)
        self.assertEqual(ledger.disposals[0]["outstanding_records_before_dispose"][0]["loans"], 1)
        ledger.event("checkin", record, pool, connection, 101)
        ledger.dispose_idle()
        self.assertEqual(connection.closed, 1)
        reference = weakref.ref(record)
        del record
        gc.collect()
        self.assertIsNone(reference())
        another = Record()
        ledger.record_ids[id(another)] = (reference, 1)  # Explicit simulated ID-map collision.
        self.assertEqual(ledger.record(another, pool), 2)
        detached, connection, record, pool = module._Ledger(), Connection(102), Record(), Pool()
        detached.event("connect", record, pool, connection, 102)
        detached.event("checkout", record, pool, connection, 102)
        detached.event("detach", record, pool, connection, 102)
        with self.assertRaises(ValueError):
            detached.no_loans()
        detached.close_detached(connection, 102)
        detached.no_loans()
        with self.assertRaises(ValueError):
            detached.no_open_dbapi()  # Event is BEFORE physical close.
        connection.closed = 1
        detached.no_open_dbapi()
        raw_ledger, raw_connection = module._Ledger(), Connection(103)
        raw_ledger.connection(raw_connection, 103)
        with self.assertRaises(ValueError):
            raw_ledger.dispose_idle()
        self.assertEqual(raw_connection.closed, 0)  # Never force-close a direct loan.

    def test_foreign_dbapi_exact_scope_and_nested_namespace(self):
        observer = module._Observer.__new__(module._Observer)
        observer.psycopg2 = SimpleNamespace(extensions=SimpleNamespace(connection=Connection))
        one = SimpleNamespace(verified=True, roles={"app", "admin"}, ledger=module._Ledger())
        two = SimpleNamespace(verified=True, roles={"app", "admin"}, ledger=module._Ledger())
        observer.leases = {"own": one, "second": two}

        class Foreign:
            def __getattribute__(self, name):
                if name == "__class__":
                    return object.__getattribute__(self, name)
                raise AssertionError("Foreign DBAPI method touched")

        self.assertIsNone(observer.selected(Foreign()))
        self.assertIs(observer.selected(Connection()), one)
        self.assertIs(observer.selected(Connection(dbname="second")), two)
        self.assertIsNone(observer.selected(Connection(dbname="outside")))
        for values in ({"host": "outside.invalid"}, {"port": "5432"}, {"user": "other"}):
            with self.assertRaises(ValueError):
                observer.selected(Connection(**values))
        one.verified = False
        with self.assertRaises(ValueError):
            observer.selected(Connection())

    def test_identity_generation_and_oid_rejected_before_any_dispose(self):
        expected = {"postmaster_start": "2026-10-23T00:00:00+00:00", "server_host": "127.0.0.1",
                    "server_port": 55483, "expected_owner": "admin", "oid": 123}
        pool = Pool()
        ledger = module._Ledger()
        ledger.pool(pool)
        lease = SimpleNamespace(name="own", expected=expected, ledger=ledger, report={})
        good = (datetime(2026, 10, 23, tzinfo=UTC), "127.0.0.1", 55483, "admin")
        for rows in ([(datetime(2026, 10, 22, tzinfo=UTC), *good[1:])], [good, (124, "admin")]):
            cursor = Cursor(rows)

            @contextmanager
            def control(_lease, _cursor=cursor):
                yield _cursor, 100.0

            with patch.object(module, "_control", control), patch.object(module.time, "monotonic", return_value=0), self.assertRaises(ValueError):
                module._drain(lease)
            self.assertEqual(pool.disposes, 0)

    def test_poll_known_then_zero_and_unknown_is_not_filtered(self):
        for observations, accepted in (([[(101,)], []], True), ([[(999,)]], False)):
            cursor = Cursor(observations)
            ledger, connection = module._Ledger(), Connection()
            ledger.connection(connection, 101)
            connection.closed = 1
            lease = SimpleNamespace(name="own", ledger=ledger,
                report={"observations": [], "natural_drain_confirmed": False})

            @contextmanager
            def control(_lease, _cursor=cursor):
                yield _cursor, 100.0

            with patch.object(module, "_control", control), patch.object(module, "_identity"), \
                    patch.object(module.time, "monotonic", return_value=0), patch.object(module.time, "sleep") as sleep:
                if accepted:
                    module._drain(lease)
                    self.assertTrue(lease.report["natural_drain_confirmed"])
                    self.assertEqual(sleep.call_count, 1)
                else:
                    with self.assertRaises(ValueError):
                        module._drain(lease)
                    self.assertFalse(lease.report["natural_drain_confirmed"])
                    self.assertEqual(sleep.call_count, 0)
            self.assertTrue(all("WHERE datname=%s ORDER BY pid" in sql for sql, _params in cursor.calls))

    def test_deadline_before_query_and_after_empty_result(self):
        cursor = Cursor([[]])
        with patch.object(module.time, "monotonic", return_value=10), self.assertRaises(TimeoutError):
            module._read(cursor, 10, "synthetic-query", many=True)
        self.assertEqual(cursor.calls, [])
        with patch.object(module.time, "monotonic", side_effect=[9.0, 10.0]), self.assertRaises(TimeoutError):
            module._read(cursor, 10, "synthetic-query", many=True)
        self.assertEqual(len(cursor.calls), 1)

    def test_stop_attempts_every_listener_and_preserves_foreign_hook(self):
        observer = module._Observer.__new__(module._Observer)
        hook, original, foreign = lambda: None, lambda: None, lambda: None
        observer.psycopg2 = SimpleNamespace(connect=hook)
        observer.Engine = SimpleNamespace(dispose=foreign)
        observer.connect_hook = observer.dispose_hook = hook
        observer.original_connect = observer.original_dispose = original
        observer.Pool = object()
        observer.listeners = [(name, object()) for name in ("one", "two", "three")]
        attempted = []

        def remove(_pool, name, _callback):
            attempted.append(name)
            if name == "one":
                raise ValueError("synthetic remove failure")

        observer.event = SimpleNamespace(remove=remove)
        with self.assertRaises(ValueError):
            observer.stop()
        self.assertEqual(attempted, ["one", "two", "three"])
        self.assertIs(observer.psycopg2.connect, original)
        self.assertIs(observer.Engine.dispose, foreign)

    def test_rejected_receipt_is_written_and_teardown_fails(self):
        root = OUTPUT / "pure-fixtures"
        root.mkdir()
        receipt = root / "synthetic-owner.json"
        receipt.write_text(json.dumps({"database": "synthetic-own", "oid": 123,
            "expected_owner": "admin", "state": "created"}), encoding="utf8")
        lease = SimpleNamespace(receipt=receipt, name="synthetic-own", expected={"oid": 123, "expected_owner": "admin"},
            output=root / "synthetic-rejected.json", ledger=module._Ledger(),
            report={"schema": "synthetic-pure-model-not-a-lease", "natural_drain_confirmed": True})
        with self.assertRaises(ValueError):
            module._publish(lease, None)
        self.assertFalse(json.loads(lease.output.read_bytes())["accepted"])
        lease.output = root / "synthetic-prior-error.json"
        module._publish(lease, "SyntheticPriorFailure")
        self.assertFalse(json.loads(lease.output.read_bytes())["accepted"])
