"""Parser before allocation, private limiter keys, and exact first-party paths."""
import asyncio
import json
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from web.client_link_schemas import InvitationAccept,InvitationIssue,LinkVersion,PlanPublication
from web.client_link_paths import is_member_link_api,is_member_link_private
from web.routes.client_links import body,enforce_limit


def parse(chunks,model=InvitationAccept,content_type='application/json'):
    calls=[]
    async def receive():
        calls.append(True)
        if len(calls)>len(chunks):raise AssertionError('Input read beyond bounded stream')
        return {'type':'http.request','body':chunks[len(calls)-1],'more_body':len(calls)<len(chunks)}
    request=Request({'type':'http','method':'POST','path':'/api/usuario/vinculaciones/aceptar',
        'headers':[(b'content-type',content_type.encode())]},receive)
    return request,calls,lambda:asyncio.run(body(model)(request))


def test_body_stops_reading_at_limit_before_json_parser_and_never_reads_tail(monkeypatch):
    request,calls,run=parse([b' '*16384,b'x',b'never-read'])
    monkeypatch.setattr(json,'loads',lambda *args,**kwargs:pytest.fail('Parser ran before rejecting volume'))
    with pytest.raises(HTTPException) as denied:run()
    assert denied.value.status_code==413 and len(calls)==2


@pytest.mark.parametrize('raw',[
    b'{"token":"'+b'A'*43+b'","expected_version":1,"confirm":true,"gym_id":"foreign"}',
    b'{"token":"'+b'A'*43+b'","expected_version":1,"confirm":true,"confirm":false}',
    b'{"token":"'+b'A'*43+b'","expected_version":"1","confirm":true}',
    b'{"token":"'+b'A'*43+b'","expected_version":1,"confirm":1}',
    b'{"token":"'+b'A'*43+b'","expected_version":NaN,"confirm":true}',
    b'{"token":"'+b'A'*43+b'","expected_version":1,"confirm":false}',
    b'['*2000+b']'*2000,b'\xff',b'{}',
],ids=['extra-authority','duplicate','coercion','bool-coercion','nonfinite','no-consent','depth','utf8','missing'])
def test_invalid_input_is_rejected_entirely_without_echoing_bearer(raw):
    _,_,run=parse([raw])
    with pytest.raises(HTTPException) as denied:run()
    assert denied.value.status_code==422 and denied.value.detail['code']=='member_invalid_input'
    assert 'A'*43 not in str(denied.value.detail)


def test_non_json_media_type_rejected_before_any_body_read():
    _,calls,run=parse([b'must-not-read'],content_type='text/plain')
    with pytest.raises(HTTPException) as denied:run()
    assert denied.value.status_code==415 and calls==[]


def test_recipient_email_uses_shared_canonical_form_and_request_key_is_explicit():
    value=InvitationIssue(recipient_email='  Person@Example.Invalid ',request_key='one-purpose-v1')
    assert value.recipient_email=='person@example.invalid'
    assert LinkVersion(expected_version=1).expected_version==1


@pytest.mark.parametrize('purpose,extra',[('issue',{'recipient':'person@example.invalid'}),('accept',{'token':'A'*43})])
def test_limiter_does_not_store_account_token_or_actor_in_cleartext(monkeypatch,purpose,extra):
    from web import rate_limiter_redis
    from web import settings as module
    settings=SimpleNamespace(SECRET_KEY='synthetic-only-key',REDIS_URL='redis://synthetic.invalid',is_production=True)
    monkeypatch.setattr(module,'get_settings',lambda:settings)
    keys=[]
    async def check(key,limit,window,**kwargs):
        keys.append(key);assert window==900 and kwargs=={'use_redis':True,'sensitive':True}
        return True,{'retry_after':0},'redis'
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',check)
    request=Request({'type':'http','method':'POST','path':'/api/usuario/vinculaciones/aceptar','headers':[],
        'client':('127.0.0.1',1)})
    asyncio.run(enforce_limit(request,{'id':'synthetic-actor'},purpose,**extra))
    assert len(keys)==3 and all('person@' not in key and 'A'*43 not in key and 'synthetic-actor' not in key and '127.0.0.1' not in key for key in keys)


def test_production_without_shared_limiter_fails_before_mutation(monkeypatch):
    from web import settings as module
    monkeypatch.setattr(module,'get_settings',lambda:SimpleNamespace(REDIS_URL='',is_production=True))
    with pytest.raises(HTTPException) as denied:asyncio.run(enforce_limit(None,{'id':'actor'},'accept',token='A'*43))
    assert denied.value.status_code==503


@pytest.mark.parametrize('path',[
    '/api/usuario/vinculos','/api/usuario/vinculaciones/aceptar','/api/usuario/vinculaciones/invitacion',
    '/api/clientes/c/vinculacion/invitaciones','/api/clientes/c/vinculacion',
    '/api/usuario/vinculos/a0000000-0000-0000-0000-000000000001/plan',
])
def test_new_api_paths_fail_closed_under_redis_outage(path):
    from web.rate_limiter_redis import _sensitive_path
    assert is_member_link_api(path) and is_member_link_private(path) and _sensitive_path(path)


@pytest.mark.parametrize('path',['/api/clientes/c/vinculacion-other','/api/usuario/vinculos-spoof','/auth/accept-client-link/other','/api/clientes/c/vinculacion/invitaciones/x/reenviar/other'])
def test_unrelated_paths_do_not_receive_the_new_first_party_policy(path):
    assert not is_member_link_private(path)


@pytest.mark.parametrize('changes',[
    {},{'expected_publication_id':True},{'expected_publication_id':5},
    {'expected_publication_id':'A0000000-0000-0000-0000-000000000001','expected_publication_version':1},
    {'expected_publication_id':'not-a-uuid','expected_publication_version':1},
    {'expected_publication_id':None,'expected_publication_version':1},
    {'expected_publication_id':'a0000000-0000-0000-0000-000000000001','expected_publication_version':0},
    {'expected_publication_id':None,'expected_publication_version':True},
])
def test_publication_observation_requires_explicit_strict_identity_and_matching_version(changes):
    values={'plan_id':1,'expected_link_version':2,'expected_publication_version':0,**changes}
    _,_,run=parse([json.dumps(values).encode()],model=PlanPublication)
    with pytest.raises(HTTPException) as denied:run()
    assert denied.value.status_code==422 and denied.value.detail['code']=='member_invalid_input'


@pytest.mark.parametrize('identity,version',[(None,0),('a0000000-0000-0000-0000-000000000001',1)])
def test_publication_observation_accepts_only_explicit_create_or_exact_replacement(identity,version):
    values={'plan_id':1,'expected_link_version':2,'expected_publication_version':version,'expected_publication_id':identity}
    _,_,run=parse([json.dumps(values).encode()],model=PlanPublication)
    result=run()
    assert result.expected_publication_id==identity and result.expected_publication_version==version
