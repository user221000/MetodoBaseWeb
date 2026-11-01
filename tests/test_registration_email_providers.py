"""Provider-neutral registration/login and own-mailbox routing, without sends.

Real auth and billing HTTP routes plus isolated SQLite; all outgoing mail and
the billing Redis protocol are doubles. These cases do not prove provider or
Apple private-relay delivery, mailbox ownership, or production behavior.
"""
from datetime import datetime, timezone

import pytest

from tests.test_registration_validation import (
    HEADERS,
    database_schema,
    isolated_database,
    otp_case,
    registration_http,
)
from tests.test_billing_email_verification import case as mailbox_case

__all__=['database_schema','isolated_database','otp_case','registration_http','mailbox_case']

DOMAINS=[
    pytest.param('gmail.com',id='gmail'),
    pytest.param('outlook.com',id='outlook'),
    pytest.param('hotmail.com',id='hotmail'),
    pytest.param('live.com',id='live'),
    pytest.param('icloud.com',id='icloud'),
    pytest.param('me.com',id='apple-me'),
    pytest.param('mac.com',id='apple-mac'),
    pytest.param('privaterelay.appleid.com',id='apple-private-relay'),
    pytest.param('ejemplo.invalid',id='corporate'),
]


@pytest.mark.parametrize('kind,role',[('gym','owner'),('usuario','viewer')])
@pytest.mark.parametrize('domain',DOMAINS)
def test_mail_provider_does_not_change_registration_login_or_recipient(
    registration_http,mailbox_case,monkeypatch,kind,role,domain,
):
    from web import auth
    from web.database.models import Usuario
    from web.routes.billing_email import router as billing_email_router
    from web.services import email_service

    case,client=registration_http
    welcome=[]
    monkeypatch.setattr(auth,'SECRET_KEY',case.settings.SECRET_KEY)
    monkeypatch.setattr(mailbox_case.service,'_now',lambda:datetime.now(timezone.utc))
    monkeypatch.setattr(email_service,'send_welcome',lambda email,name:welcome.append((email,name)) or True)
    def forbidden_transport(*args,**kwargs):
        raise AssertionError('A registration provider probe attempted real mail transport')
    monkeypatch.setattr(email_service,'_send',forbidden_transport)
    client.app.include_router(billing_email_router,prefix='/api')

    typed='  Synthetic.'+kind+'@'+domain.upper()+'  '
    expected=typed.strip().lower()
    password='Atlas-Cedro-Rio-Sintetico-2026!'
    created=client.post('/api/auth/registro',headers=HEADERS,
        json={'email':typed,'password':password,'nombre':'Persona de prueba','apellido':'', 'tipo':kind})
    assert created.status_code==200
    identity=auth.verificar_token(created.json()['token'])
    assert identity['email']==expected and identity['tipo']==kind and identity['role']==role
    assert created.json()['session_mode']=='browser' and 'refresh_token' not in created.json()
    with case.sessions() as db:
        user=db.get(Usuario,identity['id'])
        assert user.email==expected
        assert auth.verify_password(password,user.password_hash)
        assert user.email_verified_at is None
    assert welcome==[(expected,'Persona de prueba')]

    login=client.post('/api/auth/login',headers=HEADERS,
        json={'email':typed,'password':password,'tipo':kind})
    assert login.status_code==200
    logged=auth.verificar_token(login.json()['token'])
    assert logged['id']==identity['id'] and logged['email']==expected
    assert len(welcome)==1

    action='gym_stripe_checkout' if kind=='gym' else 'personal_stripe_checkout'
    plan='standard' if kind=='gym' else 'pro'
    sent=client.post('/api/billing/email-verification/request',
        headers={'Authorization':'Bearer '+login.json()['token']},json={'action':action,'plan':plan})
    assert sent.status_code==200 and sent.json()['email_verification_required'] is True
    assert sent.json()['masked_email'].endswith('@'+domain)
    assert [message[0] for message in mailbox_case.mail]==[expected]
