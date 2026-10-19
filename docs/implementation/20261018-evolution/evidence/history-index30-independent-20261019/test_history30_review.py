"""Eight independent index30 preservation/drift and mixed-history criteria."""
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import event,text
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database as original_database,run_migration,ROOT
from tests.integration_client_link_migrations import populate28
from tests.integration_stored_objects_migrations import snapshot
from tests.integration_provider_subjects import application_engine
from web.database.alembic.history_index_contract_v1 import history_index_signature
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.tenant_policy import tenant_security_signature
from web.database.schema_control import verify_runtime_schema
from web.database.tenant_context import tenant_scope
from web.services.personal_history_query import history_summary_rows

PREVIOUS='20261019_client_account_links'
CURRENT='20261019_personal_history_index'
INDEX='ix_planes_gym_cliente_history'

@pytest.fixture(params=['sqlite','postgresql'])
def owned_database(request,tmp_path):
    owner=original_database.__wrapped__(request,tmp_path)
    try:yield next(owner)
    finally:owner.close()

@pytest.fixture
def owned_pg_database(tmp_path):
    owner=original_database.__wrapped__(SimpleNamespace(param='postgresql'),tmp_path)
    try:yield next(owner)
    finally:owner.close()

def security(engine):
    with engine.connect() as db:
        return tenant_security_signature(db),member_link_security_signature(db)

def seed_member_records(engine):
    """Populate all three29 tables with real source-bound content, not empty placeholders."""
    from web.database.models import Usuario,UserRole,Cliente,PlanGenerado,ClientAccountLink,ClientLinkInvitation,ClientPlanPublication
    gym=str(uuid.uuid4());client=str(uuid.uuid4());now=datetime.now(timezone.utc)
    menu={meal:{'kcal_objetivo':200,'kcal_real':199.5,'alimentos':{'Synthetic food':48.25}}
          for meal in ['desayuno','almuerzo','comida','cena']}
    meta=dict(tmb=1500.5,get_total=2150.5,kcal_objetivo=2100.5,kcal_real=2099.5,proteina_g=100.5,
              carbs_g=240.5,grasa_g=60.5,objetivo='synthetic',nivel_actividad='synthetic',tipo_plan='menu_fijo')
    with Session(engine) as db:
        db.add(Usuario(id=gym,email=gym+'@example.invalid',password_hash='synthetic-unused',nombre='Synthetic',
                       tipo='gym',role=UserRole.OWNER,activo=True));db.flush()
        db.add(Cliente(id_cliente=client,gym_id=gym,nombre='Synthetic',activo=True));db.flush()
        plan=PlanGenerado(gym_id=gym,id_cliente=client,plan_json=json.dumps(menu),**meta);db.add(plan);db.flush()
        if engine.dialect.name=='postgresql':
            db.execute(text("SELECT set_config('app.current_tenant',:gym,true)"),{'gym':gym})
        link=ClientAccountLink(gym_id=gym,client_id=client,status='pending',gym_name='Synthetic',client_display_name='Synthetic')
        db.add(link);db.flush()
        token_hash=hashlib.sha256(b'client-account-invite-v1:synthetic-owned-review').hexdigest()
        db.add(ClientLinkInvitation(gym_id=gym,client_id=client,link_id=link.id,recipient_email='synthetic@example.invalid',
             token_hash=token_hash,expires_at=now+timedelta(days=1),status='pending',issued_by=gym,
             request_key=str(uuid.uuid4()),payload_hash='a'*64));db.flush()
        payload=json.dumps({'plan':menu,'meta':meta})
        db.add(ClientPlanPublication(gym_id=gym,client_id=client,link_id=link.id,source_plan_id=plan.id,
             status='published',published_by=gym,plan_json=payload,plan_sha256=hashlib.sha256(payload.encode()).hexdigest()))
        db.commit()
    with engine.connect() as db:
        assert [db.scalar(text('SELECT count(*) FROM '+table)) for table in
                ['client_account_links','client_link_invitations','client_plan_publications']]==[1,1,1]

def test_rollback_preserves_actual_R12_rows_and_all_23_security_families(owned_database):
    url,engine=owned_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS);populate28(engine);seed_member_records(engine)
    columns,rows=snapshot(engine);guards=security(engine)
    run_migration(url,'db_bootstrap.py','--revision',CURRENT)
    verify_runtime_schema(engine,expected_revision=CURRENT)
    assert snapshot(engine,columns)[1]==rows and security(engine)==guards
    run_migration(url,'-m','alembic','downgrade',PREVIOUS)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    assert snapshot(engine,columns)[1]==rows and security(engine)==guards
    with engine.connect() as db:
        assert history_index_signature(db) is None
        if engine.dialect.name=='postgresql':
            assert len([row for row in tenant_security_signature(db)['tables'] if row[1] and row[2]])==23
    run_migration(url,'db_bootstrap.py','--revision',CURRENT)
    verify_runtime_schema(engine,expected_revision=CURRENT)
    assert snapshot(engine,columns)[1]==rows and security(engine)==guards

