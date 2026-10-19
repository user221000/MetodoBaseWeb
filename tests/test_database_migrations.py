"""Fail-closed schema/bootstrap and idempotent onboarding regressions."""
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest


def test_bootstrap_returns_failure_when_upgrade_fails(monkeypatch):
    import db_bootstrap
    engine = create_engine("sqlite://")
    monkeypatch.setattr(db_bootstrap, "_migration_engine", lambda: engine)
    with patch("alembic.command.upgrade", side_effect=RuntimeError("synthetic DDL failure")):
        assert db_bootstrap.main() == 1
    engine.dispose()


def test_bootstrap_refuses_unversioned_existing_schema(monkeypatch):
    import db_bootstrap
    from sqlalchemy import text
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE unversioned_business_record(id INTEGER PRIMARY KEY)"))
    monkeypatch.setattr(db_bootstrap, "_migration_engine", lambda: engine)
    with patch("alembic.command.stamp") as stamp, patch("alembic.command.upgrade") as upgrade:
        assert db_bootstrap.main() == 1
    stamp.assert_not_called()
    upgrade.assert_not_called()
    engine.dispose()


def test_saas_factory_performs_no_ddl():
    from web.database.models import Base
    from web.main_web import create_app
    # R05 has already prepared this test's synthetic schema. Startup may verify
    # it, but may never create/stamp/rebuild it as a hidden repair operation.
    with patch.object(Base.metadata, "create_all", side_effect=AssertionError("Runtime DDL forbidden")) as ddl:
        app = create_app()
    assert app is not None
    ddl.assert_not_called()


def test_membership_catalog_read_never_creates_defaults():
    from web.database.models import Base, Usuario, UserRole, PlanSuscripcion
    from web.database.repository import listar_planes_suscripcion
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Usuario(id="read-only-gym", email="read@example.invalid", nombre="Synthetic",
                       password_hash="unused", tipo="gym", role=UserRole.OWNER))
        db.commit()
        assert listar_planes_suscripcion(db, "read-only-gym") == []
        assert db.query(PlanSuscripcion).count() == 0
    engine.dispose()


def test_onboarding_default_templates_are_idempotent():
    from web.database.models import Base, Usuario, UserRole, PlanSuscripcion
    from web.database.repository import _crear_planes_default
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Usuario(id="onboarding-gym", email="onboarding@example.invalid", nombre="Synthetic",
                       password_hash="unused", tipo="gym", role=UserRole.OWNER))
        db.commit()
        _crear_planes_default(db, "onboarding-gym")
        db.commit()
        _crear_planes_default(db, "onboarding-gym")
        db.commit()
        assert db.query(PlanSuscripcion).count() == 5
    engine.dispose()


def test_postgres_urls_select_the_installed_driver():
    from web.database.engine import normalize_database_url
    expected = "postgresql+psycopg2://synthetic@127.0.0.1:55482/metodobase_test"
    assert normalize_database_url("postgres://synthetic@127.0.0.1:55482/metodobase_test") == expected
    assert normalize_database_url("postgresql://synthetic@127.0.0.1:55482/metodobase_test") == expected
    assert normalize_database_url(expected) == expected


def test_api_factory_performs_no_ddl():
    from web.database.models import Base
    from api.app import create_app
    with patch.object(Base.metadata, "create_all", side_effect=AssertionError("Runtime DDL forbidden")) as ddl:
        app = create_app()
    assert app is not None
    ddl.assert_not_called()


@pytest.mark.parametrize("factory_module", ["api.app", "web.main_web"])
def test_factories_reject_old_revision_before_initializing_auth(monkeypatch, factory_module):
    import importlib
    from sqlalchemy import text
    from config.settings import get_settings
    from web.database.models import Base
    module = importlib.import_module(factory_module)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version(version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('20261018_billing_integrity')"))
    monkeypatch.setattr(get_settings(), "ENV", "development")
    monkeypatch.setattr("web.database.engine.get_engine", lambda: engine)
    with patch("web.auth.init_auth") as api_auth:
        with pytest.raises(RuntimeError, match="revision"):
            module.create_app()
    api_auth.assert_not_called()
    engine.dispose()


def test_schema_signature_normalizes_only_equivalent_pg_literal_array_casts():
    from web.database.alembic.schema_contract_v1 import _expression
    original = "plan::text = ANY (ARRAY['free'::character varying, 'standard'::character varying]::text[])"
    restored = "plan::text = ANY (ARRAY['free'::character varying::text, 'standard'::character varying::text])"
    assert _expression(original) == _expression(restored)
    assert _expression(original) != _expression(restored.replace("'standard'", "'unrecognized'"))
    assert _expression(original) != _expression(restored + ' OR true')
    assert _expression(original) != _expression(restored.replace('plan::text', 'status::text'))
    assert _expression(original) != _expression(restored + ' OR plan IS NULL')
