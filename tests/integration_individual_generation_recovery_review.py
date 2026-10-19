"""Real individual worker commit followed by an injected delivery/finalize failure.

Uses only UUID migration databases, the restricted role, real auth/middleware,
core/PDF, private storage and quota transactions. No product or schema edits.
"""
import hashlib
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine

pytestmark = pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
SUBJECT = 'individual-recovery-review'


def state(engine):
    from web.database.models import GenerationReservation, PlanGenerado, StoredObject, UserSubscription
    with Session(engine) as db:
        sub = db.query(UserSubscription).filter_by(user_id=SUBJECT).one()
        return {
            'used_credits': sub.planes_usados_mes, 'maximum_credits': sub.max_planes_mes,
            'period': sub.mes_actual,
            'plans': [{'id': row.id, 'object_id': row.pdf_object_id}
                for row in db.query(PlanGenerado).filter_by(gym_id=SUBJECT).order_by(PlanGenerado.id)],
            'objects': [{'id': row.id, 'status': row.status, 'size': row.byte_size, 'sha256': row.sha256}
                for row in db.query(StoredObject).filter_by(gym_id=SUBJECT).order_by(StoredObject.id)],
            'reservations': [{'id': row.id, 'status': row.status, 'plan_id': row.plan_id}
                for row in db.query(GenerationReservation).filter_by(user_id=SUBJECT).order_by(GenerationReservation.id)],
        }


def evidence(tmp_path, name, report):
    output = Path(os.environ.get('METODOBASE_TEST_EVIDENCE_DIR', str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    (output / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


@pytest.fixture
def individual_pg(migration_database, monkeypatch, tmp_path):
    from web.auth import crear_access_token
    from web.database import engine as database
    from web.database.models import Cliente, Usuario, UserRole, UserSubscription
    from web.database.tenant_context import configure_tenant_engine
    from web.database.tenant_policy import verify_application_database_role
    from web.services.billing_integrity import current_quota_period
    from web.settings import get_settings

    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    with Session(admin) as db:
        db.add(Usuario(id=SUBJECT, email='individual-recovery@example.invalid', nombre='Synthetic',
            tipo='usuario', role=UserRole.VIEWER, password_hash='synthetic', activo=True, session_version=0))
        db.flush()
        db.add(Cliente(id_cliente='individual-recovery-client', gym_id=SUBJECT, nombre='Synthetic',
            edad=30, sexo='M', peso_kg=75, estatura_cm=175,
            nivel_actividad='moderada', objetivo='mantenimiento', activo=True))
        db.add(UserSubscription(user_id=SUBJECT, plan='starter', status='active',
            max_planes_mes=1, planes_usados_mes=0, mes_actual=current_quota_period()))
        db.commit()
    granted = application_engine(url, admin)
    target_url = granted.url
    granted.dispose()
    # The HTTP route retains a read transaction while its real worker opens
    # another connection. Pool3 avoids introducing an artificial pool1 timeout.
    app_engine = configure_tenant_engine(create_engine(target_url, pool_size=3, max_overflow=0))
    verify_application_database_role(app_engine)
    # Auth opens SessionLocal, whereas request/worker code asks get_engine.
    # Configure both real database adapters to this same restricted UUID DB.
    monkeypatch.setattr(database, '_engine', app_engine)
    monkeypatch.setattr(database, '_SessionLocal', sessionmaker(bind=app_engine, autocommit=False, autoflush=False))
    monkeypatch.setattr(get_settings(), 'OBJECT_STORAGE_LOCAL_ROOT', str(tmp_path / 'private-objects'))
    from web.main_web import create_app
    try:
        application = create_app()
        token = crear_access_token(dict(id=SUBJECT, email='individual-recovery@example.invalid',
            nombre='Synthetic', tipo='usuario', role='viewer'))
        with TestClient(application, raise_server_exceptions=False) as client:
            authenticated = client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token})
            assert authenticated.status_code == 200, authenticated.text
            yield admin, app_engine, client, {'Authorization': 'Bearer ' + token}
    finally:
        app_engine.dispose()


@pytest.mark.parametrize('failure_type', [RuntimeError, ValueError])
def test_committed_individual_plan_must_not_refund_on_worker_delivery_failure(
        individual_pg, monkeypatch, tmp_path, failure_type):
    from web.routes import planes
    from web.services.plan_documents import read_plan_pdf

    admin, app_engine, client, headers = individual_pg
    report = {'scope': 'Real PostgreSQL restricted-role HTTP/core/PDF; injected only after actual worker returns committed result',
        'failure_type': failure_type.__name__, 'before': state(admin)}
    real_worker = planes._generar_plan_sync

    def committed_then_raise(*args, **kwargs):
        result = real_worker(*args, **kwargs)
        # Separate privileged observation proves the worker transaction is
        # committed before the error; actual bytes are read under app RLS.
        report['after_worker_commit'] = state(admin)
        with Session(app_engine) as db:
            content = read_plan_pdf(db, SUBJECT, result['plan_id'])
        assert content.startswith(b'%PDF-')
        report['real_pdf_sha256'] = hashlib.sha256(content).hexdigest()
        raise failure_type('Synthetic failure after real worker commit')

    monkeypatch.setattr(planes, '_generar_plan_sync', committed_then_raise)
    response = client.post('/api/usuario/generar-plan', headers={**headers,
        'Idempotency-Key': 'synthetic-individual-after-commit'})
    report['http_status'] = response.status_code
    report['after_http_failure'] = state(admin)
    evidence(tmp_path, 'individual-after-commit-' + failure_type.__name__.lower(), report)
    assert response.status_code in {400, 409, 500, 503}
    assert report['before']['used_credits'] == 0 and report['before']['plans'] == []
    assert report['after_worker_commit']['used_credits'] == 1
    after = report['after_http_failure']
    assert len(after['plans']) == 1 and len(after['objects']) == 1
    assert after['objects'][0]['status'] == 'ready'
    assert after['used_credits'] == 1, 'A physically committed plan must retain its consumed credit'
    assert after['reservations'][0]['status'] != 'released'


def test_failure_in_finish_after_return_retains_the_committed_plan_credit(individual_pg, monkeypatch, tmp_path):
    from web.services import generation_quota

    admin, _, client, headers = individual_pg
    report = {'scope': 'Control: failure in completion after real worker return, outside its exception/refund branch',
        'before': state(admin)}
    def failed_completion(db, reservation_id, user_id, plan_id, *, success):
        assert success is True and plan_id is not None
        report['before_completion_failure'] = state(admin)
        raise RuntimeError('Synthetic completion-record failure')
    monkeypatch.setattr(generation_quota, 'finish_generation', failed_completion)
    response = client.post('/api/usuario/generar-plan', headers={**headers,
        'Idempotency-Key': 'synthetic-individual-completion-failure'})
    report['http_status'] = response.status_code
    report['after_http_failure'] = state(admin)
    evidence(tmp_path, 'individual-completion-control', report)
    # Protocol 1 now commits completed with the actual worker result; a failed
    # verification reports reconciliation instead of reopening compensation.
    assert response.status_code == 503
    after = report['after_http_failure']
    assert len(after['plans']) == 1 and after['used_credits'] == 1
    assert after['reservations'][0]['status'] == 'completed'
