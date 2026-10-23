"""Prepared current37 PG companion: one owned DB; inert until ROOT's lease.

Original PPL functions/marks/asserts stay literal except the explicitly named
PG transaction precondition for the two eligibility-projection cases. No
historical fixture, target, product path or legacy429 test is modified.
"""
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Thread

import pytest
from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core.routine_catalog import get_routine_program
from tests import followup34_http as authentic
from tests import test_routine_catalog as original
from tests import test_security_routines_http_peer as peer
from tests.ci_web37.pg_close import owned_database
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from web.database.models import (
    Base,
    UserRole,
    Usuario,
)
from web.database.models import (
    GenerationReservation as Personal,
)
from web.database.models import (
    GymGenerationReservation as Gym,
)
from web.database.schema_control import verify_runtime_schema
from web.database.tenant_context import (
    bind_verified_subject,
    configure_tenant_engine,
    current_tenant,
)
from web.services import product_analytics as analytics

REVISION = '20261020_account_security'
PATH = '/api/analytics/producto'
ACK = 'ROOT-R30-PPL53-ONE-UUID'
routine_http = authentic.followup_http
routine_peer_http = authentic.followup_http
analytics_http = authentic.followup_http


def record(name, value):
    root = Path(os.environ['R30_PPL_PRIVATE']).resolve()
    assert root.name.startswith('metodobase-account37-author-pg-r30-ppl-')
    target = root / 'witnesses'
    target.mkdir(exist_ok=True)
    with (target / (name + '-' + uuid.uuid4().hex + '.json')).open('x', encoding='utf8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def blank_pool(application):
    assert application.pool.size() == 5 and application.pool._max_overflow == 0
    assert application.pool.checkedout() == 0
    connections = []
    try:
        for _ in range(5):
            connection = application.connect()
            connections.append(connection)
            assert tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),"
                "current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true),"
                "current_setting('app.notification_exclude_digest',true)")).one()) == ('', '', '', '')
    finally:
        for connection in reversed(connections):
            connection.close()
    assert application.pool.checkedout() == 0


@pytest.fixture(scope='module')
def followup_db(tmp_path_factory):
    assert os.environ.get('R30_PPL_PG_ACK') == ACK, 'ROOT lease is required before any owned PostgreSQL work'
    with owned_database('postgresql', tmp_path_factory.mktemp('r30-ppl37')) as (url, admin):
        run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
        granting = application_engine(url, admin)
        application = None
        try:
            application = configure_tenant_engine(create_engine(granting.url,
                pool_size=5, max_overflow=0, pool_timeout=5))
            granting.dispose()
            verify_runtime_schema(application)
            blank_pool(application)
            yield admin, application
        finally:
            granting.dispose()
            if application is not None:
                application.dispose()


@pytest.fixture(autouse=True)
def released_after_case(followup_db):
    yield
    assert current_tenant.get() == ''
    blank_pool(followup_db[1])


test_catalog_is_generic_bounded_independent_and_complete = original.test_catalog_is_generic_bounded_independent_and_complete
test_owner_and_personal_have_no_cross_space_or_bootstrap = original.test_owner_and_personal_have_no_cross_space_or_bootstrap
test_valid_team_can_read_both_general_spaces = original.test_valid_team_can_read_both_general_spaces
test_read_paths_do_not_write_or_return_subject_data = original.test_read_paths_do_not_write_or_return_subject_data
test_persisted_revocation_is_enforced = original.test_persisted_revocation_is_enforced
test_ambiguous_owner_and_methods_fail_without_adopting_profile = original.test_ambiguous_owner_and_methods_fail_without_adopting_profile
test_missing_and_malformed_bearer_are_denied = original.test_missing_and_malformed_bearer_are_denied
test_pages_are_inert_and_keyboard_controls_are_native = original.test_pages_are_inert_and_keyboard_controls_are_native
test_cleanup_failure_does_not_return_catalogue = original.test_cleanup_failure_does_not_return_catalogue
test_real_matrix_is_read_only_generic_and_never_adopts_client = peer.test_real_matrix_is_read_only_generic_and_never_adopts_client
test_actor_revocation_null_invite_and_signed_scope_forgery = peer.test_actor_revocation_null_invite_and_signed_scope_forgery
test_parent_must_remain_canonical_for_both_spaces = peer.test_parent_must_remain_canonical_for_both_spaces
test_ambiguity_validation_and_methods_have_no_fallback = peer.test_ambiguity_validation_and_methods_have_no_fallback
test_owned_read_failure_is_opaque_after_real_auth = peer.test_owned_read_failure_is_opaque_after_real_auth
test_all_four_public_shells_are_inert_and_nonce_bound = peer.test_all_four_public_shells_are_inert_and_nonce_bound


