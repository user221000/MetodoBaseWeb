"""New current33 fixture; historical migration owners are left intact."""
import pytest

from tests.google33_fixtures import owned_database


@pytest.fixture(params=['postgresql'])
def migration_database(request,tmp_path):
    with owned_database(request.param,tmp_path) as value:
        from tests.integration_schema_migrations import run_migration
        run_migration(value[0],'db_bootstrap.py','--revision','20261019_google_subjects')
        yield value
