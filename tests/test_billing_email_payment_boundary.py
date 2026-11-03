"""New admission requirement plus unchanged private provider-error translation."""
from unittest.mock import AsyncMock, patch
from tests.test_billing_integrity import billing_case, _stored_plan


def test_no_email_confirmation_never_opens_provider_or_grants_pro(billing_case):
    from web.auth import crear_access_token
    client, factory, principal = billing_case
    token = crear_access_token(principal)
    with patch('web.services.stripe_service.create_subscription_with_payment_method') as provider:
        response = client.post('/api/usuario/stripe-subscribe',
            json={'plan': 'pro', 'payment_method_id': 'pm_synthetic'},
            headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'billing_email_required'
    provider.assert_not_called()
    assert _stored_plan(factory, principal['id']) == 'starter'


def test_missing_primary_token_cannot_reach_email_or_provider(billing_case):
    client, factory, principal = billing_case
    with patch('web.services.stripe_service.create_subscription_with_payment_method') as provider:
        response = client.post('/api/usuario/stripe-subscribe',
            json={'plan': 'pro', 'payment_method_id': 'pm_synthetic'})
    assert response.status_code == 401
    provider.assert_not_called()
    assert _stored_plan(factory, principal['id']) == 'starter'


def test_confirmed_boundary_keeps_provider_failure_private(billing_case, caplog):
    # This isolated regression covers downstream translation. Dedicated real
    # JWT/Redis HTTP checks exercise the actual email admission boundary.
    client, factory, principal = billing_case
    sentinel = 'synthetic-sensitive-provider-error-token-and-health-note'
    with patch('web.routes.usuario._require_billing_email', new=AsyncMock(return_value=dict(principal))), \
         patch('web.services.stripe_service.create_subscription_with_payment_method', side_effect=Exception(sentinel)):
        response = client.post('/api/usuario/stripe-subscribe',
            json={'plan': 'pro', 'payment_method_id': 'pm_synthetic'})
    assert response.status_code == 502
    assert response.json()['detail']['code'] == 'payment_service_unavailable'
    assert response.json()['detail']['request_id']
    assert sentinel not in response.text and sentinel not in caplog.text
    assert _stored_plan(factory, principal['id']) == 'starter'
