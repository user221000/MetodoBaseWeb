"""Effective factory contracts and bounded purchase verification HTTP admission.

SQLite/JWT are real and owned by the isolated launcher. Mail/Redis/payment
providers are never contacted; these checks do not certify inbox delivery.
"""
import importlib
from collections import Counter
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture(params=['api.app', 'web.main_web'])
def factory_case(request, test_gym_user):
    app = importlib.import_module(request.param).create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield app, client, test_gym_user, request.param


def effective_routes(app):
    return [route for route in iter_route_contexts(app.routes)
            if isinstance(route.original_route, APIRoute)]


def test_each_method_path_has_one_effective_handler_and_openapi_matches(factory_case):
    app, _, _, name = factory_case
    counts = Counter((method, route.path) for route in effective_routes(app) for method in route.methods)
    assert all(count == 1 for count in counts.values())
    spec = app.openapi()
    for path in ['/api/generar-plan', '/api/descargar-pdf/{id_cliente}', '/api/alimentos/catalogo']:
        route = next(route for route in effective_routes(app) if route.path == path)
        expected_module = 'api.routes.planes' if name == 'api.app' else 'web.routes.planes'
        assert route.endpoint.__module__ == expected_module
        operation = spec['paths'][path][next(iter(route.methods)).lower()]
        assert operation['summary'] == (route.summary or route.name.replace('_', ' ').title())


def test_history_reuses_private_handlers_dependencies_and_route_order(factory_case):
    from web.nutrition_http import NutritionRoute
    from web.routes.planes import router
    app, client, user, _ = factory_case
    routes = effective_routes(app)
    for path in ['/planes', '/planes/resumen', '/planes/{plan_id}/pdf']:
        original = next(route for route in router.routes if route.path == path)
        included = next(route for route in routes if route.path == '/api' + path)
        assert included.original_route is original
        assert isinstance(included.original_route, NutritionRoute)
        assert included.dependant.call is original.endpoint
        assert included.tags == original.tags
        assert included.response_model is original.response_model
        dependencies = {item.call.__name__ for item in included.dependant.dependencies}
        assert {'get_usuario_actual', 'get_db_readonly'} <= dependencies
    response = client.get('/api/planes/resumen', headers=user['auth_headers'])
    assert response.status_code == 200
    assert response.json()['planes_total'] == 0
    assert client.get('/api/planes/resumen').status_code == 401
    assert client.get('/api/planes/1/pdf').status_code == 401


def test_purchase_verification_openapi_documents_strict_input_and_response_union(factory_case):
    app, _, _, _ = factory_case
    spec = app.openapi()
    for suffix, required in [('request', {'action', 'plan'}), ('verify', {'action', 'plan', 'challenge', 'code'})]:
        operation = spec['paths']['/api/billing/email-verification/' + suffix]['post']
        body = operation['requestBody']
        assert body['required'] is True
        schema = body['content']['application/json']['schema']
        assert set(schema['required']) == required
        assert schema['additionalProperties'] is False
        assert {'401', '403', '409', '413', '415', '422', '429', '503'} <= operation['responses'].keys()
    response = spec['paths']['/api/billing/email-verification/request']['post']['responses']['200']['content']['application/json']['schema']
    assert {item['$ref'].split('/')[-1] for item in response['anyOf']} == {'ConfirmedContact', 'PendingCode'}
    assert spec['components']['schemas']['ConfirmedContact']['properties']['email_verification_required']['const'] is False
    assert spec['components']['schemas']['PendingCode']['properties']['email_verification_required']['const'] is True
    code = spec['paths']['/api/billing/email-verification/verify']['post']['requestBody']['content']['application/json']['schema']['properties']['code']
    assert code['type'] == 'string' and code['pattern'] == '^[0-9]{6}$'


