"""Separate migration credentials never initialize or mutate the app pool."""
from unittest.mock import patch

import pytest


def test_production_requires_explicit_migrator_without_using_app_connection(monkeypatch, caplog):
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'ENV', 'production')
    monkeypatch.setattr(get_settings(), 'is_production', True)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://synthetic_app:private-marker@127.0.0.1:55482/metodobase_test_cli')
    monkeypatch.delenv('MIGRATOR_DATABASE_URL', raising=False)
    with patch('sqlalchemy.create_engine') as engine, patch('web.database.engine.get_engine') as app:
        assert db_bootstrap.main() == 1
    engine.assert_not_called()
    app.assert_not_called()
    assert 'private-marker' not in caplog.text


@pytest.mark.parametrize('migrator', [
    'postgresql://synthetic_migrator@127.0.0.2:55482/metodobase_test_cli',
    'postgresql://synthetic_migrator@127.0.0.1:55483/metodobase_test_cli',
    'postgresql://synthetic_migrator@127.0.0.1:55482/metodobase_test_other',
    'postgresql://synthetic_app@127.0.0.1:55482/metodobase_test_cli',
    'sqlite:///synthetic.db',
])
def test_production_rejects_wrong_destination_driver_or_shared_role(monkeypatch, migrator):
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'ENV', 'production')
    monkeypatch.setattr(get_settings(), 'is_production', True)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://synthetic_app@127.0.0.1:55482/metodobase_test_cli')
    monkeypatch.setenv('MIGRATOR_DATABASE_URL', migrator)
    with patch('sqlalchemy.create_engine') as engine:
        assert db_bootstrap.main() == 1
    engine.assert_not_called()


def test_dedicated_migrator_engine_keeps_app_url_unchanged(monkeypatch):
    import os
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'ENV', 'production')
    monkeypatch.setattr(get_settings(), 'is_production', True)
    app_url = 'postgresql://synthetic_app@127.0.0.1:55482/metodobase_test_cli'
    migrator_url = 'postgresql://synthetic_migrator@127.0.0.1:55482/metodobase_test_cli'
    monkeypatch.setenv('DATABASE_URL', app_url)
    monkeypatch.setenv('MIGRATOR_DATABASE_URL', migrator_url)
    with patch('sqlalchemy.create_engine') as engine, patch('web.database.engine.get_engine') as app:
        assert db_bootstrap._migration_engine() is engine.return_value
    engine.assert_called_once_with(migrator_url.replace('postgresql://', 'postgresql+psycopg2://'), pool_pre_ping=True, echo=False)
    app.assert_not_called()
    assert os.environ['DATABASE_URL'] == app_url


def test_local_explicit_database_url_still_supports_historical_rehearsal(monkeypatch):
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'ENV', 'testing')
    monkeypatch.setattr(get_settings(), 'is_production', False)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///synthetic-only.db')
    monkeypatch.delenv('MIGRATOR_DATABASE_URL', raising=False)
    with patch('sqlalchemy.create_engine') as engine:
        db_bootstrap._migration_engine()
    engine.assert_called_once_with('sqlite:///synthetic-only.db', pool_pre_ping=True, echo=False)


@pytest.mark.parametrize('override', ['host=127.0.0.2', 'port=55483', 'dbname=metodobase_test_other',
    'user=synthetic_migrator', 'service=unreviewed-service', 'options=-crole%3Dsynthetic_migrator'])
def test_application_url_cannot_hide_destination_or_role_in_query(monkeypatch, override):
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'is_production', True)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://synthetic_app@127.0.0.1:55482/metodobase_test_cli?' + override)
    monkeypatch.setenv('MIGRATOR_DATABASE_URL', 'postgresql://synthetic_migrator@127.0.0.1:55482/metodobase_test_cli')
    with patch('sqlalchemy.create_engine') as engine:
        with pytest.raises(RuntimeError, match='TLS options'):
            db_bootstrap._migration_engine()
    engine.assert_not_called()


def test_production_migrator_preserves_explicit_tls_options(monkeypatch):
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'is_production', True)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://synthetic_app@127.0.0.1:55482/metodobase_test_cli?sslmode=require')
    url = 'postgresql://synthetic_migrator@127.0.0.1:55482/metodobase_test_cli?sslmode=verify-full&sslrootcert=synthetic-ca.pem'
    monkeypatch.setenv('MIGRATOR_DATABASE_URL', url)
    with patch('sqlalchemy.create_engine') as engine:
        db_bootstrap._migration_engine()
    engine.assert_called_once_with(url.replace('postgresql://', 'postgresql+psycopg2://'), pool_pre_ping=True, echo=False)


@pytest.mark.parametrize('suffix', ['@127.0.0.1:55482', '@/metodobase_test_cli', '@127.0.0.1:55482/'])
def test_production_never_uses_libpq_host_or_database_defaults(monkeypatch, suffix):
    import db_bootstrap
    from config.settings import get_settings
    monkeypatch.setattr(get_settings(), 'is_production', True)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://synthetic_app' + suffix)
    monkeypatch.setenv('MIGRATOR_DATABASE_URL', 'postgresql://synthetic_migrator' + suffix)
    with patch('sqlalchemy.create_engine') as engine:
        with pytest.raises(RuntimeError, match='explicit host and database'):
            db_bootstrap._migration_engine()
    engine.assert_not_called()
