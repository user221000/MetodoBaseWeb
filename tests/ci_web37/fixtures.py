"""Current37-only fixture; accepted historical fixtures and targets stay intact.

The accepted account37 owner records the UUID before CREATE and requires a
normal DROP after zero sessions. Its own namespace and coordinated lease are
mandatory. Import/collection performs no SQL and no process launch.
"""
from __future__ import annotations

import os

import pytest

from tests.ci_web37.physical import REVISION, blank_pool, physical_contract


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.fail("Current37 requires an explicit exclusive PostgreSQL lease; no skip or fallback")
    from tests.account_security37_owned import owned_database
    from tests.integration_provider_subjects import application_engine
    from tests.integration_schema_migrations import run_migration

    with owned_database("postgresql", tmp_path_factory.mktemp("ci-web37")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        application = application_engine(url, admin)
        try:
            physical_contract(application)
            yield admin, application
            blank_pool(application)
        finally:
            application.dispose()


@pytest.fixture(autouse=True)
def current37_witness(followup_db):
    physical_contract(followup_db[1])
    yield
    blank_pool(followup_db[1])
