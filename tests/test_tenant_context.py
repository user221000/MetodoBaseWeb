"""Principal selection and explicit job/callback context contracts.

PostgreSQL RLS and actual multi-transaction behavior are separate integration
acceptance; SQLite does not prove database-level tenant isolation.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request


def test_production_rejects_explicit_sqlite(monkeypatch):
    from web.database.engine import _get_database_url
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///synthetic.db')
    monkeypatch.setattr('web.settings.get_settings', lambda: SimpleNamespace(is_production=True))
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        _get_database_url()


@pytest.mark.parametrize('path,expected', [('/api/clientes', 'owner-id'),
    ('/api/usuario/perfil', 'member-id'), ('/api/usuario/suscripcion', 'member-id')])
def test_professional_and_personal_contexts_use_persisted_relationship(monkeypatch, path, expected):
    from web.middleware.tenant import TenantMiddleware
    principal = {'id': 'member-id', 'tipo': 'gym', 'role': 'viewer', 'team_gym_id': 'owner-id'}
    monkeypatch.setattr('web.auth.verificar_token', lambda _: principal)
    request = Request({'type': 'http', 'method': 'GET', 'scheme': 'http', 'path': path,
                       'headers': [(b'authorization', b'Bearer synthetic')], 'query_string': b''})
    middleware = TenantMiddleware(lambda *_: None)
    assert asyncio.run(middleware._extract_tenant(request)) == expected


def test_public_request_clears_inherited_context_and_restores_caller():
    from web.database.tenant_context import current_tenant
    from web.middleware.tenant import TenantMiddleware
    app = FastAPI()
    app.add_middleware(TenantMiddleware)
    @app.get('/health')
    def health():
        return {'tenant': current_tenant.get()}
    token = current_tenant.set('outer-job')
    try:
        with TestClient(app) as client:
            assert client.get('/health').json() == {'tenant': ''}
        assert current_tenant.get() == 'outer-job'
    finally:
        current_tenant.reset(token)


def test_authorized_generation_worker_carries_explicit_tenant_without_request():
    from web.database.tenant_context import current_tenant
    from web.routes.planes import _generar_plan_sync
    assert current_tenant.get() == ''
    with patch('web.routes.planes._do_generar_plan', side_effect=lambda *args: {'tenant': current_tenant.get()}):
        assert _generar_plan_sync('client-id', 1, 'owner-id') == {'tenant': 'owner-id'}
    assert current_tenant.get() == ''


def test_generation_worker_cannot_switch_away_from_authorized_request():
    from web.database.tenant_context import tenant_scope
    from web.routes.planes import _generar_plan_sync
    with tenant_scope('owner-a'), patch('web.routes.planes._do_generar_plan') as generate:
        with pytest.raises(ValueError, match='tenant'):
            _generar_plan_sync('client-id', 1, 'owner-b')
        generate.assert_not_called()


def test_callback_cannot_rebind_request_or_reuse_session_for_another_account():
    from web.database.tenant_context import bind_verified_subject, tenant_scope
    engine = create_engine('sqlite://')
    try:
        with Session(engine) as db:
            bind_verified_subject(db, 'owner-a')
            db.commit()
            with pytest.raises(ValueError, match='mismatch'):
                bind_verified_subject(db, 'owner-b')
        with tenant_scope('owner-a'), Session(engine) as db:
            with pytest.raises(ValueError, match='mismatch'):
                bind_verified_subject(db, 'owner-b')
    finally:
        engine.dispose()


def test_failed_background_task_always_restores_context():
    from web.database.tenant_context import tenant_task, current_tenant
    @tenant_task('owner')
    def fails(owner):
        assert current_tenant.get() == owner
        raise RuntimeError('Synthetic task failure')
    with pytest.raises(RuntimeError):
        fails('owner-a')
    assert current_tenant.get() == ''
