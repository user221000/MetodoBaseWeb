"""Current35 SQLite composition for immutable34 runtime assertions.

The historical34 auth/database helpers keep their original contract. Only this
new fixture migrates its own fresh database to35. Identity, MFA, permission,
candidate/command helpers and assertions are reused without bypasses.
"""
import pytest
from sqlalchemy import event

from tests.followup34_fixtures import owned_database
from tests.followup34_http import PASSWORD, candidate, create, followup_http
from tests.integration_schema_migrations import run_migration

REVISION35 = "20261020_nutrition_profile"


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    with owned_database("sqlite", tmp_path_factory.mktemp("nutrition35-followup-current")) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION35)

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        engine.dispose()
        yield engine
