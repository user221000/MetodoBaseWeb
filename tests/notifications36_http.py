"""Current36 isolated HTTP fixtures; real registration/password/enrollment/MFA."""
import pytest
from sqlalchemy import event

from tests.notifications36_fixtures import owned_database
from tests.followup34_http import followup_http
from tests.integration_schema_migrations import run_migration
from web.database.schema_control import expected_head


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    # A new current fixture only; no accepted historical fixture is retargeted.
    with owned_database("sqlite", tmp_path_factory.mktemp("notifications36")) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", expected_head())
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
        engine.dispose()
        yield engine


notification_http = followup_http
