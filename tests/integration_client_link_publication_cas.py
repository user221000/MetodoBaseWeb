"""A publication replacement must compare the exact row that was observed.

The pre-fix service probe supplied the proposed identity in a namespace after
validating all existing fields. This keeps the two database assertions equal
before/after without pretending that the old HTTP schema accepted the new key.
"""
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from tests import integration_client_link_services as shared
from web.client_link_schemas import PlanPublication
from web.services import client_link_plans as plans

link_db=shared.link_db
case=shared.case


def publication_input(plan,link,identity,version):
    values={'plan_id':plan,'expected_link_version':link['version'],
        'expected_publication_version':version}
    if 'expected_publication_id' in PlanPublication.model_fields:
        return PlanPublication(**values,expected_publication_id=identity)
    return SimpleNamespace(**PlanPublication(**values).model_dump(),expected_publication_id=identity)


def publish(case,link,plan,identity=None,version=0):
    with shared.session(case,'gym') as db:
        return plans.publish_plan(db,shared.principal(case['gym']),case['client'],link['link_id'],
            publication_input(plan,link,identity,version))


def test_stale_publication_identity_cannot_replace_a_new_row_with_the_same_version(case):
    invitation,proof=shared.issue(case)
    link=shared.accept(case,invitation,proof)
    source,_,_=shared.source(case,marker='observed')
    observed=publish(case,link,source)
    first,_,_=shared.source(case,marker='first-replacement')
    current=publish(case,link,first,observed['publication_id'],observed['version'])
    assert current['publication_id']!=observed['publication_id']
    assert current['version']==observed['version']==1
    stale,_,_=shared.source(case,marker='stale-replacement')
    with pytest.raises(HTTPException) as conflict:
        publish(case,link,stale,observed['publication_id'],observed['version'])
    assert conflict.value.status_code==409
    assert conflict.value.detail['code']=='member_version_conflict'
    with shared.session(case,'person') as db:
        result=plans.read_member_plan(db,shared.principal(case['person']),link['link_id'])
    assert result['publication']['id']==current['publication_id']
    assert result['publication']['source_plan_id']==first