def test_current_confirmed_contact_response_has_no_challenge_or_provider_work(factory_case, monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.routes import billing_email
    _, client, user, _ = factory_case
    begin = AsyncMock(side_effect=AssertionError('confirmed contact must not send'))
    monkeypatch.setattr(billing_email.service, 'begin', begin)
    with Session(get_engine()) as db:
        stored = db.get(Usuario, user['id'])
        stored.email_verified_at = datetime.now(UTC)
        stored.email_verified_contact_version = stored.notification_contact_version
        db.commit()
    response = client.post('/api/billing/email-verification/request', headers=user['auth_headers'],
                           json={'action': 'gym_stripe_checkout', 'plan': 'standard'})
    assert response.status_code == 200
    assert response.json() == {'email_verification_required': False, 'email_verified': True}
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    begin.assert_not_awaited()


def test_pending_code_and_grant_keep_existing_http_shapes(factory_case, monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import Usuario
    from web.routes import billing_email
    _, client, user, _ = factory_case
    challenge = 'A' * 43
    pending = {'email_verification_required': True, 'challenge': challenge,
               'expires_at': '2026-11-01T13:10:00+00:00', 'masked_email': 's***@example.invalid',
               'resend_after_seconds': 60}
    begin = AsyncMock(return_value=pending)
    monkeypatch.setattr(billing_email.service, 'begin', begin)
    response = client.post('/api/billing/email-verification/request', headers=user['auth_headers'],
                           json={'action': 'gym_stripe_checkout', 'plan': 'standard'})
    assert response.status_code == 200 and response.json() == pending
    assert response.headers['cache-control'] == 'no-store'
    begin.assert_awaited_once()
    # Only the HTTP/schema and persistence boundary are exercised here. The
    # service's actual one-use/expiry/attempt invariants have separate tests.
    granted = {'verification_token': 'B' * 43, 'expires_in_seconds': 300}
    verify = AsyncMock(return_value=granted)
    monkeypatch.setattr(billing_email.service, 'verify', verify)
    completed = client.post('/api/billing/email-verification/verify', headers=user['auth_headers'],
                            json={'action': 'gym_stripe_checkout', 'plan': 'standard',
                                  'challenge': challenge, 'code': '123456'})
    assert completed.status_code == 200 and completed.json() == granted
    assert completed.headers['cache-control'] == 'no-store'
    verify.assert_awaited_once()
    with Session(get_engine()) as db:
        stored = db.get(Usuario, user['id'])
        assert stored.email_verified_at is not None
        assert stored.email_verified_contact_version == stored.notification_contact_version


@pytest.mark.parametrize('suffix,content,content_type,status', [
    ('request', '{"action":"gym_stripe_checkout","plan":"standard","plan":"clinica"}', 'application/json', 422),
    ('request', '{"action":"gym_stripe_checkout","plan":"standard","email":"forged@example.invalid"}', 'application/json', 422),
    ('request', '{"action":"personal_stripe_checkout","plan":"standard"}', 'application/json', 422),
    ('request', '{"action":"gym_stripe_checkout","plan":"standard"}', 'text/plain', 415),
    ('request', ' ' * 4097, 'application/json', 413),
    ('verify', '{"action":"gym_stripe_checkout","plan":"standard","challenge":"' + 'A' * 43 + '","code":123456}', 'application/json', 422),
])
def test_documented_transport_rejections_do_not_reach_provider(factory_case, monkeypatch, suffix, content, content_type, status):
    from web.routes import billing_email
    _, client, user, _ = factory_case
    begin = AsyncMock(side_effect=AssertionError('invalid request reached service'))
    verify = AsyncMock(side_effect=AssertionError('invalid request reached service'))
    monkeypatch.setattr(billing_email.service, 'begin', begin)
    monkeypatch.setattr(billing_email.service, 'verify', verify)
    response = client.post('/api/billing/email-verification/' + suffix, content=content,
                           headers={**user['auth_headers'], 'Content-Type': content_type})
    assert response.status_code == status
    assert response.headers['cache-control'] == 'no-store'
    assert 'forged@example.invalid' not in response.text
    begin.assert_not_awaited()
    verify.assert_not_awaited()
