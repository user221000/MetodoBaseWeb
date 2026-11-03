"""Explicit real Google/email HTTP stages with synthetic external transports.

Identity, signatures, snapshots, purpose and OTP consumption remain real.
This fixture neither intercepts HTTP calls nor grants an authenticated user.
"""
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.test_google_email_login import AtomicMemory


class WireMemory(AtomicMemory):
    def __init__(self):
        super().__init__()
        self.windows = {}

    async def eval(self, script, keys, key, *arguments):
        from web.rate_limiter_redis import _FIXED_WINDOW_LUA
        from web.services.google_email_login import CONSUME_LUA
        if script == _FIXED_WINDOW_LUA:
            assert keys == 1 and len(arguments) == 1
            if self.fail_eval:
                raise ConnectionError('Synthetic Redis wire unavailable')
            async with self.lock:
                count, expiry = self.windows.get(key, (0, self.now + arguments[0] * 1000))
                if expiry <= self.now:
                    count, expiry = 0, self.now + arguments[0] * 1000
                self.windows[key] = (count + 1, expiry)
                return [count + 1, max(1, (expiry - self.now) // 1000)]
        assert script == CONSUME_LUA
        return await super().eval(script, keys, key, *arguments)


def install(monkeypatch, settings):
    from web import rate_limiter_redis
    from web.services import email_service
    from web.services import google_email_login as service

    monkeypatch.setattr(settings, 'REDIS_URL', 'redis://127.0.0.1:56379/15')
    monkeypatch.setattr(settings, 'RESEND_API_KEY', 'synthetic-not-a-provider-key')
    monkeypatch.setattr(settings, 'RESEND_FROM_EMAIL', 'MetodoBase <no-reply@example.invalid>')
    cache, mail = WireMemory(), []

    async def redis():
        return cache

    def send(email, code):
        mail.append((email, code))
        return True

    monkeypatch.setattr(rate_limiter_redis, '_get_redis', redis)
    monkeypatch.setattr(email_service, 'send_google_login_code', send)
    return SimpleNamespace(cache=cache, mail=mail, service=service)


def counts(case):
    from web.database.models import (
        AuthExternalIdentity,
        GymProfile,
        PlanSuscripcion,
        RefreshToken,
        Usuario,
    )

    with Session(case['admin']) as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (Usuario, AuthExternalIdentity, GymProfile, PlanSuscripcion, RefreshToken))


def begin(case, *, credential=None, tipo='usuario'):
    credential = case['credential']() if credential is None else credential
    before = counts(case)
    mail = case['mail_transport'].mail
    sent = len(mail)
    response = case['client'].post('/api/auth/google', json={'credential': credential, 'tipo': tipo})
    assert response.status_code == 202
    body = response.json()
    assert body['email_verification_required'] is True
    assert not {'token', 'access_token', 'refresh_token', 'reauthentication_token'} & body.keys()
    assert counts(case) == before
    assert len(mail) == sent + 1 and mail[-1][0] == case['google']['email']
    assert case['google']['email'] not in response.text and credential not in response.text
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    return response


def verify(case, issued, *, code=None):
    code = case['mail_transport'].mail[-1][1] if code is None else code
    return case['client'].post('/api/auth/google/verify-email',
                               json={'challenge': issued.json()['challenge'], 'code': code})