def test_service_uses_only_eligibility_projection(routine_http):
    """Explicit PG companion: full setup witness precedes the measured SUT."""
    case = routine_http
    from web.services.routine_catalog import catalog_for_subject
    principal = case['raw'].get('/api/auth/me').json()
    setup, queries = [], []

    def observe_setup(_connection, _cursor, sql, parameters, _context, _many):
        setup.append({'sql': sql, 'parameters': parameters})

    def observe(_connection, _cursor, sql, _parameters, _context, _many):
        queries.append(sql)

    with Session(case['engine']) as db:
        event.listen(case['engine'], 'before_cursor_execute', observe_setup)
        try:
            connection = db.connection()  # Finite PG-only transaction precondition.
            neutral = tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),"
                "current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true),"
                "current_setting('app.notification_exclude_digest',true)")).one())
        finally:
            event.remove(case['engine'], 'before_cursor_execute', observe_setup)
        assert neutral == ('', '', '', '')
        assert setup and all(row['sql'].lstrip().upper().startswith('SELECT') for row in setup)
        record('ppl-transaction-setup', {'factory': case['factory_name'], 'tenant_and_purposes': neutral,
            'complete_setup_sql': setup, 'measured_SUT_has_no_filter': True})
        event.listen(case['engine'], 'before_cursor_execute', observe)
        try:
            result = catalog_for_subject(db, principal, 'gym')
        finally:
            event.remove(case['engine'], 'before_cursor_execute', observe)
    assert result['program'] == get_routine_program()
    assert len(queries) == 1
    assert not any(word in queries[0].lower() for word in ('password', 'email', 'nombre', 'cliente'))
    assert [column.strip() for column in queries[0].split('FROM', 1)[0].removeprefix('SELECT ').split(',')] == [
        'usuarios.' + name for name in ('id', 'tipo', 'role', 'team_gym_id', 'activo',
                                      'deleted_at', 'invitation_token', 'session_version')]


def seed(case, subject, *, scope='gym', count=1):
    stamp = datetime.now(UTC) - timedelta(hours=1)
    with Session(case['admin']) as db:
        for _ in range(count):
            values = {'id': str(uuid.uuid4()), 'request_key': uuid.uuid4().hex, 'period': stamp.strftime('%Y-%m'),
                'status': 'completed', 'persisted_at': stamp, 'created_at': stamp, 'updated_at': stamp}
            if scope == 'gym':
                values.update(gym_id=subject, request_hash='a' * 64, local_date=stamp.date(),
                    timezone='America/Mexico_City', catalog_plan='free', result_json='{}')
                db.add(Gym(**values))
            else:
                values.update(user_id=subject, publication_protocol=1)
                db.add(Personal(**values))
        db.commit()


def private(response, status):
    assert response.status_code == status
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "default-src 'none'" in response.headers['content-security-policy']
    assert all('mb_refresh' not in value for value in response.headers.get_list('set-cookie'))


