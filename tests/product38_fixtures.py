"""New revision38 companions, never retargeting a frozen37 fixture."""
import pytest
from sqlalchemy import event

from tests.followup34_fixtures import owned_database
from tests.integration_schema_migrations import run_migration
from tests import integration_client_link_services as shared

REVISION = '20261023_product_facts'


@pytest.fixture(scope='module')
def origin38_engine(tmp_path_factory):
    with owned_database('sqlite', tmp_path_factory.mktemp('product38')) as (url, engine):
        run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
        def foreign_keys(connection, _record):
            connection.execute('PRAGMA foreign_keys=ON')
        event.listen(engine, 'connect', foreign_keys)
        engine.dispose()
        yield engine


@pytest.fixture(scope='module')
def link_db(origin38_engine):
    yield origin38_engine, origin38_engine


# The original actor/body factories remain literal, explicitly composed on38.
case = shared.case
