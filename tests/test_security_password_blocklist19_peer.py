"""Independent whole-value, changed-file and invitation privacy boundaries."""
import hashlib

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from tests import account_security37_http
from web import auth, password_blocklist
from web.account_values import validate_new_password

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http
COMMON = 'qwertyuiop' + ''.join(str(value) for value in range(1, 6))
ABSENT = 'Independent whole-value sentinel phrase 7639!'


def test_whole_value_digest_membership_and_absent_padding_are_exact():
    corpus = password_blocklist._CORPUS_PATH.read_bytes()
    digests = {corpus[offset:offset + 32] for offset in range(0, len(corpus), 32)}
    assert hashlib.sha256(COMMON.encode()).digest() in digests
    with pytest.raises(ValueError, match='demasiado común'):
        validate_new_password(COMMON)
    for candidate in (' ' + COMMON + ' ', COMMON + '-independent-suffix', ABSENT, 'e\u0301' * 12):
        assert hashlib.sha256(candidate.encode()).digest() not in digests
        assert validate_new_password(candidate) == candidate


def test_same_path_tamper_after_authenticated_use_fails_closed_without_cached_acceptance(tmp_path, monkeypatch):
    payload = password_blocklist._CORPUS_PATH.read_bytes()
    path = tmp_path / 'not-a-provider-token.bin'
    path.write_bytes(payload)
    monkeypatch.setattr(password_blocklist, '_CORPUS_PATH', path)
    assert validate_new_password(ABSENT) == ABSENT
    changed = bytearray(payload)
    changed[32 * 54_321 + 15] ^= 1
    path.write_bytes(changed)
    with pytest.raises(ValueError) as failure:
        validate_new_password(ABSENT)
    assert str(failure.value) == 'No se pudo comprobar la contraseña. Intenta de nuevo más tarde.'
    assert ABSENT not in str(failure.value) and str(path) not in str(failure.value)


def test_reader_uses_one_bounded_read_even_for_oversized_stream(monkeypatch):
    reads = []

    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, count):
            reads.append(count)
            return b'x' * count

    class Location:
        def open(self, mode):
            assert mode == 'rb'
            return Stream()

    monkeypatch.setattr(password_blocklist, '_CORPUS_PATH', Location())
    with pytest.raises(ValueError, match='No se pudo comprobar'):
        validate_new_password(ABSENT)
    assert reads == [3_199_969]


def test_real_existing_login_and_identity_survive_missing_setting_corpus(account_http, monkeypatch, tmp_path):
    from web.database.models import Usuario
    case = account_http
    with Session(case['admin']) as db:
        user = db.get(Usuario, case['member'])
        user.password_hash = auth.hash_password(COMMON)
        email = user.email
        db.commit()
    calls = []

    def not_a_login_dependency(*args):
        calls.append(True)
        raise AssertionError('Password-setting corpus was consulted by login/read')

    monkeypatch.setattr(password_blocklist, '_CORPUS_PATH', tmp_path / 'missing-corpus')
    monkeypatch.setattr(password_blocklist, 'contains_password', not_a_login_dependency)
    monkeypatch.setattr('web.account_values.contains_password', not_a_login_dependency)
    login = case['raw'].post('/api/auth/login', json={'email': email, 'password': COMMON})
    assert login.status_code == 200
    identity = case['raw'].get('/api/auth/me', headers={'Authorization': 'Bearer ' + login.json()['token']})
    assert identity.status_code == 200 and identity.json()['id'] == case['member']
    assert calls == []


@pytest.mark.parametrize('account_http', ['web.main_web'], indirect=True)
@pytest.mark.parametrize('path', ['/api/auth/accept-invite', '/api/auth/accept-invite/'])
@pytest.mark.parametrize('shape', ['malformed-json', 'top-level-list', 'nested-proof'])
def test_legacy_invitation_422_has_fixed_body_without_input_context_or_DML(account_http, path, shape, caplog):
    case = account_http
    marker = 'INERT-PRIVATE-CANDIDATE-CONTEXT'
    statements = []

    def observe(_conn, _cursor, sql, _parameters, _context, _many):
        statements.append(sql.lstrip().split(None, 1)[0].upper())

    event.listen(case['engine'], 'before_cursor_execute', observe)
    try:
        if shape == 'malformed-json':
            response = case['raw'].post(path, content='{"token":"' + marker + '","password":',
                                        headers={'Content-Type': 'application/json'})
        elif shape == 'top-level-list':
            response = case['raw'].post(path, json=[{'token': marker, 'password': ABSENT}])
        else:
            response = case['raw'].post(path, json={'token': {marker: [ABSENT]}, 'password': COMMON})
    finally:
        event.remove(case['engine'], 'before_cursor_execute', observe)
    assert response.status_code == 422
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    detail = response.json()['detail']
    assert set(detail) == {'code', 'message', 'fields'}
    assert detail['code'] == 'invitation_invalid_input' and set(detail['fields']) <= {'token', 'password'}
    assert all(value not in response.text + caplog.text for value in (marker, ABSENT, COMMON))
    assert not set(statements) & {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP'}
    assert not any('mb_refresh' in value for value in response.headers.get_list('set-cookie'))


@pytest.mark.parametrize('account_http', ['api.app'], indirect=True)
def test_API_factory_team_scope_remains_absent(account_http):
    raw = account_http['raw']
    assert raw.post('/api/auth/accept-invite', json={'token': 'inert', 'password': ABSENT}).status_code == 404
    assert raw.post('/api/auth/accept-invite/', json={}).status_code == 404
    assert raw.post('/api/gym/team/invite', json={}).status_code == 404