def test_pg_current37_schema_index_role_and_pool_contract(followup_db):
    application = followup_db[1]
    assert len(Base.metadata.tables) == 41
    with application.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == REVISION
        assert len(inspect(db).get_table_names()) == 42
        assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,"
            "pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') "
            "FROM pg_roles WHERE rolname=current_user")).one()) == (False, False, False, False, False)
        assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
            "AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 32
        from web.database.alembic.history_index_contract_v1 import (
            history_index_signature,
        )
        target = json.loads((Path(__file__).resolve().parents[1] / 'web/database/alembic/schema_targets' /
                             '20261020_account_security_postgresql.json').read_bytes())
        assert history_index_signature(db) == target['history_order_index']
    blank_pool(application)


def test_pg_real_gym_and_personal_snapshots_start_neutral_then_bind_own_subject(analytics_http, monkeypatch):
    case = analytics_http
    seed(case, case['user'])
    actor = original.login_actor(case, UserRole.ADMIN, team=True)
    seed(case, actor, scope='personal')
    seed(case, case['member'], scope='personal', count=2)
    seed(case, case['member'], count=2)
    factories, cleanup, observed, statements = [], [], [], []
    inspecting = False
    real_read = analytics.read_report

    class Owned(Session):
        def rollback(self):
            cleanup.append(('rollback', self.info.get('tenant_id')))
            return super().rollback()

        def close(self):
            super().close()
            cleanup.append(('closed', self.info.get('tenant_id')))

    def owned():
        factories.append(current_tenant.get())
        return Owned(case['engine'], autoflush=False)

    def read(*args, **kwargs):
        incoming = current_tenant.get()
        value = real_read(*args, factory=owned, **kwargs)
        assert current_tenant.get() == incoming
        return value

    def observe(connection, _cursor, sql, _parameters, _context, _many):
        nonlocal inspecting
        statements.append(sql.lstrip().split(None, 1)[0].upper())
        authority = sql.startswith('SELECT usuarios.id, usuarios.tipo')
        ledger = any('FROM ' + model.__tablename__ in sql for model in (Gym, Personal))
        if not inspecting and (authority or ledger):
            inspecting = True
            try:
                state = tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),"
                    "current_setting('transaction_isolation'),current_setting('transaction_read_only')")).one())
                observed.append(('authority' if authority else 'ledger', state))
            finally:
                inspecting = False

    monkeypatch.setattr(analytics, 'read_report', read)
    event.listen(case['engine'], 'before_cursor_execute', observe)
    try:
        for scope, subject in (('gym', case['user']), ('personal', actor)):
            response = case['raw'].get(PATH, params={'context': scope})
            private(response, 200)
            assert response.json()['scope'] == scope
            assert sum(row['saved_publications'] for row in response.json()['weekly']) == 1
            assert cleanup[-2:] == [('rollback', subject), ('closed', subject)]
            assert subject not in response.text
    finally:
        event.remove(case['engine'], 'before_cursor_execute', observe)
    assert factories == ['', '']
    assert observed and all(state == ('', 'repeatable read', 'on') for kind, state in observed if kind == 'authority')
    assert {state for kind, state in observed if kind == 'ledger'} == {
        (case['user'], 'repeatable read', 'on'), (actor, 'repeatable read', 'on')}
    assert not set(statements) & {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'ALTER', 'DROP'}
    # Server-side RLS witness has no caller WHERE selector, in fresh Sessions.
    counts = []
    for model, subject in ((Gym, case['user']), (Personal, actor)):
        with Session(case['engine']) as db:
            assert db.scalar(select(func.count()).select_from(model)) == 0
            bind_verified_subject(db, subject)
            assert db.scalar(select(func.count()).select_from(model)) == 1
            counts.append((0, 1))
    record('r30-snapshot', {'factory': case['factory_name'], 'authority_empty': True,
        'ledger_context_count': sum(kind == 'ledger' for kind, _ in observed),
        'snapshot': ['repeatable read', 'on'], 'neutral_then_own_RLS_counts': counts,
        'cleanup_before_response': True, 'no_DML_normal_reads': True})


