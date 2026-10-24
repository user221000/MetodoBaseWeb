"""Both real factories, original authentication harness and closed HTTP inputs."""
import uuid
import pytest
from tests import account_security37_http as original
from tests.privacy39_fixtures import privacy39_engine,database_schema,isolated_database
from tests.test_account_security37_http import headers,private

account37_engine=privacy39_engine
followup_db=original.followup_db
account_http=original.account_http
PREFIX='/api/account/privacy'


def test_authenticated_owner_request_idempotency_does_not_close_portfolio(account_http):
    case=account_http;body={'idempotency_key':str(uuid.uuid4()),'intent':'erase_personal_data'}
    first=case['raw'].post(PREFIX+'/requests',json=body,headers=headers(case))
    assert first.status_code==201;private(first)
    repeated=case['raw'].post(PREFIX+'/requests',json=body,headers=headers(case))
    assert repeated.status_code==201 and repeated.json()==first.json()
    row=first.json();assert row['state']=='blocked' and not row['account_closed']
    closed=case['raw'].post(PREFIX+'/requests/'+row['id']+'/close-account',headers=headers(case),json={
        'expected_version':row['version'],'confirmation':'close_account','reauthentication_token':'A'*43})
    assert closed.status_code==200 and closed.json()['reason']=='professional_obligations_require_review'
    assert not closed.json()['account_closed'] and case['raw'].get('/api/auth/me').status_code==200
    assert not any('mb_refresh' in value for value in closed.headers.get_list('set-cookie'))


@pytest.mark.parametrize('raw',['{"idempotency_key":"private-marker","subject_id":"foreign"}',
    '{"intent":"erase_personal_data","intent":"other"}', '{"idempotency_key":NaN}', '[]'])
def test_privacy_rejects_ambiguous_or_foreign_scope_without_echo(account_http,raw):
    response=account_http['raw'].post(PREFIX+'/requests',content=raw,
        headers={**headers(account_http),'Content-Type':'application/json'})
    assert response.status_code==422 and 'private-marker' not in response.text
    private(response)


def test_owner_personal_fact_download_cannot_export_portfolio(account_http):
    response=account_http['raw'].get(PREFIX+'/personal-facts')
    assert response.status_code in {403,409}


def test_real_active_A_B_authorization_and_personal_closure_in_both_factories(account_http):
    from tests.followup34_http import PASSWORD
    from tests.test_privacy39_transactions import policy_for_now
    case=account_http
    foreign=case['raw'].post(PREFIX+'/requests',headers=headers(case),json={
        'idempotency_key':str(uuid.uuid4()),'intent':'erase_personal_data'}).json()
    email=uuid.uuid4().hex+'@example.invalid'
    created=case['raw'].post('/api/auth/registro',json={'email':email,'password':PASSWORD,'nombre':'Synthetic privacy personal','tipo':'usuario'})
    assert created.status_code==200
    login=case['raw'].post('/api/auth/login',json={'email':email,'password':PASSWORD})
    assert login.status_code==200
    case['raw'].headers['Authorization']='Bearer '+login.json()['token']
    me=case['raw'].get('/api/auth/me');assert me.status_code==200 and me.json()['id']!=case['user']
    assert case['raw'].get(PREFIX+'/requests/'+foreign['id']).status_code==404
    row=case['raw'].post(PREFIX+'/requests',headers=headers(case),json={
        'idempotency_key':str(uuid.uuid4()),'intent':'erase_personal_data'}).json()
    policy=policy_for_now();case['raw'].app.state.privacy_policy_provider=lambda **_:policy
    authenticated=case['raw'].post('/api/auth/mfa/reauth',headers=headers(case),json={'password':PASSWORD})
    assert authenticated.status_code==200
    payload={'expected_version':row['version'],'confirmation':'close_account',
        'reauthentication_token':authenticated.json()['reauthentication_token']}
    foreign_close=case['raw'].post(PREFIX+'/requests/'+foreign['id']+'/close-account',headers=headers(case),json=payload)
    assert foreign_close.status_code==404
    changed=case['raw'].post(PREFIX+'/requests/'+row['id']+'/close-account',headers=headers(case),json={**payload,'expected_version':row['version']+1})
    assert changed.status_code==409
    result=case['raw'].post(PREFIX+'/requests/'+row['id']+'/close-account',headers=headers(case),json=payload)
    assert result.status_code==200 and result.json()['account_closed'] and result.json()['sessions_revoked']
    private(result)
    assert any('mb_refresh_dev=' in value and 'Max-Age=0' in value for value in result.headers.get_list('set-cookie'))
    assert not result.json()['erasure_complete'] and case['raw'].get('/api/auth/me').status_code==401


