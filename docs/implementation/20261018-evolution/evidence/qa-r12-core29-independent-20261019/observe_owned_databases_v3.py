"""Add ordinary migration fixture observation for the bounded new29 preservation selection."""
from observe_owned_databases_v2 import *
import pytest

@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef,request):
    outcome=yield
    if fixturedef.argname!='migration_database' or outcome.excinfo is not None:
        return
    value=outcome.get_result()
    if value[1].dialect.name!='postgresql':
        return
    name=value[1].url.database
    assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',name)
    OWNED[name]={'fixture':'migration_database','module':request.module.__name__,'criterion':request.node.name}
    persist_pending()
