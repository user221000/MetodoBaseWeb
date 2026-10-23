"""New37 PostgreSQL DDL companion, with its own non-destructive lease source."""
import os

import pytest
from sqlalchemy import inspect, text

from tests import integration_account_security37_migrations as own
from tests.account_security37_owned import owned_database
from tests.integration_client_link_migrations import populate28
from tests.integration_schema_migrations import run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import verify_runtime_schema

PREVIOUS = "20261020_notifications"
REVISION = "20261020_account_security"


def _drain_fixture_pool(value, known_pids, output):
    # Proposed fixture-only followup; the owned37 authority remains unchanged.
    from contextlib import closing
    from datetime import datetime
    import json
    from pathlib import Path
    import sys
    import time
    from urllib.parse import urlsplit
    import psycopg2
    from tests.isolation import validate_postgres_test_url

    _, engine = value
    name = engine.url.database
    assert name.startswith("metodobase_test_account37_")
    identifier = name.removeprefix("metodobase_test_account37_")
    assert len(identifier) == 32 and all(c in "0123456789abcdef" for c in identifier)
    receipt = Path(os.environ["ACCOUNT37_PRIVATE_LEASES"]) / ("lease-" + identifier + ".json")
    expected = json.loads(receipt.read_bytes())
    assert expected["database"] == name and expected["state"] == "created"
    assert expected["launcher_pid"] == os.getpid()
    state = {"known_backend_pids": sorted(known_pids), "observations": []}
    try:
        state["checked_out_before_dispose"] = engine.pool.checkedout()
        engine.dispose()  # This engine only; checked-out Connections are not forced closed.
        assert state["checked_out_before_dispose"] == 0, "A fixture Connection remains checked out"
        source = validate_postgres_test_url(os.environ["METODOBASE_TEST_MIGRATOR_URL"])
        parsed = urlsplit(source)
        assert parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == 55483
        with closing(psycopg2.connect(source.replace("postgresql+psycopg2://", "postgresql://", 1), connect_timeout=5,
                options="-c statement_timeout=250ms -c lock_timeout=250ms")) as control:
            control.autocommit = True  # Each observation uses a fresh transaction snapshot.
            with control.cursor() as cursor:
                deadline = time.monotonic() + 2.0
                state.update(drain_deadline_seconds=2.0, statement_timeout_ms=250,
                             lock_timeout_ms=250, connect_timeout_seconds=5)
                def read(statement, parameters=None, *, many=False):
                    assert time.monotonic() < deadline, "Owned drain deadline expired before query"
                    cursor.execute(statement, parameters)
                    rows = cursor.fetchall() if many else cursor.fetchone()
                    assert time.monotonic() < deadline, "Owned drain deadline expired during query"
                    return rows
                started, host, port, user = read("SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port(),current_user")
                assert started == datetime.fromisoformat(expected["postmaster_start"])
                assert host == expected["server_host"] and port == expected["server_port"] == 55483
                assert user == expected["expected_owner"]
                while True:
                    assert read("SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (name,)) == (expected["oid"], expected["expected_owner"]), "Owned identity changed"
                    active = [row[0] for row in read("SELECT pid FROM pg_stat_activity WHERE datname=%s ORDER BY pid", (name,), many=True)]
                    state["observations"].append(active)
                    assert set(active) <= known_pids, "An active backend is not attributed to the fixture pool"
                    remaining = deadline - time.monotonic()
                    assert remaining > 0, "Owned drain deadline expired after observation"
                    if not active:
                        break
                    time.sleep(min(0.05, remaining))
        state["natural_drain_confirmed"] = True
    finally:
        error_type = sys.exc_info()[0]
        state["error_type"] = error_type.__name__ if error_type else None
        # Root-created pytest tmp_path inherits the private phase boundary.
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, indent=2)
            stream.write("\n")


@pytest.fixture
def account_database(tmp_path):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.fail("Current37 PostgreSQL migrations require an explicit own lease profile")
    from sqlalchemy import event
    with owned_database("postgresql", tmp_path) as value:
        known_pids = set()
        def connected(connection, _record):
            known_pids.add(connection.get_backend_pid())  # Cached DBAPI metadata, no SELECT.
        event.listen(value[1], "connect", connected)
        try:
            yield value
        finally:
            try:
                _drain_fixture_pool(value, known_pids, tmp_path / "account37-fixture-close.json")
            finally:
                event.remove(value[1], "connect", connected)


@pytest.mark.parametrize("populated", [False, True])
def test_exact36_preserves_rows_repeat_and_empty37_downgrade(account_database, populated):
    url, engine = account_database
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    if populated:
        populate28(engine)
    columns, rows = snapshot(engine)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
    with engine.connect() as db:
        assert len(inspect(db).get_table_names()) == 42
        assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
                              "AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 32
        assert db.scalar(text("SELECT count(*) FROM usuarios WHERE email_verified_at IS NOT NULL OR email_verification_hash IS NOT NULL")) == 0
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    assert snapshot(engine, columns)[1] == rows
    run_migration(url, "-m", "alembic", "downgrade", PREVIOUS)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows


test_predecessor_drift_refuses_before_addition = own.test_predecessor_drift_refuses_before_addition
test_interrupted_install_rolls_back_all_metadata_and_revision = own.test_interrupted_install_rolls_back_all_metadata_and_revision
test_any_contact_evidence_refuses_destructive_downgrade = own.test_any_contact_evidence_refuses_destructive_downgrade
test_partial_malformed_contact_metadata_is_rejected = own.test_partial_malformed_contact_metadata_is_rejected
test_predecessor_security_components_are_identical = own.test_predecessor_security_components_are_identical
