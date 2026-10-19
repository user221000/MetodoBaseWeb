"""Actual PostgreSQL units and timestamp comparison under two DB timezones."""
import pytest
from sqlalchemy import text

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine
from tests.test_cleanup_tokens import FixedClock, assert_cleanup_boundaries


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('zone', ['UTC', 'America/Mexico_City'])
def test_cleanup_keeps_the_same_cutoff_rows_under_database_timezone(migration_database, monkeypatch, zone):
    from scripts import cleanup_expired_tokens as cleanup
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    # The audit fixtures have no tenant, as historical global auth failures do.
    # This test exercises existing application privileges, never adds a bypass.
    app = application_engine(url, admin)
    try:
        with app.begin() as connection:
            connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {'zone': zone})
        monkeypatch.setattr(cleanup, 'get_engine', lambda: app)
        monkeypatch.setattr(cleanup, 'datetime', FixedClock)
        assert_cleanup_boundaries(app)
    finally:
        app.dispose()
