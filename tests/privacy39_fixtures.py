"""New39 genuine migration fixtures; no retarget of frozen37/38 tests."""
import pytest
from sqlalchemy import event
from tests.followup34_fixtures import owned_database
from tests.integration_schema_migrations import run_migration
from tests import account_security37_fixtures as security

REVISION='20261023_privacy_disposition'


@pytest.fixture(scope='module')
def privacy39_engine(tmp_path_factory):
    with owned_database('sqlite',tmp_path_factory.mktemp('privacy39')) as (url,engine):
        # Missing genuine targets must reject; no create_all/stamp fallback.
        run_migration(url,'db_bootstrap.py','--revision',REVISION)
        def foreign_keys(connection,_record):connection.execute('PRAGMA foreign_keys=ON')
        event.listen(engine,'connect',foreign_keys);engine.dispose()
        yield engine


@pytest.fixture(scope='session',autouse=True)
def database_schema():yield


@pytest.fixture(autouse=True)
def isolated_database():yield


account37_engine=privacy39_engine
account37=security.account37