@pytest.mark.parametrize('change',['operator_class','predicate','timestamp_nulls','included_column'])
def test_startup_and_downgrade_reject_physical_drift_without_deleting_any_index_or_rows(owned_pg_database,change):
    url,engine=owned_pg_database
    run_migration(url,'db_bootstrap.py','--revision',CURRENT);seed_member_records(engine)
    columns,rows=snapshot(engine);guards=security(engine)
    with engine.begin() as db:
        structural=schema_signature(db)
        db.exec_driver_sql('DROP INDEX '+INDEX)
        owner='gym_id text_pattern_ops' if change=='operator_class' else 'gym_id'
        order='fecha_generacion DESC NULLS FIRST' if change=='timestamp_nulls' else 'fecha_generacion DESC NULLS LAST'
        include=' INCLUDE (kcal_real)' if change=='included_column' else ''
        predicate='deleted_at IS NULL OR kcal_real=999' if change=='predicate' else 'deleted_at IS NULL'
        db.exec_driver_sql('CREATE INDEX '+INDEX+' ON planes_generados ('+owner+',id_cliente,'+order+',id DESC NULLS LAST)'+include+' WHERE '+predicate)
        altered=history_index_signature(db)
        if change in ['operator_class','timestamp_nulls']:
            assert schema_signature(db)==structural
    with pytest.raises(RuntimeError,match='ordering|structure'):
        verify_runtime_schema(engine,expected_revision=CURRENT)
    import subprocess,sys
    result=subprocess.run([sys.executable,'-X','utf8','-m','alembic','downgrade',PREVIOUS],cwd=ROOT,
             env=dict(os.environ,DATABASE_URL=url,METODOBASE_TEST_DATABASE_URL=''),capture_output=True)
    assert result.returncode!=0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==CURRENT
        assert history_index_signature(db)==altered
    assert snapshot(engine,columns)[1]==rows and security(engine)==guards

def test_live_cursor_boundaries_exclude_deleted_clients_and_both_cross_owner_directions(owned_database):
    from web.database.models import Usuario,UserRole,Cliente,PlanGenerado
    url,admin=owned_database
    run_migration(url,'db_bootstrap.py','--revision',CURRENT)
    subject,other='qa-index30-person','qa-index30-other'
    profile,extra,foreign,deleted='qa-index30-self','qa-index30-extra','qa-index30-foreign','qa-index30-deleted'
    valid=[];stamp=datetime(2026,10,1,12,30)
    with Session(admin) as db:
        for actor in [subject,other]:
            db.add(Usuario(id=actor,email=actor+'@example.invalid',password_hash='synthetic-unused',nombre='Synthetic',
                           tipo='usuario',role=UserRole.VIEWER,activo=True))
        db.flush()
        for identity,gym,removed in [(profile,subject,None),(extra,subject,None),(foreign,other,None),(deleted,subject,stamp)]:
            db.add(Cliente(id_cliente=identity,gym_id=gym,nombre='Synthetic',activo=False,deleted_at=removed))
        db.flush()
        for number in range(41):
            at=stamp-timedelta(minutes=number//3)
            row=PlanGenerado(gym_id=subject,id_cliente=profile,fecha_generacion=at,kcal_objetivo=1000+number,plan_json='{"private":"synthetic"}')
            db.add(row);db.flush()
            if number>=30:
                row.fecha_generacion=None;db.flush();at=None
            valid.append((row.id,at,1000+number))
        for gym,client in [(subject,extra),(subject,foreign),(other,profile),(other,foreign),(subject,deleted)]:
            db.add(PlanGenerado(gym_id=gym,id_cliente=client,fecha_generacion=stamp,kcal_objetivo=99999,plan_json='{"foreign":true}'))
        db.add(PlanGenerado(gym_id=subject,id_cliente=profile,fecha_generacion=stamp,deleted_at=stamp,kcal_objetivo=99999))
        db.commit()
    def key(value):
        identity,at,_=value
        micros=0 if at is None else ((at.toordinal()*86400+at.hour*3600+at.minute*60+at.second)*1000000+at.microsecond)
        return at is None,-micros,-identity
    oracle=sorted(valid,key=key)
    app=application_engine(url,admin);statements=[]
    def capture(connection,cursor,statement,parameters,context,many):
        if 'planes_generados' in statement:statements.append(statement)
    event.listen(app,'before_cursor_execute',capture)
    try:
        with tenant_scope(subject),Session(app) as db:
            if app.dialect.name=='postgresql':
                assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one())==(False,False,False,False)
                assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND pg_has_role(current_user,relowner,'MEMBER'))"))
            position=None;seen=[]
            for _ in range(20):
                before=len(statements);candidates=history_summary_rows(db,subject,profile,6,position)
                assert len(statements)==before+1 and len(candidates)<=7
                page=candidates[:6];seen.extend((row.id,row.fecha_generacion,row.kcal_objetivo) for row in page)
                if len(candidates)<=6:break
                position=(page[-1].fecha_generacion,page[-1].id)
            assert seen==oracle and len({row[0] for row in seen})==41
            last=oracle[-1]
            assert last[1] is None and history_summary_rows(db,subject,profile,6,(None,last[0]))==[]
            # Explicitly exercise date->NULL union at the exact last dated anchor.
            anchor=oracle[29]
            assert anchor[1] is not None
            assert [(r.id,r.fecha_generacion,r.kcal_objetivo) for r in history_summary_rows(db,subject,profile,6,(anchor[1],anchor[0]))]==oracle[30:37]
            assert history_summary_rows(db,subject,deleted,6,None)==[]
            assert history_summary_rows(db,subject,foreign,6,None)==[]
            assert all('plan_json' not in statement.lower() and 'count(' not in statement.lower() and statement.lstrip().upper().startswith('SELECT') for statement in statements)
            db.rollback()
    finally:
        event.remove(app,'before_cursor_execute',capture)
        if app is not admin:app.dispose()
