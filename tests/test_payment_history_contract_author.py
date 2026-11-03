"""Own-actor payment GET contract and documented response whitelist over ASGI."""
import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from tests.test_partial_refund_facts_author import billing_case, database_schema, isolated_database


@pytest.fixture
def history_app(billing_case):
    from web.auth_deps import get_usuario_actual
    from web.database.models import Payment, Usuario, UserRole
    from web.routes import usuario, billing
    _, factory, principal = billing_case
    with factory() as db:
        db.add(Usuario(id='foreign-gym', email='foreign-gym@example.invalid', password_hash='unused',
            nombre='Foreign synthetic', tipo='gym', role=UserRole.OWNER, activo=True))
        db.flush()
        for owner in (principal['id'], 'foreign-gym'):
            db.add(Payment(gym_id=owner, amount_cents=7900, currency='mxn', status='refunded',
                created_at=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)))
        db.commit()
    app = FastAPI()
    app.include_router(usuario.router, prefix='/api')
    app.include_router(billing.router, prefix='/api')
    app.dependency_overrides[get_usuario_actual] = lambda: dict(principal)
    return app, principal


def get(app, url):
    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
            return await client.get(url)
    return asyncio.run(request())


def test_personal_history_has_only_own_payments_and_preserves_unknowns_and_UTC(history_app):
    app, _ = history_app
    response = get(app, '/api/usuario/payments?user_id=foreign-gym&gym_id=foreign-gym')
    assert response.status_code == 200
    rows = response.json()['payments']
    assert len(rows) == 1
    assert rows[0]['created_at'] == '2026-11-01T12:00:00+00:00'
    assert (rows[0]['refund_amount_cents'], rows[0]['net_amount_cents'], rows[0]['refund_observed_at']) == (None, None, None)
    assert set(rows[0]) == {'id', 'amount_cents', 'refund_amount_cents', 'net_amount_cents',
        'refund_observed_at', 'currency', 'status', 'plan', 'created_at', 'stripe_invoice_id'}


def test_team_member_uses_own_personal_payments_and_never_inherits_gym_history(history_app):
    app, actor = history_app
    actor.update(tipo='gym', role='viewer', team_gym_id='foreign-gym')
    response = get(app, '/api/usuario/payments')
    assert response.status_code == 200 and len(response.json()['payments']) == 1


def test_business_owner_cannot_use_personal_route(history_app):
    app, actor = history_app
    actor['tipo'] = 'gym'
    assert get(app, '/api/usuario/payments').status_code == 403


def test_anonymous_personal_history_requires_authentication(history_app):
    app, _ = history_app
    app.dependency_overrides.clear()
    assert get(app, '/api/usuario/payments').status_code == 401


@pytest.mark.parametrize('limit', [0, 101, 'wrong'])
def test_personal_page_limit_is_bounded(history_app, limit):
    app, _ = history_app
    assert get(app, '/api/usuario/payments?limit=' + str(limit)).status_code == 422


def test_both_GETs_publish_same_readonly_response_and_hide_charge_identifier(history_app):
    app, _ = history_app
    schema = app.openapi()
    models = [schema['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
        for path in ('/api/billing/payments', '/api/usuario/payments')]
    assert models == [{'$ref': '#/components/schemas/PaymentHistoryResponse'}] * 2
    fields = schema['components']['schemas']['PaymentHistoryItem']['properties']
    assert 'stripe_charge_id' not in fields
    assert all({'type': 'null'} in fields[name]['anyOf'] for name in
        ('refund_amount_cents', 'net_amount_cents', 'refund_observed_at'))


@pytest.mark.parametrize('value', [True, -1, 1.5])
def test_response_money_contract_requires_nonnegative_integer(value):
    from web.billing_schemas import PaymentHistoryItem
    with pytest.raises(ValidationError):
        PaymentHistoryItem(id=1, amount_cents=value, currency='mxn', status='legacy-state',
            plan=None, created_at=None, stripe_invoice_id=None, refund_amount_cents=None,
            net_amount_cents=None, refund_observed_at=None)
