"""Explicit leased PG38 races; no SQL at collection and no automatic skips.

Root's future ci_web38 PG composition must provide link_db=(admin,restricted).
The original actor fixture is reused. One owned UUID contains all four cases;
each worker uses a separate pool1/overflow0, not a fictitious shared pool1.
This module is not part of automatic SQLite broad collection.
"""
from contextlib import contextmanager
import json
from threading import Event, Thread
import time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, select, text, update
from sqlalchemy.orm import Session

from tests import integration_client_link_services as shared
from web.client_link_schemas import InvitationAccept
from web.database.models import ClientLinkInvitation, ProductAnalyticsFact as Fact, Usuario
from web.database.repository import registrar_plan
from web.database.tenant_context import configure_tenant_engine, tenant_scope
from web.services import client_link_invitations as invitations, product_facts
from web.services.product_analytics_v2 import origin

case = shared.case


def claims(case):
    with Session(case['admin']) as db:
        actor = db.get(Usuario, case['gym'])
        return {'id': actor.id, 'tipo': actor.tipo, 'role': actor.role.value,
                'team_gym_id': actor.team_gym_id, 'session_version': actor.session_version}


class Worker:
    """Own one finite SQL worker; release observer gates and join before dispose."""
    def __init__(self, case, function, *, pause_owner=False):
        assert case['app'].dialect.name == 'postgresql'
        self.engine = configure_tenant_engine(create_engine(case['app'].url, pool_size=1,
            max_overflow=0, pool_timeout=5,
            connect_args={'options': '-c statement_timeout=6000 -c lock_timeout=5000'}))
        self.owner = case['gym']
        self.pid = None
        self.owner_locked = Event()
        self.release = Event()
        self.done = Event()
        self.result = None
        self.error = None
        self.pause_owner = pause_owner
        event.listen(self.engine, 'connect', self.connected)
        event.listen(self.engine, 'after_cursor_execute', self.after)

        def run():
            try:
                self.result = function(self.engine)
            except BaseException as error:
                self.error = error
            finally:
                self.done.set()
        self.thread = Thread(target=run, name='product38-owned-race')

    def connected(self, connection, _record):
        self.pid = connection.get_backend_pid()  # Metadata only, no SQL/cursor.

    def after(self, _connection, _cursor, statement, parameters, _context, _many):
        upper = ' '.join(statement.upper().split())
        values = parameters.values() if isinstance(parameters, dict) else parameters
        if self.pause_owner and 'FROM USUARIOS' in upper and 'FOR UPDATE' in upper and self.owner in values:
            self.pause_owner = False
            self.owner_locked.set()
            if not self.release.wait(4):
                raise TimeoutError('Own observation gate expired')

    def start(self):
        self.thread.start()
        return self

    def finish(self):
        self.thread.join(8)
        if self.thread.is_alive():
            # Keep the owned stack/pool until normal completion; never kill or
            # dispose under a live worker, even if the enclosing test failed.
            self.thread.join()
        if self.error is not None:
            raise self.error
        return self.result

    def close(self):
        self.release.set()
        if self.thread.ident is not None:
            self.thread.join(8)
            if self.thread.is_alive():
                self.thread.join()
        event.remove(self.engine, 'connect', self.connected)
        event.remove(self.engine, 'after_cursor_execute', self.after)
        assert self.engine.pool.checkedout() == 0
        self.engine.dispose()


@contextmanager
def worker(case, function, **kwargs):
    value = Worker(case, function, **kwargs)
    try:
        yield value.start()
    finally:
        value.close()


def blocked(admin, value):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if value.done.is_set():
            raise AssertionError('The expected owned worker did not wait for its row lock')
        if value.pid is not None:
            with Session(admin) as db:
                observed = db.scalar(text("SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid AND datname=current_database()"), {'pid': value.pid})
            if observed == 'Lock':
                return
        time.sleep(0.01)
    raise AssertionError('The actual PostgreSQL lock wait was not observed')


def declare(case, actor):
    def run(engine):
        with tenant_scope(case['gym']), Session(engine) as db:
            return origin(db, actor, 'gym', case['client'], value='demo', expected_version=0)
    return run


