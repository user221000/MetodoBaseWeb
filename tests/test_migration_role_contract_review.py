"""Connection overrides must not bypass the reviewed migration destination."""
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("override", ["host=127.0.0.2", "port=55483", "dbname=metodobase_test_other", "user=metodobase_test_app"])
def test_migrator_query_override_is_rejected_before_any_connection(monkeypatch, override):
    import db_bootstrap
    import sqlalchemy

    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(is_production=True))
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://metodobase_test_app@127.0.0.1:55482/metodobase_test_isolated")
    monkeypatch.setenv("MIGRATOR_DATABASE_URL", "postgresql+psycopg2://metodobase_test_admin@127.0.0.1:55482/metodobase_test_isolated?" + override)
    created = []

    def no_network_engine(*args, **kwargs):
        created.append(True)
        return object()

    monkeypatch.setattr(sqlalchemy, "create_engine", no_network_engine)
    with pytest.raises(RuntimeError):
        db_bootstrap._migration_engine()
    assert created == []
