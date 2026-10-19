"""Opt-in current31 preparation for unchanged publication/diary contracts.

The revision29 fixture remains immutable. Upgrade its SAME isolated SQLite
database to31 before case seeding or factory startup. Authentication is the
reviewed real password/enrollment/TOTP/challenge/recovery HTTP sequence; no
MFA dependency, business endpoint or historical migration helper is replaced.
"""
import pytest
from sqlalchemy import inspect

from tests import integration_client_link_services as historical
from tests.ci_mfa31.current_link_fixtures import http  # noqa: F401
from tests.integration_schema_migrations import run_migration

case = historical.case


@pytest.fixture(scope="module", params=["sqlite"])
def link_db(request, tmp_path_factory):
    """Only the caller's locally owned SQLite; PostgreSQL is not enabled here."""
    assert request.param == "sqlite"
    owner = historical.link_db.__wrapped__(request, tmp_path_factory)
    admin, app = next(owner)
    try:
        from web.database.schema_control import expected_head, verify_runtime_schema
        assert admin.dialect.name == app.dialect.name == "sqlite"
        run_migration(str(admin.url), "db_bootstrap.py", "--revision", "20261019_mfa")
        assert expected_head() == "20261019_mfa"
        verify_runtime_schema(app, expected_revision="20261019_mfa")
        with app.connect() as db:
            assert len(inspect(db).get_table_names()) == 33
        yield admin, app
    finally:
        owner.close()