def accept(case, issued, token):
    def run(engine):
        with tenant_scope(case['person']), Session(engine) as db:
            return invitations.accept_invitation(db, shared.principal(case['person']),
                InvitationAccept(token=token, expected_version=issued['version'], confirm=True))
    return run


def test_revoked_session_while_origin_waits_on_owner_cannot_commit(case):
    actor = claims(case)
    with Session(case['admin']) as holder:
        holder.scalar(select(Usuario).where(Usuario.id == case['gym']).with_for_update())
        with worker(case, declare(case, actor)) as pending:
            blocked(case['admin'], pending)
            holder.execute(update(Usuario).where(Usuario.id == case['gym']).values(session_version=1))
            holder.commit()
            with pytest.raises(HTTPException) as denied:
                pending.finish()
            assert denied.value.status_code == 401
    with Session(case['admin']) as db:
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='origin_declared').count() == 0


def test_acceptance_first_preserves_prior_origin_then_declaration_applies_to_future(case):
    issued, token = shared.issue(case)
    with worker(case, accept(case, issued, token), pause_owner=True) as accepting:
        assert accepting.owner_locked.wait(2)
        with worker(case, declare(case, claims(case))) as declaring:
            blocked(case['admin'], declaring)
            accepting.release.set()
            assert accepting.finish()['status'] == 'active'
            assert declaring.finish()['origin'] == 'demo'
    with Session(case['admin']) as db:
        assert db.scalar(select(Fact.origin).where(Fact.owner_id == case['gym'], Fact.event_type == 'client_link_accepted')) == 'unknown'
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='origin_declared', origin='demo').count() == 1


def test_declaration_first_retains_R12_nowait_then_explicit_accept_retry_snapshots_demo(case):
    issued, token = shared.issue(case)
    with worker(case, declare(case, claims(case)), pause_owner=True) as declaring:
        assert declaring.owner_locked.wait(2)
        with worker(case, accept(case, issued, token)) as accepting:
            with pytest.raises(HTTPException) as busy:
                accepting.finish()
            assert busy.value.status_code == 409
        declaring.release.set()
        assert declaring.finish()['origin'] == 'demo'
    with Session(case['admin']) as db:
        assert db.get(ClientLinkInvitation, issued['invitation_id']).status == 'pending'
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='client_link_accepted').count() == 0
    # Explicit new request, not an automatic product retry or a changed oracle.
    with worker(case, accept(case, issued, token)) as retry:
        assert retry.finish()['status'] == 'active'
    with Session(case['admin']) as db:
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='client_link_accepted', origin='demo').count() == 1


def test_plan_fact_replay_after_new_classification_preserves_original_snapshot(case):
    actor = claims(case)
    raw = json.dumps({meal: {'kcal_objetivo': 100, 'kcal_real': 100, 'alimentos': {'synthetic': 50}}
                      for meal in ('desayuno', 'almuerzo', 'comida', 'cena')})
    with tenant_scope(case['gym']), Session(case['app']) as db:
        origin(db, actor, 'gym', case['client'], value='demo', expected_version=0)
    with tenant_scope(case['gym']), Session(case['app']) as db:
        identity = registrar_plan(db, case['gym'], case['client'], {'plan_json': raw}, return_id=True)
        db.commit()
    with Session(case['admin']) as db:
        row = db.scalar(select(Fact).where(Fact.owner_id == case['gym'], Fact.event_type == 'plan_saved'))
        before = (row.id, row.origin, row.occurred_at)
    with tenant_scope(case['gym']), Session(case['app']) as db:
        origin(db, actor, 'gym', case['client'], value='customer', expected_version=1)
    from web.database.models import PlanGenerado
    with tenant_scope(case['gym']), Session(case['app']) as db:
        product_facts.plan_saved(db, db.get(PlanGenerado, identity))
        db.commit()
    with Session(case['admin']) as db:
        rows = db.scalars(select(Fact).where(Fact.owner_id == case['gym'], Fact.event_type == 'plan_saved')).all()
        assert len(rows) == 1 and (rows[0].id, rows[0].origin, rows[0].occurred_at) == before
