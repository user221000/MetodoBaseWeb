"""Current40 companion for the unchanged historical privacy39 HTTP criteria.

The frozen39 fixture deliberately lacks later gym-equipment columns. Reuse
every original assertion with a separate genuine current-head database;
never change the historical revision, bypass schema gates or create_all.
"""
import pytest
from sqlalchemy import event

from tests import test_privacy39_http as original
from tests.followup34_fixtures import owned_database
from tests.integration_schema_migrations import run_migration
from tests.privacy39_fixtures import database_schema, isolated_database


@pytest.fixture(scope='module')
def current40_engine(tmp_path_factory):
    with owned_database('sqlite', tmp_path_factory.mktemp('qa-current40-privacy')) as (url, engine):
        run_migration(url, 'db_bootstrap.py', '--revision', 'head')
        def foreign_keys(connection, _record):
            connection.execute('PRAGMA foreign_keys=ON')
        event.listen(engine, 'connect', foreign_keys)
        engine.dispose()
        yield engine


privacy39_engine = current40_engine
account37_engine = current40_engine
followup_db = original.followup_db
account_http = original.account_http

# Preserve the original functions, parameter markers and assertions byte-for-
# byte. Only the composed fixture above is new and explicitly current40.
for _name in dir(original):
    if _name.startswith('test_'):
        globals()[_name] = getattr(original, _name)
