"""Own UUID33, real HTTP-issued proofs, two restricted pool1 race workers."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, get_ident
from time import monotonic
import uuid

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session

from tests.test_security_google33_peer import *  # noqa:F403
from tests.integration_google33_postgres import google_db
from tests.test_personal_progress_http import progress_http
from tests.test_google33_association_security import (
    test_unbound_third_party_google_subject_requires_independent_link_before_login,
    test_unbound_google_subject_cannot_supply_fresh_primary_for_factor_account,
    test_provider_validation_controls_do_not_issue_a_local_session,
)
from tests.integration_google33_postgres import test_provider_await_has_no_transaction_or_account_lock_and_pool1_is_clean
from tests.test_google33_headers import test_unconfirmed_publication_rollback_and_preclose_failure_still_discard_owned_session


@pytest.fixture(scope='module')
def progress_db(google_db):
    return google_db


def blank(engine):
    assert engine.pool.checkedout() == 0 and engine.pool.size() == 1
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one()) == ('', '', '')


def test_actual33_contract_is_restricted_and_adds_only_trigger_functions(google_db):
    from web.database.models import Base
    from web.database.google_identity_policy import signature
    admin, app = google_db
    assert len(Base.metadata.tables) == 35
    with app.connect() as db:
        assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') FROM pg_roles WHERE rolname=current_user")).one()) == (False, False, False, False, False)
        assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r'")) == 36
        assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 26
        assert db.scalar(text("SELECT count(*) FROM pg_proc WHERE pronamespace=current_schema()::regnamespace")) == 26
        assert db.scalar(text("SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal")) == 12
        metadata = signature(db)
        assert len(metadata['functions']) == 2 and len(metadata['triggers']) == 2
        assert all(row[2] == 'trigger' and row[3] is False and row[-1] is True for row in metadata['functions'])
    blank(app)


def race_engines(c):
    from web.database.tenant_context import configure_tenant_engine
    engines = [configure_tenant_engine(create_engine(c['engine'].url, pool_size=1, max_overflow=0, pool_timeout=5)) for _ in range(2)]
    for engine in engines:
        with engine.connect() as db:
            assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one()) == (False, False, False, False)
    return engines


def test_one_real_intent_has_one_winner_under_two_pool1_workers(google_http):
    from web.auth import verificar_token
    from web.services import google_link
    from web.database.models import GoogleLinkIntent, AuthExternalIdentity, Usuario
    c = google_http
    prepared = issue(c)  # noqa:F405
    assert prepared.status_code == 200
    access = c['headers']['Authorization'][7:]
    expected = verificar_token(access)
    assert expected and expected['id'] == c['user']
    engines = race_engines(c)
    lock_observed = Event()
    losing_request_done = Event()
    arrivals = []
    for engine in engines:
        with Session(engine, autoflush=False) as db:
            google_link.admit(db, expected, access, phase='confirm', now=c['clock'][0])
        @event.listens_for(engine, 'after_cursor_execute')
        def hold_actual_actor_lock(conn, cursor, statement, parameters, context, many):
            if 'FOR UPDATE NOWAIT' in statement:
                arrivals.append((get_ident(), monotonic()))
                lock_observed.set()
                assert losing_request_done.wait(10), 'No independent worker observed the real held lock'
    def worker(engine):
        with Session(engine, autoflush=False) as db:
            pid = db.scalar(text('SELECT pg_backend_pid()'))
            try:
                google_link.confirm(db, expected, access, prepared.json()['intent'], now=c['clock'][0])
                return 200, pid
            except google_link.HTTPException as error:
                google_link.rollback(db)
                losing_request_done.set()
                return error.status_code, pid
    try:
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes = list(pool.map(worker, engines))
        assert sorted(status for status, _ in outcomes) == [200, 409]
        assert len({pid for _, pid in outcomes}) == 2 and lock_observed.is_set() and len(arrivals) == 1
        with Session(c['admin']) as db:
            assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.subject == c['google']['sub'])) == c['user']
            assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id == c['user'])) is not None
            assert db.get(Usuario, c['user']).session_version == 1
        for engine in engines: blank(engine)
    finally:
        for engine in engines: engine.dispose()
    blank(c['engine'])


def test_distinct_real_actors_cannot_acquire_one_subject_in_two_pool1_workers(google_http):
    from web.auth import verificar_token
    from web.services import google_link
    from web.database.models import AuthExternalIdentity, GoogleLinkIntent, Usuario
    c = google_http
    first = issue(c)  # noqa:F405
    assert first.status_code == 200
    email = uuid.uuid4().hex + '@example.invalid'
    created = c['client'].post('/api/auth/registro', json={'email': email, 'password': PASSWORD, 'nombre': 'Other race actor'})  # noqa:F405
    assert created.status_code == 200
    other_access = created.json()['token']
    second = c['client'].post('/api/auth/google/link/start', headers={'Authorization': 'Bearer ' + other_access},
        json={'password': PASSWORD, 'google_credential': c['credential']()})  # noqa:F405
    assert second.status_code == 200
    access = c['headers']['Authorization'][7:]
    expected = [verificar_token(access), verificar_token(other_access)]
    assert expected[0]['id'] != expected[1]['id']
    args = [(expected[0], access, first.json()['intent']), (expected[1], other_access, second.json()['intent'])]
    engines = race_engines(c)
    barrier = Barrier(2)
    arrivals = []
    for engine, (actor, token, _) in zip(engines, args):
        with Session(engine, autoflush=False) as db: google_link.admit(db, actor, token, phase='confirm', now=c['clock'][0])
        @event.listens_for(engine, 'before_cursor_execute')
        def meet_at_real_unique_insert(conn, cursor, statement, parameters, context, many):
            if statement.startswith('INSERT INTO auth_external_identities'):
                arrivals.append((get_ident(), monotonic()))
                barrier.wait(timeout=10)
    def worker(pair):
        engine, (actor, token, intent) = pair
        with Session(engine, autoflush=False) as db:
            pid = db.scalar(text('SELECT pg_backend_pid()'))
            try:
                google_link.confirm(db, actor, token, intent, now=c['clock'][0])
                return 200, pid
            except google_link.HTTPException as error:
                google_link.rollback(db)
                return error.status_code, pid
    try:
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes = list(pool.map(worker, zip(engines, args)))
        assert sorted(status for status, _ in outcomes) == [200, 409] and len({pid for _, pid in outcomes}) == 2
        assert len({thread for thread, _ in arrivals}) == 2
        with Session(c['admin']) as db:
            rows = db.scalars(select(AuthExternalIdentity).where(AuthExternalIdentity.subject == c['google']['sub'])).all()
            assert len(rows) == 1
            ids = [actor['id'] for actor in expected]
            assert rows[0].user_id in ids and sorted(db.get(Usuario, actor).session_version for actor in ids) == [0, 1]
            intents = db.scalars(select(GoogleLinkIntent).where(GoogleLinkIntent.user_id.in_(ids))).all()
            assert len(intents) == 2 and sum(row.consumed_at is not None for row in intents) == 1
        for engine in engines: blank(engine)
    finally:
        for engine in engines: engine.dispose()
    blank(c['engine'])
