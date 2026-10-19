"""SQLite metadata constraints, distinct from PostgreSQL proof/RLS acceptance."""
from datetime import datetime,timezone
import hashlib
import uuid

import pytest
from sqlalchemy import create_engine,event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def model_case(tmp_path):
    from web.database.models import Base,Usuario,UserRole,Cliente,PlanGenerado,StoredObject,ClientAccountLink
    engine=create_engine('sqlite:///'+(tmp_path/'models.db').as_posix())
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Usuario(id='model-gym',email='model-gym@example.invalid',nombre='Synthetic',password_hash='synthetic',tipo='gym',role=UserRole.OWNER),
            Usuario(id='model-person',email='model-person@example.invalid',nombre='Synthetic',password_hash='synthetic',tipo='usuario',role=UserRole.VIEWER)])
        db.flush();db.add(Cliente(id_cliente='model-client',gym_id='model-gym',nombre='Synthetic',activo=True));db.flush()
        db.add(StoredObject(id='a'*32,gym_id='model-gym',kind='plan_pdf',key='opaque/synthetic',content_type='application/pdf',byte_size=10,sha256='b'*64,storage_backend='local',status='ready'));db.flush()
        plan=PlanGenerado(gym_id='model-gym',id_cliente='model-client',pdf_object_id='a'*32,plan_json='{}')
        link=ClientAccountLink(gym_id='model-gym',client_id='model-client',gym_name='Synthetic gym',client_display_name='Synthetic client')
        db.add_all([plan,link]);db.commit()
        result={'plan_id':plan.id,'link_id':link.id}
    yield engine,result
    engine.dispose()


def publication_values(case):
    _,ids=case
    return dict(id=str(uuid.uuid4()),gym_id='model-gym',client_id='model-client',link_id=ids['link_id'],source_plan_id=ids['plan_id'],
        published_by='model-gym',plan_json='{}',plan_sha256=hashlib.sha256(b'{}').hexdigest(),source_object_id='a'*32,
        object_key='opaque/synthetic',content_type='application/pdf',byte_size=10,sha256='b'*64,storage_backend='local')


@pytest.mark.parametrize('field',['source_object_id','object_key','content_type','byte_size','sha256','storage_backend'])
def test_present_pdf_reference_requires_every_descriptor_field_not_sql_unknown(model_case,field):
    from web.database.models import ClientPlanPublication
    values=publication_values(model_case);values[field]=None
    with Session(model_case[0]) as db:
        db.add(ClientPlanPublication(**values))
        with pytest.raises(IntegrityError,match='ck_client_publication_pdf'):db.commit()


def test_complete_descriptor_passes_structural_checks(model_case):
    from web.database.models import ClientPlanPublication
    with Session(model_case[0]) as db:
        row=ClientPlanPublication(**publication_values(model_case));db.add(row);db.commit()
        assert row.source_object_id=='a'*32


def test_partial_consumption_cannot_commit_through_deferred_fk(model_case):
    from web.database.models import ClientLinkInvitation
    engine,ids=model_case
    now=datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(ClientLinkInvitation(gym_id='model-gym',client_id='model-client',link_id=ids['link_id'],recipient_email='model-person@example.invalid',
            token_hash='c'*64,expires_at=now.replace(year=now.year+1),status='consumed',issued_by='model-gym',consumed_by='model-person',
            consumed_at=now,request_key='synthetic-key',payload_hash='d'*64))
        db.flush()
        with pytest.raises(IntegrityError):db.commit()
