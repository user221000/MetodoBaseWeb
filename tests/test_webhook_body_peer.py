"""Independent full-factory ingress tests; real signatures, no provider calls.

ASGI messages represent chunked and dishonest-length transports directly.
No proxy is claimed by this in-process HTTP composition check.
"""
import asyncio
import hashlib
import hmac
import json
import time

import pytest

SURFACES = [
    ('web', '/api/billing/webhook', 'stripe'),
    ('web', '/api/billing/mp/webhook', 'mp'),
    ('api', '/api/billing/webhook', 'stripe'),
    ('api', '/api/billing/mp/webhook', 'mp'),
    ('api', '/api/pagos/stripe/webhook', 'stripe'),
    ('api', '/api/pagos/mp/webhook', 'mp'),
]
LIMIT = 65536
SECRET = 'offline-qa-webhook-owner-secret'


@pytest.fixture
def ingress(monkeypatch):
    from web.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, 'BASE_URL', 'https://testserver')
    # The default on the old version is intentionally not patched with raising=False.
    # Before this setting exists the independent RED must still reach the old route.
    if hasattr(settings, 'WEBHOOK_MAX_BODY_BYTES'):
        monkeypatch.setattr(settings, 'WEBHOOK_MAX_BODY_BYTES', LIMIT)
    monkeypatch.setattr(settings, 'STRIPE_WEBHOOK_SECRET', SECRET)
    monkeypatch.setattr(settings, 'MERCADOPAGO_WEBHOOK_SECRET', SECRET)
    from web.services import stripe_service, mercadopago_service
    originals = {'stripe': stripe_service.verify_webhook, 'mp': mercadopago_service.verify_notification}
    seen = []
    def stripe_verify(raw, signature):
        seen.append(('stripe', raw))
        return originals['stripe'](raw, signature)
    def mp_verify(request, raw):
        seen.append(('mp', raw))
        return originals['mp'](request, raw)
    monkeypatch.setattr(stripe_service, 'verify_webhook', stripe_verify)
    monkeypatch.setattr(mercadopago_service, 'verify_notification', mp_verify)
    # Provider writes/reads must be impossible even if a supposedly ignored event regresses.
    def blocked(*args, **kwargs):
        raise AssertionError('external payment capability must not execute')
    monkeypatch.setattr(mercadopago_service, 'get_sdk', blocked)
    import stripe
    monkeypatch.setattr(stripe.Subscription, 'retrieve', blocked)
    monkeypatch.setattr(stripe.Invoice, 'retrieve', blocked)
    apps = {}
    def run(surface, variant, length=None):
        kind, path, provider = surface
        if kind not in apps:
            if kind == 'web':
                from web.main_web import create_app
            else:
                from api.app import create_app
            apps[kind] = create_app()
        body = {'id': 'evt_peer_bounded', 'type': 'qa.ignored', 'livemode': False,
                'data': {'object': {}, 'id': '123'}, 'label': 'áé\n'}
        if provider == 'mp':
            body.update(type='merchant_order', id='notification-peer')
        raw = json.dumps(body, ensure_ascii=False, indent=1).encode('utf-8')
        if length is not None:
            assert length >= len(raw)
            raw += b' ' * (length-len(raw))
        stamp = str(int(time.time()))
        headers = [(b'host', b'testserver'), (b'content-type', b'application/json')]
        query = b''
        if provider == 'stripe':
            digest = hmac.new(SECRET.encode(), stamp.encode()+b'.'+raw, hashlib.sha256).hexdigest()
            headers.append((b'stripe-signature', f't={stamp},v1={digest}'.encode()))
        else:
            digest = hmac.new(SECRET.encode(), f'id:123;request-id:peer-owned;ts:{stamp};'.encode(), hashlib.sha256).hexdigest()
            headers += [(b'x-request-id', b'peer-owned'), (b'x-signature', f'ts={stamp},v1={digest}'.encode())]
            query = b'data.id=123'
        if variant == 'chunked':
            headers.append((b'transfer-encoding', b'chunked'))
        elif variant == 'length':
            headers.append((b'content-length', str(len(raw)).encode()))
        elif variant == 'understated':
            headers.append((b'content-length', b'1'))
        elif variant == 'duplicate':
            headers += [(b'content-length', b'1'), (b'content-length', b'1')]
        elif variant == 'both':
            headers += [(b'content-length', str(len(raw)).encode()), (b'transfer-encoding', b'chunked')]
        elif variant == 'overstated':
            headers.append((b'content-length', str(LIMIT+1).encode()))
        elif variant == 'nonnumeric':
            headers.append((b'content-length', b'bad'))
        chunks = [raw[i:i+4093] for i in range(0, len(raw), 4093)]
        count = 0
        async def invoke():
            responses = []
            async def receive():
                nonlocal count
                if count < len(chunks):
                    index = count
                    count += 1
                    return {'type': 'http.request', 'body': chunks[index], 'more_body': count < len(chunks)}
                await asyncio.Event().wait()
            async def send(message):
                responses.append(message)
            scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                     'method': 'POST', 'scheme': 'https', 'path': path, 'raw_path': path.encode(),
                     'root_path': '', 'query_string': query, 'headers': headers,
                     'server': ('testserver', 443), 'client': ('127.0.0.1', 41357)}
            await asyncio.wait_for(apps[kind](scope, receive, send), timeout=10)
            start = next(item for item in responses if item['type'] == 'http.response.start')
            output = b''.join(item.get('body', b'') for item in responses if item['type'] == 'http.response.body')
            return start['status'], json.loads(output)
        status, response = asyncio.run(invoke())
        return status, response, raw, count
    return run, seen


@pytest.mark.parametrize('surface', SURFACES)
@pytest.mark.parametrize('variant', ['chunked', 'length'])
def test_exact_limit_reaches_real_signature_verifier_without_reserializing(ingress, surface, variant):
    run, seen = ingress
    status, response, raw, _ = run(surface, variant, LIMIT)
    assert status == 200, response
    assert seen == [(surface[2], raw)]


@pytest.mark.parametrize('surface', SURFACES)
@pytest.mark.parametrize('variant', ['chunked', 'understated', 'overstated'])
def test_limit_plus_one_is_rejected_before_signature_or_provider(ingress, surface, variant):
    run, seen = ingress
    status, response, _, reads = run(surface, variant, LIMIT+1)
    assert status == 413, response
    assert response['detail']['code'] == 'webhook_body_too_large'
    assert seen == []
    if variant == 'overstated':
        assert reads == 0


@pytest.mark.parametrize('surface', SURFACES)
@pytest.mark.parametrize('variant', ['duplicate', 'both', 'nonnumeric', 'understated'])
def test_ambiguous_or_mismatched_length_cannot_reach_signature_verifier(ingress, surface, variant):
    run, seen = ingress
    status, response, _, _ = run(surface, variant)
    assert status == 400, response
    assert response['detail']['code'] == 'webhook_content_length_invalid'
    assert seen == []
