"""Current PG fixture close barrier; the original UUID owner remains unchanged.

Import is inert. Root's exclusive generation/role/CREATE admission is external.
Callbacks use cached DBAPI metadata only, never SQL. Generation/OID/owner are
queried before the body and again before disposing any registered target Pool.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import time
import weakref
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from urllib.parse import unquote, urlsplit

_NAME = re.compile(r"metodobase_test_account37_([0-9a-f]{32})\Z")
_LOCK = RLock()
_OBSERVER = None


class _Ledger:
    """One UUID; strong Pool references, weak Record/DBAPI lifetimes."""

    def __init__(self):
        self.pools = {}
        self.records = {}
        self.record_ids = {}
        self.connections = {}
        self.connection_ids = {}
        self.disposals = []
        self.errors = []

    def pool(self, pool):
        self.pools.setdefault(id(pool), pool)

    def connection(self, connection, pid):
        if type(pid) is not int or pid <= 0:
            raise ValueError("A positive attributed backend PID is required")
        previous = self.connection_ids.get(id(connection))
        if previous is not None and previous[0]() is connection:
            row = self.connections[previous[1]]
            if row["pid"] != pid:
                raise ValueError("A live DBAPI connection changed backend PID")
            return previous[1]
        token = len(self.connections) + 1
        reference = weakref.ref(connection)
        self.connection_ids[id(connection)] = (reference, token)
        self.connections[token] = {"reference": reference, "pid": pid,
                                   "detached": False, "close_event": False}
        return token

    def record(self, record, pool):
        self.pool(pool)
        previous = self.record_ids.get(id(record))
        if previous is not None and previous[0]() is record:
            row = self.records[previous[1]]
            if row["pool"] != id(pool):
                raise ValueError("A live Record changed Pool")
            return previous[1]
        token = len(self.records) + 1
        self.record_ids[id(record)] = (weakref.ref(record), token)
        self.records[token] = {"pool": id(pool), "loans": 0, "generations": []}
        return token

    def has_record(self, record):
        previous = self.record_ids.get(id(record))
        return previous is not None and previous[0]() is record

    def event(self, kind, record, pool, connection=None, pid=None):
        token = self.record(record, pool)
        row = self.records[token]
        physical = self.connection(connection, pid) if connection is not None else None
        if physical is not None and (not row["generations"] or row["generations"][-1] != physical):
            row["generations"].append(physical)
        if kind == "checkout":
            row["loans"] += 1
        elif kind == "checkin":
            row["loans"] -= 1
        elif kind == "detach":
            row["loans"] -= 1
            self.connections[physical]["detached"] = True
        elif kind == "close":
            self.connections[physical]["close_event"] = True
        if row["loans"] < 0:
            raise ValueError("Incomplete checkout/checkin sequence")

    def close_detached(self, connection, pid):
        previous = self.connection_ids.get(id(connection))
        if previous is None or previous[0]() is not connection:
            raise ValueError("Unknown detached DBAPI lifetime")
        row = self.connections[previous[1]]
        if row["pid"] != pid or not row["detached"]:
            raise ValueError("Detached DBAPI generation changed")
        row.update(detached=False, close_event=True)

    def checkedout(self, pool):
        value = pool.checkedout()
        if type(value) is not int:
            raise ValueError("A supported exact Pool counter is required")
        return value

    def no_loans(self):
        if self.errors or any(row["loans"] != 0 for row in self.records.values()):
            raise ValueError("Fixture has an unreturned or unobserved Pool loan")
        if any(row["detached"] for row in self.connections.values()):
            raise ValueError("Fixture has an unclosed detached connection")
        if any(self.checkedout(pool) != 0 for pool in self.pools.values()):
            raise ValueError("An original fixture Pool is still checked out")

    def no_open_dbapi(self):
        for row in self.connections.values():
            connection = row["reference"]()
            if connection is not None and connection.closed == 0:
                raise ValueError("Attributed DBAPI connection remains open")

    def dispose_idle(self):
        self.no_loans()
        for pool in tuple(self.pools.values()):
            self.no_loans()
            self.before_dispose(pool, "common_idle_pool")
            pool.dispose()  # Only the exact admitted UUID's recorded, idle Pools.
        self.no_loans()
        self.no_open_dbapi()

    def before_dispose(self, pool, origin):
        self.pool(pool)
        physical = {token for row in self.records.values() if row["pool"] == id(pool)
                    for token in row["generations"]}
        self.disposals.append({"origin": origin, "pool_id": id(pool),
            "checkedout_before_dispose": self.checkedout(pool),
            "outstanding_records_before_dispose": [
                {"token": token, "loans": row["loans"]} for token, row in self.records.items()
                if row["pool"] == id(pool) and row["loans"] != 0],
            "detached_connections_before_dispose": [
                token for token in physical if self.connections[token]["detached"]]})

    def snapshot(self):
        return {"pools": [{"pool_id": identity, "checkedout": self.checkedout(pool)}
                          for identity, pool in self.pools.items()],
                "record_generations": [{"token": token, **row, "generations": list(row["generations"])}
                                       for token, row in self.records.items()],
                "connections": [{"token": token, "pid": row["pid"], "detached": row["detached"],
                                 "close_event_before_physical_close": row["close_event"]}
                                for token, row in self.connections.items()],
                "disposals": [dict(row) for row in self.disposals], "diagnostic_errors": list(self.errors)}


class _Observer:
    def __init__(self):
        import psycopg2
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        from sqlalchemy.pool import Pool

        self.psycopg2, self.event, self.Engine, self.Pool = psycopg2, event, Engine, Pool
        self.original_connect, self.original_dispose = psycopg2.connect, Engine.dispose
        self.leases = {}
        self.users = 0
        self.listeners = [("connect", self.connected), ("checkout", self.checkout),
                          ("checkin", self.checkin), ("detach", self.detach),
                          ("close", self.close), ("close_detached", self.close_detached)]
        def disposed(engine, *args, **kwargs):
            return self.dispose(engine, *args, **kwargs)
        self.connect_hook, self.dispose_hook = self.connect, disposed
        installed = []
        try:
            for name, callback in self.listeners:
                event.listen(Pool, name, callback)
                installed.append((name, callback))
            psycopg2.connect, Engine.dispose = self.connect_hook, self.dispose_hook
        except BaseException as primary:
            if psycopg2.connect is self.connect_hook:
                psycopg2.connect = self.original_connect
            if Engine.dispose is self.dispose_hook:
                Engine.dispose = self.original_dispose
            cleanup_errors = []
            for name, callback in reversed(installed):
                try:
                    event.remove(Pool, name, callback)
                except BaseException as error:  # noqa: BLE001 -- finish removing all owned listeners, then re-raise.
                    cleanup_errors.append(type(error).__name__)
            if cleanup_errors:
                primary.add_note("Observer cleanup error classes: " + ",".join(cleanup_errors))
            raise

    def selected(self, connection):
        if not isinstance(connection, self.psycopg2.extensions.connection):
            return None
        if connection.closed:
            return next((lease for lease in self.leases.values()
                if (previous := lease.ledger.connection_ids.get(id(connection))) is not None
                and previous[0]() is connection), None)
        values = connection.get_dsn_parameters()  # Cached metadata, no query.
        lease = self.leases.get(values.get("dbname"))
        if lease is None:
            return None
        if (not lease.verified or values.get("host") not in {"127.0.0.1", "localhost"}
                or values.get("port") != "55483" or values.get("user") not in lease.roles):
            raise ValueError("Connection is outside the admitted UUID endpoint or roles")
        return lease

    def observe(self, callback, *args):
        try:
            with _LOCK:
                callback(*args)
        except Exception as error:  # noqa: BLE001 -- reject close without exposing exception text or changing callback lifecycle.
            with _LOCK:
                for lease in self.leases.values():
                    lease.ledger.errors.append(type(error).__name__)

    def pool_event(self, kind, connection, record, proxy=None):
        lease = self.selected(connection)
        if lease is None and connection is None:
            lease = next((value for value in self.leases.values() if value.ledger.has_record(record)), None)
        if lease is None:
            return
        pool = getattr(proxy, "_pool", None) if proxy is not None else None
        if pool is None:
            pool = getattr(record, "_ConnectionRecord__pool", None)
        if pool is None:
            raise ValueError("Supported diagnostic Pool association required")
        pid = None
        if connection is not None:
            if connection.closed:
                previous = lease.ledger.connection_ids.get(id(connection))
                if previous is None or previous[0]() is not connection:
                    raise ValueError("Closed DBAPI lifetime was not attributed")
                pid = lease.ledger.connections[previous[1]]["pid"]
            else:
                pid = connection.get_backend_pid()
        lease.ledger.event(kind, record, pool, connection, pid)

    def connected(self, connection, record):
        self.observe(self.pool_event, "connect", connection, record)

    def checkout(self, connection, record, proxy):
        self.observe(self.pool_event, "checkout", connection, record, proxy)

    def checkin(self, connection, record):
        self.observe(self.pool_event, "checkin", connection, record)

    def detach(self, connection, record):
        self.observe(self.pool_event, "detach", connection, record)

    def close(self, connection, record):
        self.observe(self.pool_event, "close", connection, record)

    def close_detached(self, connection):
        def record():
            lease = self.selected(connection)
            if lease is not None:
                lease.ledger.close_detached(connection, connection.get_backend_pid())
        self.observe(record)

    def connect(self, *args, **kwargs):
        connection = self.original_connect(*args, **kwargs)
        def record():
            lease = self.selected(connection)
            if lease is not None:
                lease.ledger.connection(connection, connection.get_backend_pid())
        self.observe(record)
        return connection

    def dispose(self, engine, *args, **kwargs):
        def before():
            lease = self.leases.get(engine.url.database)
            if lease is None:
                return
            if (engine.url.host not in {"127.0.0.1", "localhost"} or engine.url.port != 55483
                    or engine.url.username not in lease.roles):
                raise ValueError("Engine endpoint does not match its admitted UUID")
            lease.ledger.before_dispose(engine.pool, "original_Engine.dispose")
        self.observe(before)
        return self.original_dispose(engine, *args, **kwargs)  # Exactly once, original arguments.

    def stop(self):
        failure = None
        if (self.psycopg2.connect is not self.connect_hook
                or self.Engine.dispose is not self.dispose_hook):
            failure = ValueError("Scoped fixture observer hook changed")
        # Restore only hooks still owned by this observer, never somebody else's replacement.
        if self.psycopg2.connect is self.connect_hook:
            self.psycopg2.connect = self.original_connect
        if self.Engine.dispose is self.dispose_hook:
            self.Engine.dispose = self.original_dispose
        for name, callback in self.listeners:
            try:
                self.event.remove(self.Pool, name, callback)
            except BaseException as error:  # noqa: BLE001 -- attempt every owned listener and preserve the first failure.
                if failure is None:
                    failure = error
        if failure is not None:
            raise failure


def _plain(path, *, directory=False):
    info = path.lstat()
    kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not kind or stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
        raise ValueError("An ordinary owned evidence path is required")
    return path


class _Lease:
    def __init__(self, value, birth):
        from tests.isolation import validate_postgres_test_url

        url, engine = value
        parsed = urlsplit(validate_postgres_test_url(url))
        match = _NAME.fullmatch(parsed.path.removeprefix("/"))
        if (match is None or parsed.hostname not in {"127.0.0.1", "localhost"}
                or parsed.port != 55483):
            raise ValueError("An exact owned UUID loopback55483 lease is required")
        self.name, self.identifier = match.group(0), match.group(1)
        self.roles = set()
        for key in ("METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL"):
            profile = urlsplit(validate_postgres_test_url(os.environ[key]))
            if profile.hostname not in {"127.0.0.1", "localhost"} or profile.port != 55483:
                raise ValueError("Admitted fixture roles must use loopback55483")
            self.roles.add(unquote(profile.username or ""))
        if len(self.roles) != 2 or not all(self.roles):
            raise ValueError("Distinct explicit fixture roles are required")
        root = _plain(Path(os.environ["ACCOUNT37_PRIVATE_LEASES"]).resolve(strict=True), directory=True)
        self.receipt = _plain(root / ("lease-" + self.identifier + ".json"))
        self.initial_raw = self.receipt.read_bytes()
        self.expected = json.loads(self.initial_raw)
        expected = self.expected
        if (expected["database"] != self.name or expected["plan_id"] != self.identifier
                or expected["state"] != "created" or expected["launcher_pid"] != os.getpid()
                or expected["launcher_birth"] != birth or expected["launcher_birth_after_create"] != birth
                or type(expected["oid"]) is not int or expected["oid"] <= 0
                or expected["expected_owner"] != unquote(parsed.username or "")):
            raise ValueError("Original UUID receipt does not match this fixture")
        self.output_root = root.parent / "pool-close"
        self.output_root.mkdir(exist_ok=True)  # Inherits Root's existing private lease boundary.
        _plain(self.output_root, directory=True)
        self.output = self.output_root / (self.identifier + ".json")
        if os.path.lexists(self.output):
            raise ValueError("Fresh UUID close evidence is required")
        self.ledger = _Ledger()
        self.ledger.pool(engine.pool)
        self.verified = False
        self.report = {"schema": "current37-natural-pool-close-v1", "database": self.name,
            "initial_owner_receipt_sha256": hashlib.sha256(self.initial_raw).hexdigest(),
            "generation_callbacks": "cached_endpoint_role_UUID_lifetimes_only_under_Root_no_restart_lease",
            "source_generation_admitted_before_body": False, "natural_drain_confirmed": False,
            "observed_backend_pids": [], "observations": [], "owner_closed_absent": False,
            "accepted": False}


def _read(cursor, deadline, statement, parameters=None, *, many=False):
    if time.monotonic() >= deadline:
        raise TimeoutError("Fixture close deadline expired before query")
    cursor.execute(statement, parameters)
    rows = cursor.fetchall() if many else cursor.fetchone()
    if time.monotonic() >= deadline:
        raise TimeoutError("Fixture close deadline expired during query")
    return rows


def _identity(cursor, deadline, lease):
    from datetime import datetime

    expected = lease.expected
    started, host, port, user = _read(cursor, deadline,
        "SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port(),current_user")
    if (started != datetime.fromisoformat(expected["postmaster_start"])
            or host != expected["server_host"] or port != expected["server_port"] or port != 55483
            or user != expected["expected_owner"]):
        raise ValueError("Owned server generation or control identity changed")
    row = _read(cursor, deadline,
        "SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (lease.name,))
    if row != (expected["oid"], expected["expected_owner"]):
        raise ValueError("Owned database OID or owner changed")


@contextmanager
def _control(lease):
    from contextlib import closing

    import psycopg2

    from tests.isolation import validate_postgres_test_url

    source = validate_postgres_test_url(os.environ["METODOBASE_TEST_MIGRATOR_URL"])
    parsed = urlsplit(source)
    if (parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 55483
            or parsed.path.removeprefix("/") == lease.name):
        raise ValueError("Independent exact-loopback control database required")
    with closing(psycopg2.connect(source.replace("postgresql+psycopg2://", "postgresql://", 1),
            connect_timeout=5, options="-c statement_timeout=250ms -c lock_timeout=250ms")) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            yield cursor, time.monotonic() + 2.0


def _admit(lease):
    with _control(lease) as (cursor, deadline):
        _identity(cursor, deadline, lease)
    lease.verified = True
    lease.report["source_generation_admitted_before_body"] = True


def _drain(lease):
    with _control(lease) as (cursor, deadline):
        _identity(cursor, deadline, lease)  # Refuse changed generation BEFORE disposing target Pools.
        with _LOCK:
            lease.ledger.dispose_idle()
            known = {row["pid"] for row in lease.ledger.connections.values()}
            lease.report["observed_backend_pids"] = sorted(known)
        while True:
            _identity(cursor, deadline, lease)
            active = [row[0] for row in _read(cursor, deadline,
                "SELECT pid FROM pg_stat_activity WHERE datname=%s ORDER BY pid", (lease.name,), many=True)]
            lease.report["observations"].append(active)
            if not set(active) <= known:
                raise ValueError("An active owned-DB backend is not attributed to this fixture")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Fixture close deadline expired after observation")
            if not active:
                break
            time.sleep(min(0.05, remaining))
    lease.report["natural_drain_confirmed"] = True


def _publish(lease, error_type):
    final_raw = _plain(lease.receipt).read_bytes()
    final = json.loads(final_raw)
    with _LOCK:
        snapshot = lease.ledger.snapshot()
    lease.report.update(error_type=error_type, ledger=snapshot,
                        final_owner_receipt_sha256=hashlib.sha256(final_raw).hexdigest())
    lease.report["owner_closed_absent"] = (final["database"] == lease.name
        and final["oid"] == lease.expected["oid"] and final["expected_owner"] == lease.expected["expected_owner"]
        and final["state"] == "closed_absent" and type(final.get("sessions_before_drop")) is int
        and final["sessions_before_drop"] == 0
        and final.get("absence_verified") == "fresh_control_connection")
    lease.report["accepted"] = (error_type is None and lease.report["natural_drain_confirmed"]
        and lease.report["owner_closed_absent"] and not lease.ledger.errors)
    with lease.output.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(lease.report, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if error_type is None and not lease.report["accepted"]:
        raise ValueError("Fixture close evidence was rejected")


@contextmanager
def owned_database(dialect, directory):
    """Same fixture API; no UUID creation/drop implementation is duplicated."""
    if dialect != "postgresql":
        raise ValueError("The common close adapter is PostgreSQL only")
    from tests.account_security37_owned import owned_database as original
    from tests.account_security37_owned import process_birth

    global _OBSERVER
    with _LOCK:
        if _OBSERVER is None:
            _OBSERVER = _Observer()
        observer = _OBSERVER
        observer.users += 1
    lease = None
    admitted = False
    try:
        with original(dialect, directory) as value:
            lease = _Lease(value, process_birth())
            with _LOCK:
                if lease.name in observer.leases:
                    raise ValueError("Duplicate live UUID close context")
                observer.leases[lease.name] = lease
                admitted = True
            _admit(lease)
            try:
                yield value
            finally:
                _drain(lease)
    finally:
        error_type = sys.exc_info()[0]
        try:
            with _LOCK:
                if admitted:
                    observer.leases.pop(lease.name, None)
                observer.users -= 1
                if observer.users == 0:
                    try:
                        observer.stop()
                    finally:
                        _OBSERVER = None
        except BaseException:
            if lease is not None:
                lease.ledger.errors.append("ObserverRestoreError")
            raise
        finally:
            final_error = sys.exc_info()[0] or error_type
            if lease is not None:
                _publish(lease, final_error.__name__ if final_error else None)
