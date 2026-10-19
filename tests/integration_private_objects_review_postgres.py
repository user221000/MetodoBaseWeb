"""Independent R07 composition: real PG/RLS, local bytes, core/PDF and quota."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine
from web.database.tenant_context import current_tenant, tenant_scope


@pytest.fixture
def private_pg(migration_database, monkeypatch, tmp_path):
    from web.database.models import Cliente, Subscription, Usuario, UserRole
    from web.database import engine as database
    from web.settings import get_settings
    from web.storage.runtime import get_object_store
    url,admin = migration_database
    run_migration(url,'db_bootstrap.py','--revision','head')
    with Session(admin) as db:
        for suffix in ('a','b'):
            owner='review-object-'+suffix
            db.add(Usuario(id=owner,email=owner+'@example.invalid',nombre='Synthetic',
                tipo='gym',role=UserRole.OWNER,password_hash='unused-synthetic'))
        db.flush()
        for suffix in ('a','b'):
            owner='review-object-'+suffix
            db.add(Cliente(gym_id=owner,id_cliente='review-client-'+suffix,nombre='Synthetic',edad=30,
                sexo='M',peso_kg=75,estatura_cm=175,nivel_actividad='moderada',objetivo='mantenimiento',activo=True))
            db.add(Subscription(gym_id=owner,plan='clinica',status='active',
                current_period_end=datetime.now(timezone.utc)+timedelta(days=1)))
        db.commit()
    app=application_engine(url,admin)
    assert app.pool.size() == 1
    settings=get_settings()
    monkeypatch.setattr(settings,'OBJECT_STORAGE_LOCAL_ROOT',str(tmp_path/'private-objects'))
    monkeypatch.setattr(database,'get_engine',lambda:app)
    store=get_object_store()
    try:
        yield admin,app,store
    finally:
        app.dispose()


def reserve(app,suffix='a'):
    from web.services.gym_generation_quota import reserve_gym_generation
    owner='review-object-'+suffix
    with tenant_scope(owner), Session(app) as db:
        row=reserve_gym_generation(db,owner,{'id_cliente':'review-client-'+suffix},'review-request-'+suffix)
        return row.id


def assert_blank(app):
    from web.database.models import StoredObject, PlanGenerado
    assert current_tenant.get() == ''
    with Session(app) as db:
        assert db.scalar(text("SELECT current_setting('app.current_tenant',TRUE)")) == ''
        assert db.scalars(select(StoredObject)).all() == []
        assert db.scalars(select(PlanGenerado)).all() == []


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
def test_real_worker_publishes_owned_objects_without_exposing_render_workspace(private_pg,monkeypatch):
    from web.database.models import StoredObject, PlanGenerado
    from web.services import plan_generation as worker
    from web.services.plan_documents import read_plan_pdf
    from web.services.gym_generation_quota import complete_gym_generation
    _,app,store=private_pg
    temporary=[]
    original=worker.tempfile.TemporaryDirectory
    def capture(*args,**kwargs):
        directory=original(*args,**kwargs)
        temporary.append(Path(directory.name))
        return directory
    monkeypatch.setattr(worker.tempfile,'TemporaryDirectory',capture)
    results={}
    for suffix in ('a','b'):
        owner='review-object-'+suffix
        reservation=reserve(app,suffix)
        result=worker.generate_plan('review-client-'+suffix,1,owner,reservation_id=reservation)
        assert result['success'] and 'ruta_pdf' not in result
        assert result['pdf_url']=='/api/planes/'+str(result['plan_id'])+'/pdf'
        assert all(str(path) not in repr(result) for path in temporary)
        with tenant_scope(owner),Session(app) as db:
            complete_gym_generation(db,owner,reservation,result)
            plan=db.get(PlanGenerado,result['plan_id'])
            metadata=db.get(StoredObject,plan.pdf_object_id)
            assert metadata.status=='ready' and metadata.storage_backend=='local'
            assert plan.ruta_pdf is None
            content=read_plan_pdf(db,owner,plan.id)
            assert content.startswith(b'%PDF-') and len(content)==metadata.byte_size
            results[suffix]=plan.id
        assert_blank(app)
    assert temporary and all(not path.exists() for path in temporary)
    with tenant_scope('review-object-a'),Session(app) as db:
        with pytest.raises(HTTPException) as foreign:
            read_plan_pdf(db,'review-object-a',results['b'])
        assert foreign.value.status_code==404
    assert_blank(app)


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
@pytest.mark.parametrize('bytes_uploaded',[False,True])
def test_pending_commit_precedes_put_and_uncertainty_never_publishes_reference(private_pg,monkeypatch,bytes_uploaded):
    from web.database.models import StoredObject,PlanGenerado
    from web.services import private_objects as objects
    from web.storage.objects import ObjectUnavailable
    _,app,store=private_pg
    original=store.put
    observed=[]
    def uncertain(descriptor,data,*,owner_id):
        with Session(app) as observer:
            row=observer.get(StoredObject,descriptor.id)
            assert row.status=='pending' and row.gym_id==owner_id
        observed.append(descriptor)
        if bytes_uploaded:
            original(descriptor,data,owner_id=owner_id)
        raise ObjectUnavailable('Synthetic uncertain PUT')
    monkeypatch.setattr(store,'put',uncertain)
    with pytest.raises(ObjectUnavailable):
        objects.publish_pending_object('review-object-a','plan_pdf',b'%PDF-review-pending','application/pdf')
    assert_blank(app)
    with tenant_scope('review-object-a'),Session(app) as db:
        assert db.scalars(select(PlanGenerado)).all()==[]
        assert db.get(StoredObject,observed[0].id).status=='pending'
        with pytest.raises(ObjectUnavailable):
            objects.read_private_object(db,'review-object-a',observed[0].id,'plan_pdf')
    assert_blank(app)
    if bytes_uploaded:
        assert store.read(observed[0],owner_id='review-object-a')==b'%PDF-review-pending'


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
def test_worker_failure_after_put_rolls_back_ready_plan_and_credit_marker(private_pg,monkeypatch):
    from web.database import repository
    from web.database.models import StoredObject,PlanGenerado,GymGenerationReservation
    from web.services.plan_generation import generate_plan
    from web.services.gym_generation_quota import compensate_generation_failure
    from web.services.private_objects import _descriptor
    _,app,store=private_pg
    reservation=reserve(app)
    original=repository.registrar_plan
    reached=[]
    def fail_after_real_flush(*args,**kwargs):
        plan_id=original(*args,**kwargs)
        assert plan_id
        reached.append(plan_id)
        raise RuntimeError('Synthetic failure before consumer commit')
    monkeypatch.setattr(repository,'registrar_plan',fail_after_real_flush)
    with pytest.raises(RuntimeError):
        generate_plan('review-client-a',1,'review-object-a',reservation_id=reservation)
    assert reached
    assert_blank(app)
    with tenant_scope('review-object-a'),Session(app) as db:
        metadata=db.scalars(select(StoredObject)).one()
        assert metadata.status=='pending'
        assert store.read(_descriptor(metadata),owner_id='review-object-a').startswith(b'%PDF-')
        assert db.scalars(select(PlanGenerado)).all()==[]
        ledger=db.get(GymGenerationReservation,reservation)
        assert ledger.plan_id is None and ledger.persisted_at is None and ledger.status=='reserved'
        compensate_generation_failure(db,'review-object-a',reservation)
        compensate_generation_failure(db,'review-object-a',reservation)
        assert db.get(GymGenerationReservation,reservation).status=='released'
    assert_blank(app)


@pytest.mark.parametrize('migration_database',['postgresql'],indirect=True)
def test_committed_plan_object_and_marker_survive_later_compensation(private_pg):
    from web.database.models import StoredObject,PlanGenerado,GymGenerationReservation
    from web.services.plan_generation import generate_plan
    from web.services.plan_documents import read_plan_pdf
    from web.services.gym_generation_quota import compensate_generation_failure,complete_gym_generation
    _,app,_=private_pg
    reservation=reserve(app)
    result=generate_plan('review-client-a',1,'review-object-a',reservation_id=reservation)
    assert_blank(app)
    with tenant_scope('review-object-a'),Session(app) as db:
        compensate_generation_failure(db,'review-object-a',reservation)
        row=db.get(GymGenerationReservation,reservation)
        assert row.status=='reserved' and row.persisted_at is not None and row.plan_id==result['plan_id']
        assert db.scalars(select(StoredObject)).one().status=='ready'
        assert read_plan_pdf(db,'review-object-a',result['plan_id']).startswith(b'%PDF-')
        assert complete_gym_generation(db,'review-object-a',reservation,result)==result
        assert complete_gym_generation(db,'review-object-a',reservation,result)==result
        assert len(db.scalars(select(PlanGenerado)).all())==1
    assert_blank(app)
