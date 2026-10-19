"""R23 shared HTTP on an owned UUID database, migrated current head, restricted FORCE RLS."""
from datetime import datetime, timedelta, timezone
import importlib

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine

pytestmark=pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)


@pytest.mark.parametrize('factory',['web.main_web','api.app'])
def test_readonly_followup_double_owner_admin_scope_and_revocation(migration_database, monkeypatch, factory):
    from web.auth import crear_access_token, identity_from_user
    from web.database import engine as database
    from web.database.models import Cliente, PlanGenerado, Usuario, UserRole
    from web.database.tenant_context import tenant_scope
    url,admin=migration_database
    run_migration(url,'db_bootstrap.py','--revision','head')
    with Session(admin) as db:
        for identity,role,team in [('follow-owner',UserRole.OWNER,None),('follow-foreign',UserRole.OWNER,None),
                ('follow-admin',UserRole.ADMIN,'follow-owner')]:
            db.add(Usuario(id=identity,email=identity+'@example.invalid',nombre='Synthetic',password_hash='unused',
                tipo='gym',role=role,team_gym_id=team,activo=True));db.flush()
        for identity,owner in [('own-never','follow-owner'),('own-dated','follow-owner'),('foreign','follow-foreign')]:
            db.add(Cliente(id_cliente=identity,gym_id=owner,nombre='Synthetic '+identity));db.flush()
        db.add_all([PlanGenerado(id_cliente='own-dated',gym_id='follow-owner',fecha_generacion=datetime.now(timezone.utc)-timedelta(days=40)),
            PlanGenerado(id_cliente='own-never',gym_id='follow-foreign'),
            PlanGenerado(id_cliente='foreign',gym_id='follow-owner')]);db.commit()
    app_engine=application_engine(url,admin)
    try:
        monkeypatch.setattr(database,'_engine',app_engine)
        monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=app_engine,autoflush=False))
        application=importlib.import_module(factory).create_app()
        with Session(app_engine) as db:
            headers={name:{'Authorization':'Bearer '+crear_access_token(identity_from_user(db.get(Usuario,name),db))}
                for name in ['follow-owner','follow-admin','follow-foreign']}
        statements=[]
        def observe(conn,cursor,statement,parameters,context,many):statements.append(statement)
        with TestClient(application,raise_server_exceptions=False) as client:
            event.listen(app_engine,'before_cursor_execute',observe)
            try:
                for name in ['follow-owner','follow-admin']:
                    response=client.get('/api/estadisticas/seguimiento',headers=headers[name]);assert response.status_code==200,response.text
                    body=response.json()
                    assert [row['id_cliente'] for row in body['items']]==['own-never','own-dated']
                    assert body['items'][0]['causes']==['no_saved_plan']
                    assert body['metrics']['plans_saved']==0
                    assert response.headers['Referrer-Policy']=='no-referrer'
                assert client.get('/api/estadisticas/seguimiento',headers=headers['follow-foreign']).json()['items'][0]['id_cliente']=='foreign'
            finally:event.remove(app_engine,'before_cursor_execute',observe)
            assert not [s for s in statements if s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','ALTER'))]
            with Session(admin) as db:
                member=db.get(Usuario,'follow-admin');member.team_gym_id=None;member.role=UserRole.VIEWER;member.session_version+=1;db.commit()
            assert client.get('/api/estadisticas/seguimiento',headers=headers['follow-admin']).status_code==401
        # Empty public transaction and a different tenant on the same small pool
        # cannot reuse an earlier gym's result or ambient GUC.
        with Session(app_engine) as db:
            assert db.query(Cliente).count()==0
        with tenant_scope('follow-foreign'),Session(app_engine) as db:
            assert [row.id_cliente for row in db.query(Cliente).all()]==['foreign']
    finally:app_engine.dispose()
