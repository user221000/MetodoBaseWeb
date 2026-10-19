"""Public onboarding binds server-created identity before tenant-owned writes.

Google's external identity response is synthetic; database and HTTP composition
are real. Run again after R04 activation to accept the RLS onboarding channel.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_schema_migrations import run_migration
from tests.google33_fixtures import owned_database
import importlib
import os
from tests.integration_provider_subjects import application_engine


@pytest.fixture
def migration_database(request,tmp_path):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):pytest.skip("Explicit own synthetic PostgreSQL required")
    assert request.param=="postgresql"
    with owned_database("postgresql",tmp_path) as value:yield value

@pytest.fixture(params=["web.main_web","api.app"])
def onboarding_application(migration_database, monkeypatch,request):
    from web.database import engine as module
    create_app=importlib.import_module(request.param).create_app
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    app_engine = application_engine(url, admin)
    monkeypatch.setattr(module, '_engine', app_engine)
    monkeypatch.setattr(module, '_SessionLocal', sessionmaker(bind=app_engine, expire_on_commit=False))
    monkeypatch.setattr('web.services.email_service.send_welcome', lambda *args, **kwargs: False)
    try:
        with TestClient(create_app()) as client:
            yield client, admin
    finally:
        app_engine.dispose()


def assert_own_onboarding(admin, email):
    from web.database.models import Usuario, GymProfile, PlanSuscripcion, UserRole
    with Session(admin) as db:
        user = db.query(Usuario).filter_by(email=email).one()
        assert user.id != 'untrusted-subject-from-body'
        assert user.role == UserRole.OWNER and user.team_gym_id is None
        assert db.query(GymProfile).filter_by(gym_id=user.id).count() == 1
        assert db.query(PlanSuscripcion).filter_by(gym_id=user.id).count() == 5
        assert db.query(GymProfile).filter_by(gym_id='untrusted-subject-from-body').count() == 0


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
def test_registration_initializes_only_server_created_subject(onboarding_application):
    client, admin = onboarding_application
    response = client.post('/api/auth/registro', json={'email': 'pg-register@example.test',
        'password': 'Synthetic-password-only-2026', 'nombre': 'Synthetic', 'tipo': 'gym',
        'id': 'untrusted-subject-from-body', 'gym_id': 'untrusted-subject-from-body'})
    assert response.status_code == 200, response.text
    assert_own_onboarding(admin, 'pg-register@example.test')


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
def test_google_initializes_only_verified_new_subject(onboarding_application, monkeypatch):
    client, admin = onboarding_application
    from datetime import datetime,timezone
    from web.settings import get_settings
    from tests.google33_signed_provider import SignedProvider
    monkeypatch.setattr(get_settings(),"GOOGLE_CLIENT_ID","synthetic-google-client")
    now=int(datetime.now(timezone.utc).timestamp())
    provider=SignedProvider(monkeypatch,{"aud":"synthetic-google-client","iss":"https://accounts.google.com",
        "sub":"onboarding33-google-subject","email_verified":True,"email":"pg-google@example.test",
        "given_name":"Synthetic","iat":now,"exp":now+3600,"auth_time":now})
    response = client.post('/api/auth/google', json={'credential': provider.credential(), 'tipo': 'gym',
        'id': 'untrusted-subject-from-body', 'gym_id': 'untrusted-subject-from-body'})
    assert response.status_code == 200, response.text
    assert_own_onboarding(admin, 'pg-google@example.test')
