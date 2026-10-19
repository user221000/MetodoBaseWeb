"""Exact immutable R24 privacy repro; actual source state, both factories."""
import os,json
from pathlib import Path
import pytest
from tests.integration_client_link_services import link_db,case,source
from tests.integration_client_link_http import http
from tests.test_publication_diary_consumption import prepare_publication

@pytest.mark.parametrize('link_db',['sqlite'],indirect=True)
@pytest.mark.parametrize('variant',['revoked-source','old-publication-identity'])
def test_diary_rejection_keeps_private_response_headers(http,variant):
    day,body=prepare_publication(http);client=http['client_http'];headers=http['headers']['person']
    if variant=='revoked-source':
        result=client.request('DELETE','/api/usuario/vinculos/'+body['link_id'],headers=headers,json={'expected_version':2});assert result.status_code==200
    else:
        endpoint='/api/clientes/'+http['client']+'/vinculacion/'+body['link_id']+'/publicaciones'
        result=client.request('DELETE',endpoint+'/'+body['publication_id'],headers=http['headers']['gym'],json={'expected_version':1});assert result.status_code==200
        plan,_,_=source(http,pdf=False,marker='huevo')
        result=client.post(endpoint,headers=http['headers']['gym'],json={'plan_id':plan,'expected_link_version':2,'expected_publication_version':0,'expected_publication_id':None});assert result.status_code==200
        current=client.get('/api/usuario/vinculos/'+body['link_id']+'/plan',headers=headers).json()['publication']
        assert current['id']!=body['publication_id']and current['version']==body['expected_publication_version']==1
    denied=client.patch(day,headers=headers,json=body)
    current_day=client.get(day,headers=headers).json();assert current_day['version']==0 and current_day['meals']=={}
    proof={'variant':variant,'factory':http['factory'],'actual_HTTP':True,'status':denied.status_code,'body_code':denied.json()['detail']['code'],'cache_control':denied.headers.get('cache-control'),'referrer_policy':denied.headers.get('referrer-policy'),'personal_version':current_day['version'],'meals_empty':not current_day['meals'],'expected_status':404,'expected_referrer':'no-referrer','secrets_or_private_source_body_recorded':False}
    output=Path(os.environ['R24_FAILURE_OUTPUT']);output.mkdir(exist_ok=True);(output/(http['factory']+'-'+variant+'.json')).write_text(json.dumps(proof,indent=2)+'\n')
    assert denied.status_code==404
    assert 'no-store'in {p.strip()for p in denied.headers['cache-control'].split(',')}
    assert denied.headers['referrer-policy']=='no-referrer'
