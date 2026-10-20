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


@pytest.fixture
def account_database(tmp_path):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.fail("Current37 PostgreSQL migrations require an explicit own lease profile")
    with owned_database("postgresql", tmp_path) as value:
        yield value


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
