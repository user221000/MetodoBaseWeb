"""Uniform public admission and real counters, without provider connections."""
import pytest
from tests.test_account_recovery_contract_before import recovery_case
from tests.test_password_recovery import recovery_http,wait_idle


@pytest.mark.parametrize('email',['recovery-before@example.invalid','missing@example.invalid'])
def test_real_account_limit_never_changes_existing_account_or_exposes_bucket(recovery_http,email):
    case=recovery_http
    for _ in range(3):
        response=case.client.post('/api/auth/password-reset/request',json={'email':email})
        assert response.status_code==202,response.text
    rejected=case.client.post('/api/auth/password-reset/request',json={'email':email})
    assert rejected.status_code==429 and int(rejected.headers['retry-after'])>0
    assert rejected.headers['cache-control']=='no-store' and rejected.headers['referrer-policy']=='no-referrer'
    assert email not in rejected.text
    wait_idle(case.client)


def test_full_dispatcher_returns_same_global_unavailable_before_account_lookup(recovery_http,monkeypatch):
    case=recovery_http
    monkeypatch.setattr(case.client.app.state.recovery_dispatcher,'submit',lambda *args:False)
    known=case.client.post('/api/auth/password-reset/request',json={'email':'recovery-before@example.invalid'})
    missing=case.client.post('/api/auth/password-reset/request',json={'email':'missing@example.invalid'})
    assert known.status_code==missing.status_code==503 and known.json()==missing.json()
    assert case.messages==[]


def test_invalid_bearer_real_limit_and_malformed_input_do_not_echo_secrets(recovery_http):
    case=recovery_http
    payload={'token':'v'*43,'new_password':'SyntheticNewPassword456','confirm_password':'SyntheticNewPassword456'}
    for _ in range(10):
        response=case.client.post('/api/auth/password-reset/confirm',json=payload)
        assert response.status_code==400
    rejected=case.client.post('/api/auth/password-reset/confirm',json=payload)
    assert rejected.status_code==429 and int(rejected.headers['retry-after'])>0
    assert payload['token'] not in rejected.text and payload['new_password'] not in rejected.text
    for raw,status in [(b'private-not-json',422),(b'['+b' '*4096+b']',413)]:
        response=case.client.post('/api/auth/password-reset/confirm',content=raw,headers={'Content-Type':'application/json'})
        assert response.status_code==status and 'private-not-json' not in response.text
        assert response.headers['cache-control']=='no-store' and response.headers['referrer-policy']=='no-referrer'
