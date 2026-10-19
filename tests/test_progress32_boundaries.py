"""Current32 technical limits, own retirement authority and paged export."""
import json
import uuid
from datetime import timedelta

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from tests.test_personal_progress_http import progress_db,progress_http,accepted,grant,command


def test_retirement_identity_inclusive_sv_bound_without_personal_authority(progress_http):
    from web.database.models import Usuario,UserRole
    from web.services.progress_share import list_own_consents
    c=progress_http
    for value,allowed in [(2147483647,True),(-1,False),(2147483648,False)]:
        with Session(c['admin']) as db:
            actor=db.get(Usuario,c['person']);actor.role=UserRole.OWNER;actor.session_version=value;db.commit()
        with Session(c['engine']) as db:
            if allowed:assert list_own_consents(db,{'id':c['person'],'session_version':value})=={'items':[],'next_after':None}
            else:
                with pytest.raises(HTTPException) as denied:list_own_consents(db,{'id':c['person'],'session_version':value})
                assert denied.value.status_code==401
    with Session(c['engine']) as db,pytest.raises(HTTPException):list_own_consents(db,{'id':c['person'],'session_version':True})


def test_dates_body_duplicate_unknown_nonfinite_and_response_privacy_are_integral(progress_http):
    c=progress_http;client=c['client_http'];headers={**c['headers']['person'],'Content-Type':'application/json'}
    key=str(uuid.uuid4());path='/api/usuario/progreso/mediciones/'+key;body=command(c)
    bads=[('{'+('"x":0,'*1400)+'"x":0}',413),('{"expected_version":0,"expected_version":0}',422),
        (json.dumps({**body,'measured_on':(c['today']+timedelta(days=1)).isoformat()}),422),
        (json.dumps({**body,'values':{'peso_kg':float('nan')}}),422)]
    for raw,status in bads:
        result=client.put(path,headers=headers,content=raw)
        assert result.status_code==status
        assert result.headers['Cache-Control']=='no-store' and result.headers['Referrer-Policy']=='no-referrer'
    assert client.get(path,headers=c['headers']['person']).status_code==404
    assert client.get('/api/usuario/progreso/completados?from='+c['today'].isoformat(),headers=headers).status_code==422
    assert client.get('/api/usuario/progreso/completados?from='+(c['today']-timedelta(days=62)).isoformat()+'&through='+c['today'].isoformat(),headers=headers).status_code==422


def test_export_eighth_keyset_and_consent_future_scope_are_explicit(progress_http):
    c=progress_http;client=c['client_http'];link=accepted(c)
    future=c['today']+timedelta(days=7)
    result,_=grant(c,link,from_date=future.isoformat(),through_date=(future+timedelta(days=365)).isoformat(),ongoing=False)
    assert result.status_code==200
    original=result.json()['consent']
    second,_=grant(c,link,expected_consent_id=original['id'],expected_version=1)
    assert second.status_code==200
    endpoint='/api/usuario/privacidad/exportar?limit=1'
    seen=[];cursor=None
    for _ in range(3):
        response=client.get(endpoint+('&after_progress_consent='+cursor if cursor else ''),headers=c['headers']['person'])
        assert response.status_code==200
        page=response.json()['progress_consents']
        seen.extend(item['id'] for item in page['records']);cursor=page['next_after']
        assert all(set(item)=={'link_id','id','version','event','protocol','link_version','source_profile_id','categories','from_date','through_date','ongoing','created_at'} for item in page['records'])
        if cursor is None:break
    assert set(seen)=={original['id'],second.json()['consent']['id']} and len(seen)==2
    assert client.get(endpoint+'&after_progress_consent='+original['id'].upper(),headers=c['headers']['person']).status_code==422
    other=client.get(endpoint,headers=c['headers']['other']);assert other.status_code==200 and other.json()['progress_consents']['records']==[]
