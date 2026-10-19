"""Canonical HTTP gym onboarding collision, two real restricted pool1 workers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextvars import ContextVar
import importlib
import json
import os
from pathlib import Path
from threading import Barrier, get_ident
from time import monotonic
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_google33_postgres import google_db
from tests.test_google33_http import google_http


def test_canonical_http_new_gym_subject_collision_is_a_conflict(google_http, monkeypatch):
    from web.database import engine as database
    from web.database.tenant_context import configure_tenant_engine
    from web.database.models import Usuario, AuthExternalIdentity, GymProfile, PlanSuscripcion
    c = google_http
    subject = str(uuid.uuid4().int)
    claims = {**c['google'], 'sub': subject, 'iat': c['google']['auth_time']}
    credentials = [c['credential'](claims={**claims, 'email': uuid.uuid4().hex + '@thirdparty.example.invalid'}) for _ in range(2)]
    engines = [configure_tenant_engine(create_engine(c['engine'].url, pool_size=1, max_overflow=0, pool_timeout=5)) for _ in range(2)]
    factories = [sessionmaker(bind=e, autoflush=False, expire_on_commit=False) for e in engines]
    worker = ContextVar('independent_google33_worker', default=0)
    barrier = Barrier(2)
    arrivals = []
    for engine in engines:
        with engine.connect() as db:
            assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()) == (False, False, False, False)
        @event.listens_for(engine, 'before_cursor_execute')
        def actual_unique_insert(conn, cursor, statement, parameters, context, many):
            if statement.startswith('INSERT INTO auth_external_identities'):
                arrivals.append({'thread': get_ident(), 'backend_pid': conn.connection.driver_connection.get_backend_pid(), 'time': monotonic()})
                barrier.wait(timeout=10)
    with Session(c['admin']) as db: before = set(db.scalars(select(Usuario.id)))
    results = None
    try:
        with monkeypatch.context() as patch:
            # Infrastructure dispatcher only: one ordinary production-configured
            # Session factory per ASGI worker, no auth/identity/provider override.
            patch.setattr(database, '_SessionLocal', lambda: factories[worker.get()]())
            with ExitStack() as clients:
                http = []
                for index in range(2):
                    application = importlib.import_module(c['factory']).create_app()
                    async def app(scope, receive, send, _index=index, _app=application):
                        token = worker.set(_index)
                        try: await _app(scope, receive, send)
                        finally: worker.reset(token)
                    http.append(clients.enter_context(TestClient(app, raise_server_exceptions=False,
                        client=('192.77.33.' + str(index + 1), 52000 + index))))
                def register(index):
                    return http[index].post('/api/auth/google', json={'credential': credentials[index],
                        'tipo': 'gym', 'id': 'untrusted-caller-id', 'gym_id': 'untrusted-caller-id'})
                with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(register, range(2)))
        with Session(c['admin']) as db:
            added = set(db.scalars(select(Usuario.id))) - before
            bindings = db.scalars(select(AuthExternalIdentity).where(AuthExternalIdentity.subject == subject)).all()
            owner = bindings[0].user_id if len(bindings) == 1 else None
            profiles = db.scalars(select(GymProfile.gym_id).where(GymProfile.gym_id.in_(added))).all()
            defaults = list(db.scalars(select(PlanSuscripcion.gym_id).where(PlanSuscripcion.gym_id.in_(added))))
        observation = {'factory': c['factory'], 'statuses': sorted(r.status_code for r in results),
            'provider_signature_and_JWKS_real_library': True, 'workers': 2, 'pool_size_each': 1,
            'autoflush_each': False, 'source_dispatcher_only_no_identity_override': True,
            'arrivals': arrivals, 'unique_insert_workers': len({a['thread'] for a in arrivals}),
            'unique_insert_backends': len({a['backend_pid'] for a in arrivals}),
            'one_new_container': len(added) == 1, 'one_binding': len(bindings) == 1,
            'binding_owner_is_new_container': owner in added, 'one_server_owned_profile': profiles == [owner],
            'exactly_five_own_defaults': len(defaults) == 5 and set(defaults) == {owner},
            'losing_response_has_no_tokens': all(not {'token', 'refresh_token', 'challenge'} & r.json().keys() for r in results if r.status_code != 200),
            'losing_error_codes': [r.json().get('detail', {}).get('code') for r in results if r.status_code != 200]}
        path = Path(os.environ['SEC_GOOGLE_PRIVATE_RECEIPTS']) / ('canonical-gym-race-' + c['factory'].replace('.', '_') + '.json')
        with path.open('xb') as output: output.write((json.dumps(observation, indent=2) + '\n').encode())
        assert observation['unique_insert_workers'] == observation['unique_insert_backends'] == 2
        assert observation['one_new_container'] and observation['one_binding'] and observation['binding_owner_is_new_container']
        assert observation['one_server_owned_profile'] and observation['exactly_five_own_defaults'] and observation['losing_response_has_no_tokens']
        assert sorted(r.status_code for r in results) == [200, 409]
    finally:
        for engine in engines:
            assert engine.pool.checkedout() == 0 and engine.pool.size() == 1
            with engine.connect() as db:
                assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one()) == ('', '', '')
            engine.dispose()