def test_privacy_browser_admission_precedes_bearer_for_closed_transport_inputs(account_http,monkeypatch):
    from web import auth
    case=account_http;calls=[]
    monkeypatch.setattr(auth,'verificar_token',lambda *args:calls.append(True))
    normal=list({**headers(case),'Content-Type':'application/json'}.items())
    def without(name):return [(key,value) for key,value in normal if key.lower()!=name.lower()]
    bad=[
        ('',without('Origin')+[('Origin','https://foreign.example.invalid')],403),
        ('',without('Origin'),403),
        ('',normal+[('Origin',headers(case)['Origin'])],403),
        ('',without('X-MetodoBase-Browser'),403),
        ('',without('X-MetodoBase-Browser')+[('X-MetodoBase-Browser','0')],403),
        ('',normal+[('X-MetodoBase-Browser','1')],403),
        ('?untrusted=1',normal,403),
        ('/',normal,403),
        ('',without('Content-Type'),415),
        ('',without('Content-Type')+[('Content-Type','text/plain')],415),
        ('',normal+[('Content-Type','application/json')],415),
    ]
    for path in (PREFIX+'/requests',PREFIX+'/requests/'+'a'*32+'/close-account'):
        for suffix,submitted,status in bad:
            response=case['raw'].post(path+suffix,content='{}',headers=submitted)
            assert response.status_code==status
            private(response)
            assert not any('mb_refresh' in value for value in response.headers.get_list('set-cookie'))
    assert calls==[]


def test_privacy_private_get_failures_do_not_inherit_public_csp(account_http,monkeypatch):
    from web.services import account_privacy
    case=account_http;path=PREFIX+'/requests/'+'a'*32
    missing=case['raw'].get(path)
    assert missing.status_code==404
    private(missing)
    blocked=case['raw'].get(PREFIX+'/personal-facts')
    assert blocked.status_code in {403,409}
    private(blocked)
    def unavailable(*args,**kwargs):raise RuntimeError('synthetic-private-failure')
    monkeypatch.setattr(account_privacy,'read_request',unavailable)
    failed=case['raw'].get(path)
    assert failed.status_code==503 and 'synthetic-private-failure' not in failed.text
    private(failed)
    case['raw'].headers.pop('Authorization')
    for target in (path,PREFIX+'/personal-facts'):
        unauthorized=case['raw'].get(target)
        assert unauthorized.status_code==401
        private(unauthorized)
    # A surviving refresh cookie is never identity for a privacy resource.
    case['raw'].cookies.set('mb_refresh_dev','synthetic-without-bearer')
    cookie_only=case['raw'].post(PREFIX+'/requests',headers=headers(case),json={
        'idempotency_key':str(uuid.uuid4()),'intent':'erase_personal_data'})
    assert cookie_only.status_code==401
    private(cookie_only)


def test_privacy_matchers_reject_neighbor_paths_and_noncanonical_request_ids():
    from web.privacy_paths import is_privacy_post,is_privacy_post_boundary,is_privacy_private
    close=PREFIX+'/requests/'+'a'*32+'/close-account'
    for path in (PREFIX+'/requests',close):
        assert is_privacy_post(path) and is_privacy_post_boundary(path) and is_privacy_private(path)
        assert not is_privacy_post(path+'/') and is_privacy_post_boundary(path+'/') and is_privacy_private(path+'/')
        assert not is_privacy_post_boundary(path+'//') and not is_privacy_private(path+'//')
    assert is_privacy_private(PREFIX+'/requests/'+'a'*32)
    assert is_privacy_private(PREFIX+'/personal-facts')
    for path in (PREFIX+'/requests-extra',close+'-extra',PREFIX+'/requests/'+'A'*32+'/close-account',
            PREFIX+'/requests/'+'a'*31+'/close-account',PREFIX+'/requests/'+'a'*33+'/close-account',
            PREFIX+'/requests/'+'g'*32+'/close-account',PREFIX+'/personal-facts-extra',
            PREFIX+'/requests/'+'a'*32+'/other',PREFIX+'/requests/'+'a'*32+'?other=1'):
        assert not is_privacy_post(path) and not is_privacy_post_boundary(path) and not is_privacy_private(path)
