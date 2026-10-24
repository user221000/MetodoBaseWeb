"""Real personal fact pages preserve keysets and never expose other owners."""
import uuid
from sqlalchemy.orm import Session
from tests.privacy39_fixtures import (privacy39_engine,account37_engine,account37,database_schema,isolated_database)
from web.database.models import Usuario,UserRole
from web.services.product_analytics_v2 import origin
from web.services.privacy_facts_export import export_personal_facts,FIELDS


def test_personal_origin_fact_export_is_self_only_bounded_and_keyset_complete(account37):
    case=account37;foreign=str(uuid.uuid4())
    with case['factory']() as db:
        db.add(Usuario(id=foreign,email=foreign+'@example.invalid',password_hash='not-a-login',nombre='Synthetic foreign',tipo='usuario',role=UserRole.VIEWER));db.commit()
    for subject,labels in ((case['user'],('demo','customer')),(foreign,('customer',))):
        expected={'id':subject,'tipo':'usuario','role':'viewer','session_version':0,'team_gym_id':None}
        for version,label in enumerate(labels):
            with case['factory']() as db:origin(db,expected,'personal',None,value=label,expected_version=version)
    with case['factory']() as db:
        first=export_personal_facts(db,case['user'],limit=1)
        assert len(first['records'])==1 and first['next_after']==first['records'][0]['id']
        second=export_personal_facts(db,case['user'],limit=1,after=first['next_after'])
        assert len(second['records'])==1 and second['next_after'] is None
        values=first['records']+second['records']
        assert len({row['id'] for row in values})==2
        assert all(set(row)==set(FIELDS) and row['source_id']==case['user'] for row in values)
        assert {row['origin'] for row in values}=={'demo','customer'}
        assert foreign not in str(values)
        assert first['max_response_bytes']==131072 and 'professional_portfolio' in first['excluded_categories']
