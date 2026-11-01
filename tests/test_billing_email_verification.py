"""Billing mailbox proof contracts using an atomic Redis protocol model.

No Redis Lua interpreter, database, provider, email delivery or charge is used.
The independent integration gate must cover real Lua separately.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from starlette.requests import Request


@pytest.fixture(scope="module")
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


class AtomicRedis:
    def __init__(self, service):
        self.service, self.rows, self.now = service, {}, 0
        self.lock = asyncio.Lock()
        self.fail = None
        self.expiries_seen = []

    def read(self, key):
        row = self.rows.get(key)
        if row and row[1] <= self.now:
            self.rows.pop(key)
            return None
        return row

    async def get(self, key):
        if self.fail == 'get': raise ConnectionError('private synthetic transport detail')
        row = self.read(key)
        return None if row is None else row[0]

    async def delete(self, key):
        if self.fail == 'delete': raise ConnectionError('private synthetic transport detail')
        return int(self.rows.pop(key, None) is not None)

    async def eval(self, script, count, *arguments):
        if self.fail == 'eval' or self.fail == script: raise ConnectionError('private synthetic transport detail')
        keys, args = arguments[:count], arguments[count:]
        async with self.lock:
            if script == self.service.BEGIN_LUA:
                challenge, active, cooldown = keys
                item, ttl, wait, reference = args
                row = self.read(cooldown)
                if row: return [0, max(1, (row[1] - self.now) // 1000)]
                if self.read(challenge): return [-1]
                self.rows[challenge] = (item, self.now + ttl * 1000)
                self.rows[active] = (reference, self.now + ttl * 1000)
                self.rows[cooldown] = ('1', self.now + wait * 1000)
                return [1]
            if script == self.service.ACTIVATE_LUA:
                challenge, active = keys
                payload, signature, digest, reference = args
                row, current = self.read(challenge), self.read(active)
                if not row or not current or current[0] != reference: return [0]
                item = json.loads(row[0])
                if (item['payload'], item['signature'], item['code_digest']) != (payload, signature, digest): return [0]
                item['delivery_ready'] = True
                self.rows[challenge] = (json.dumps(item), row[1])
                return [1]
            if script == self.service.VERIFY_LUA:
                challenge, active, grant = keys
                payload, signature, digest, maximum, proof, reference, ttl = args
                row, current = self.read(challenge), self.read(active)
                if not row or not current or current[0] != reference: return [0]
                item = json.loads(row[0])
                if (item['payload'], item['signature']) != (payload, signature) or item['delivery_ready'] is not True: return [0]
                if item['code_digest'] != digest:
                    item['attempts'] += 1
                    if item['attempts'] >= maximum: del self.rows[challenge]
                    else: self.rows[challenge] = (json.dumps(item), row[1])
                    return [0]
                if self.read(grant): return [-1]
                self.rows[grant] = (proof, self.now + ttl * 1000)
                self.rows[active] = (reference, self.now + ttl * 1000)
                del self.rows[challenge]
                return [1]
            assert script == self.service.CONSUME_LUA
            grant, active = keys
            expected, reference, mode, replacement = args
            row, current = self.read(grant), self.read(active)
            if not row or row[0] != expected or not current or current[0] != reference: return [0]
            self.expiries_seen.append(row[1])
            if mode == 'delete': del self.rows[grant]
            elif mode == 'replace': self.rows[grant] = (replacement, row[1])
            else: assert mode == 'confirm'
            return [1]


def request(path='/api/billing/checkout', method='POST'):
    return Request({'type': 'http', 'method': method, 'path': path,
                    'headers': [], 'client': ('192.0.2.70', 43000)})


@pytest.fixture
def case(monkeypatch):
    from web.services import billing_email_verification as service, email_service
    from web.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, 'REDIS_URL', 'redis://127.0.0.1:56379/15')
    monkeypatch.setattr(settings, 'RESEND_API_KEY', 'synthetic-provider-key-never-used')
    monkeypatch.setattr(settings, 'RESEND_FROM_EMAIL', 'Method Base <no-reply@example.invalid>')
    monkeypatch.setattr(settings, 'SECRET_KEY', 'synthetic-billing-test-secret-32-bytes-or-more')
    email = 'owner@example.invalid'
    binding = {'actor_id': 'synthetic-owner-1', 'session_version': 2,
        'notification_contact_version': 3, 'email_hash': hashlib.sha256(email.encode()).hexdigest(),
        'access_hash': 'a' * 64, 'catalog_digest': 'b' * 64, 'tipo': 'gym', 'role': 'owner',
        'team_gym_id': None, 'action': 'gym_stripe_checkout', 'plan': 'standard'}
    cache, mail, limits = AtomicRedis(service), [], []
    real_limit = service._limit

    async def redis(): return cache
    async def limit(req, purpose, value): limits.append((purpose, value['actor_id']))
    def send(recipient, code, label): mail.append((recipient, code, label)); return True
    monkeypatch.setattr(service, '_redis', redis)
    monkeypatch.setattr(service, '_limit', limit)
    monkeypatch.setattr(service, '_now', lambda: datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(milliseconds=cache.now))
    monkeypatch.setattr(email_service, 'send_billing_verification_code', send)
    return SimpleNamespace(service=service, cache=cache, mail=mail, limits=limits,
        binding=binding, email=email, request=request(), settings=settings, real_limit=real_limit)


async def begin(c): return await c.service.begin(c.binding, c.email, c.request)
async def proof(c):
    challenge = (await begin(c))['challenge']
    return (await c.service.verify(c.binding, challenge, c.mail[-1][1], c.request))['verification_token']
async def use(c, token, *, binding=None, body=None, key='purchase-synthetic-1', req=None):
    return await c.service.consume(binding or c.binding, token, req or c.request,
        body=body or {'plan': 'standard'}, idempotency_key=key)


@pytest.mark.asyncio
async def test_request_sends_only_to_bound_recipient_and_keeps_codes_out_of_redis(case):
    c = case
    value = await begin(c)
    assert set(value) == {'email_verification_required','challenge','expires_at','masked_email','resend_after_seconds'}
    assert value['email_verification_required'] is True and value['resend_after_seconds'] == 60
    assert c.service.TOKEN_PATTERN.fullmatch(value['challenge'])
    assert c.mail == [(c.email, c.mail[0][1], 'Standard')]
    assert c.service.CODE_PATTERN.fullmatch(c.mail[0][1])
    assert c.email not in json.dumps(value)
    key = c.service._challenge_key(value['challenge'])
    item = json.loads(c.cache.rows[key][0])
    assert item['delivery_ready'] is True and item['attempts'] == 0
    assert c.mail[0][1] not in c.cache.rows[key][0]
    assert value['challenge'] not in key and c.email not in key and c.binding['actor_id'] not in key
    assert c.cache.rows[key][1] == 600000


@pytest.mark.asyncio
async def test_cooldown_rejects_parallel_issues_and_preserves_first_code(case):
    c = case
    results = await asyncio.gather(begin(c), begin(c), return_exceptions=True)
    assert sum(isinstance(item, dict) for item in results) == 1
    failure = next(item for item in results if isinstance(item, HTTPException))
    assert failure.status_code == 429 and failure.headers['Retry-After'] == '60'
    assert len(c.mail) == 1


@pytest.mark.asyncio
async def test_resend_after_cooldown_invalidates_old_challenge_and_grant(case):
    c = case
    first = await begin(c)
    token = (await c.service.verify(c.binding, first['challenge'], c.mail[-1][1], c.request))['verification_token']
    c.cache.now = 61000
    await begin(c)
    with pytest.raises(HTTPException) as error: await use(c, token)
    assert error.value.status_code == 403
    with pytest.raises(HTTPException): await c.service.verify(c.binding, first['challenge'], c.mail[0][1], c.request)


@pytest.mark.asyncio
async def test_five_wrong_codes_survive_requests_preserve_expiry_and_exhaust_challenge(case):
    c = case
    challenge = (await begin(c))['challenge']
    key = c.service._challenge_key(challenge)
    correct = c.mail[-1][1]
    wrong = '000001' if correct != '000001' else '000002'
    for number in range(1, 6):
        c.cache.now += 1000
        with pytest.raises(HTTPException) as error:
            await c.service.verify(c.binding, challenge, wrong, c.request)
        assert error.value.detail['code'] == 'billing_email_code_invalid'
        if number < 5:
            raw, expiry = c.cache.rows[key]
            assert json.loads(raw)['attempts'] == number and expiry == 600000
    assert key not in c.cache.rows
    with pytest.raises(HTTPException): await c.service.verify(c.binding, challenge, correct, c.request)


@pytest.mark.asyncio
async def test_code_consumption_creates_one_grant_atomically(case):
    c = case
    challenge = (await begin(c))['challenge']
    results = await asyncio.gather(*[c.service.verify(c.binding, challenge, c.mail[-1][1], c.request) for _ in range(2)], return_exceptions=True)
    assert sum(isinstance(item, dict) for item in results) == 1
    result = next(item for item in results if isinstance(item, dict))
    assert result['expires_in_seconds'] == 300 and c.service.TOKEN_PATTERN.fullmatch(result['verification_token'])
    assert c.service._challenge_key(challenge) not in c.cache.rows
    assert c.cache.rows[c.service._grant_key(result['verification_token'])][1] == 300000


@pytest.mark.asyncio
async def test_same_exact_idempotent_retry_succeeds_without_extending_grant(case):
    c = case
    token = await proof(c)
    await use(c, token)
    c.cache.now = 30000
    await use(c, token)
    assert c.cache.expiries_seen == [300000, 300000]
    assert c.cache.rows[c.service._grant_key(token)][1] == 300000


@pytest.mark.asyncio
async def test_verification_near_code_expiry_keeps_full_advertised_grant_lifetime(case):
    c = case
    challenge = (await begin(c))['challenge']
    c.cache.now = 599000
    token = (await c.service.verify(c.binding, challenge, c.mail[-1][1], c.request))['verification_token']
    c.cache.now = 898000
    await use(c, token)
    assert c.cache.rows[c.service._grant_key(token)][1] == 899000


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['key','body','path','method','plan','action','actor_id','session_version',
    'notification_contact_version','email_hash','access_hash','role','tipo','team_gym_id','catalog_digest'])
async def test_verified_grant_cannot_authorize_another_request_or_identity(case, change):
    c = case
    token = await proof(c)
    await use(c, token)
    binding, body, key, req = dict(c.binding), {'plan':'standard'}, 'purchase-synthetic-1', c.request
    if change == 'key': key = 'purchase-synthetic-2'
    elif change == 'body': body['success_url'] = '/configuracion'
    elif change == 'path': req = request('/api/pagos/stripe/session')
    elif change == 'method': req = request(method='PUT')
    elif change in {'email_hash','access_hash','catalog_digest'}: binding[change] = 'f' * 64
    elif change in {'session_version','notification_contact_version'}: binding[change] += 1
    else: binding[change] = 'different'
    with pytest.raises(HTTPException) as error: await use(c, token, binding=binding, body=body, key=key, req=req)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_portal_without_idempotency_is_strictly_one_use(case):
    c = case
    c.binding.update(action='gym_stripe_portal', plan='manage')
    token = await proof(c)
    await use(c, token, body={'return_url':'/suscripciones'}, key=None)
    with pytest.raises(HTTPException) as error: await use(c, token, body={'return_url':'/suscripciones'}, key=None)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_expired_code_and_grant_cannot_open_payment(case):
    c = case
    challenge = (await begin(c))['challenge']
    c.cache.now = 600001
    with pytest.raises(HTTPException): await c.service.verify(c.binding, challenge, c.mail[-1][1], c.request)
    token = await proof(c)
    c.cache.now += 300001
    with pytest.raises(HTTPException) as error: await use(c, token)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_delivery_failure_or_pending_activation_never_grants_proof(case, monkeypatch):
    from web.services import email_service
    c = case
    monkeypatch.setattr(email_service, 'send_billing_verification_code', lambda *args: False)
    with pytest.raises(HTTPException) as error: await begin(c)
    assert error.value.status_code == 503 and error.value.detail['code'] == 'billing_email_delivery_unconfirmed'
    assert not any(':challenge:' in key for key in c.cache.rows)


@pytest.mark.asyncio
async def test_activation_failure_keeps_pending_code_unusable(case):
    c = case
    c.cache.fail = c.service.ACTIVATE_LUA
    with pytest.raises(HTTPException): await begin(c)
    c.cache.fail = None
    key = next(key for key in c.cache.rows if ':challenge:' in key)
    item = json.loads(c.cache.rows[key][0])
    assert item['delivery_ready'] is False
    state = json.loads(item['payload'])
    # The caller never received this token; extracting the fixture's keyed
    # reference still cannot make a pending challenge pass the Lua condition.
    assert state['binding'] == c.binding


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['begin','verify','consume'])
async def test_backend_uncertainty_fails_closed_without_exposing_details(case, stage, caplog):
    c = case
    token = await proof(c) if stage == 'consume' else None
    challenge = (await begin(c))['challenge'] if stage == 'verify' else None
    c.cache.fail = 'get' if stage != 'begin' else 'eval'
    with pytest.raises(HTTPException) as error:
        if stage == 'begin': await begin(c)
        elif stage == 'verify': await c.service.verify(c.binding, challenge, c.mail[-1][1], c.request)
        else: await use(c, token)
    assert error.value.status_code == 503
    assert 'private synthetic transport detail' not in caplog.text
    assert c.email not in caplog.text
    assert error.value.headers['Cache-Control'] == 'no-store'


@pytest.mark.asyncio
async def test_tampered_signed_binding_is_rejected_before_grant_creation(case):
    c = case
    challenge = (await begin(c))['challenge']
    key = c.service._challenge_key(challenge)
    item = json.loads(c.cache.rows[key][0]); payload = json.loads(item['payload'])
    payload['binding']['plan'] = 'clinica'; item['payload'] = json.dumps(payload)
    c.cache.rows[key] = (json.dumps(item), c.cache.rows[key][1])
    with pytest.raises(HTTPException) as error: await c.service.verify(c.binding, challenge, c.mail[-1][1], c.request)
    assert error.value.status_code == 503 and not any(':grant:' in name for name in c.cache.rows)


@pytest.mark.asyncio
async def test_unverified_or_malformed_grant_and_request_key_are_rejected(case):
    c = case
    for value in (None, '', 'a' * 42, 'a' * 44):
        with pytest.raises(HTTPException) as error: await use(c, value)
        assert error.value.status_code == 403
    token = await proof(c)
    for key in ('', 'bad\r\nkey', 'á', 'a' * 129):
        with pytest.raises(HTTPException) as error: await use(c, token, key=key)
        assert error.value.status_code == 422
    await use(c, token)


@pytest.mark.asyncio
async def test_legacy_short_printable_idempotency_key_remains_exactly_bound(case):
    c = case
    token = await proof(c)
    await use(c, token, key='x')
    await use(c, token, key='x')
    with pytest.raises(HTTPException): await use(c, token, key='y')


@pytest.mark.asyncio
async def test_recipient_mismatch_is_rejected_without_send(case):
    c = case
    with pytest.raises(HTTPException) as error: await c.service.begin(c.binding, 'another@example.invalid', c.request)
    assert error.value.status_code == 503 and c.mail == [] and c.cache.rows == {}


@pytest.mark.asyncio
@pytest.mark.parametrize('key', ['REDIS_URL','RESEND_API_KEY','RESEND_FROM_EMAIL','SECRET_KEY'])
async def test_missing_configuration_never_uses_local_fallback(case, monkeypatch, key):
    c = case
    monkeypatch.setattr(c.settings, key, '')
    with pytest.raises(HTTPException) as error: await begin(c)
    assert error.value.status_code == 503 and not c.cache.rows and not c.mail


@pytest.mark.asyncio
async def test_real_limit_adapter_hashes_account_and_ip_and_enforces_both(monkeypatch, case):
    from web import rate_limiter_redis
    c = case
    calls = []
    async def check(key, maximum, window, **kwargs):
        calls.append((key,maximum,window,kwargs)); return True, {'retry_after':0}, 'redis'
    monkeypatch.setattr(rate_limiter_redis, 'check_rate_limit', check)
    await c.real_limit(c.request, 'send', c.binding)
    assert [item[1] for item in calls] == [3,10]
    assert all(item[2] == 900 and item[3] == {'use_redis':True,'sensitive':True} for item in calls)
    assert c.binding['actor_id'] not in repr(calls) and '192.0.2.70' not in repr(calls)


def test_email_helper_escapes_plan_and_sends_no_code_in_subject(monkeypatch):
    from web.services import email_service
    sent = []
    monkeypatch.setattr(email_service, '_send', lambda *args: sent.append(args) or True)
    assert email_service.send_billing_verification_code('owner@example.invalid', '123456', '<Plan>') is True
    assert '123456' not in sent[0][1] and '123456' in sent[0][2] and '&lt;Plan&gt;' in sent[0][2]
    assert 'ningún cargo' in sent[0][2]
    assert email_service.send_billing_verification_code('owner@example.invalid', 'bad', 'Pro') is False
    assert len(sent) == 1