def test_pg_repeatable_snapshot_keeps_facts_and_authority_after_concurrent_commit(analytics_http):
    case = analytics_http
    seed(case, case['user'])
    changed, errors, workers = [], [], []

    def writer():
        try:
            seed(case, case['user'])
            with Session(case['admin']) as db:
                db.get(Usuario, case['user']).activo = False
                db.commit()
        except Exception as error:  # noqa: BLE001 -- retain only worker class; no secret payload
            errors.append(type(error).__name__)

    def after(_connection, _cursor, sql, _parameters, _context, _many):
        if not changed and sql.startswith('SELECT usuarios.id, usuarios.tipo'):
            changed.append(True)
            worker = Thread(target=writer)
            workers.append(worker)
            worker.start()
            worker.join(10)
            assert not worker.is_alive(), 'Owned writer did not finish normally'

    event.listen(case['engine'], 'after_cursor_execute', after)
    try:
        response = case['raw'].get(PATH, params={'context': 'gym'})
    finally:
        event.remove(case['engine'], 'after_cursor_execute', after)
        for worker in workers:
            worker.join(10)
            assert not worker.is_alive(), 'Owned writer retained; no forced stop or DROP is permitted'
    private(response, 200)
    assert changed == [True] and errors == []
    assert sum(row['saved_publications'] for row in response.json()['weekly']) == 1
    private(case['raw'].get(PATH, params={'context': 'gym'}), 401)
    record('r30-repeatable-read', {'factory': case['factory_name'], 'committed_writer_joined': True,
        'first_snapshot_publications': 1, 'later_read_after_revocation': 401})


@pytest.mark.parametrize('fault', ['rollback', 'close'])
def test_pg_cleanup_uncertainty_cannot_publish_report(analytics_http, monkeypatch, caplog, fault):
    case = analytics_http
    operations = []
    real_read = analytics.read_report

    class Broken(Session):
        def rollback(self):
            operations.append('rollback')
            if fault == 'rollback':
                raise RuntimeError('PRIVATE_R30_PG_CLEANUP')
            return super().rollback()

        def close(self):
            operations.append('close')
            if fault == 'close':
                raise RuntimeError('PRIVATE_R30_PG_CLEANUP')
            return super().close()

        def invalidate(self):
            super().invalidate()
            operations.append('invalidated')

    monkeypatch.setattr(analytics, 'read_report', lambda *args, **kwargs:
        real_read(*args, factory=lambda: Broken(case['engine'], autoflush=False), **kwargs))
    response = case['raw'].get(PATH, params={'context': 'gym'})
    private(response, 503)
    assert response.json()['detail']['code'] == 'analytics_unavailable'
    assert operations == ['rollback', 'close', 'invalidated']
    assert 'PRIVATE_R30_PG_CLEANUP' not in response.text + caplog.text
    assert case['engine'].pool.checkedout() == 0
    record('r30-cleanup', {'factory': case['factory_name'], 'fault': fault, 'operations_before_response': operations,
        'status': 503, 'remaining_checkout': 0})


def test_pg_readonly_rejects_deliberate_DML_without_durable_change(analytics_http, monkeypatch, caplog):
    case = analytics_http
    codes = []
    with Session(case['admin']) as db:
        before = db.get(Usuario, case['user']).nombre

    def attempted(db, scope, _context):
        try:
            db.execute(text('UPDATE usuarios SET nombre=:marker WHERE id=:subject'),
                {'marker': 'PRIVATE_R30_READONLY_WITNESS', 'subject': scope})
        except DBAPIError as error:
            codes.append(error.orig.pgcode)
            raise
        raise AssertionError('Read-only write unexpectedly admitted')

    monkeypatch.setattr(analytics, '_preparation', attempted)
    response = case['raw'].get(PATH, params={'context': 'gym'})
    private(response, 503)
    assert codes == ['25006']
    assert 'PRIVATE_R30_READONLY_WITNESS' not in response.text + caplog.text
    with Session(case['admin']) as db:
        assert db.get(Usuario, case['user']).nombre == before
    assert case['engine'].pool.checkedout() == 0
    record('r30-readonly', {'factory': case['factory_name'], 'deliberate_DML_rejected_SQLSTATE': codes,
        'durable_subject_unchanged': True, 'status': 503})
