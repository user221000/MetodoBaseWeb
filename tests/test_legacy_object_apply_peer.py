"""Independent, synthetic persistence checks for the operator-only apply job."""
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from tests import test_legacy_object_apply as author
from web.database.models import Cliente, Usuario
from web.database.tenant_context import current_tenant
from web.services import legacy_object_apply as service
from web.storage.objects import ObjectAccessDenied, describe

account37_engine = author.account37_engine
case = author.case


def planned(case):
    return [json.loads(line)['data'] for line in case.journal.read_bytes().splitlines()
            if json.loads(line)['data'].get('event') == 'planned']


def test_planned_fsync_ack_loss_precedes_every_database_write_and_resumes_same_descriptor(case, monkeypatch):
    statements, calls = [], []
    event.listen(case.engine, 'before_cursor_execute',
        lambda _c, _u, sql, *_args: statements.append(sql.split()[0].upper()))
    real_fsync = service.os.fsync
    def lose_ack(fd):
        calls.append(fd)
        real_fsync(fd)
        if len(calls) == 2:
            raise OSError('Synthetic planned fsync acknowledgement loss')
    with monkeypatch.context() as patch:
        patch.setattr(service.os, 'fsync', lose_ack)
        patch.setattr(case.store, 'put', lambda *_a, **_k: pytest.fail('PUT after unconfirmed journal fsync'))
        with pytest.raises(OSError):
            author.execute(case)
    assert len(calls) == 2 and not set(statements) & {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}
    assert author.status(case) == (None, [], 0)
    first = planned(case)
    assert len(first) == 1
    assert author.execute(case)['applied'] == 1
    assert planned(case) == first and author.status(case)[0] == first[0]['descriptor']['id']
    assert case.original.read_bytes() == case.data and current_tenant.get() == ''


@pytest.mark.parametrize('commit_number', [1, 2], ids=['pending', 'ready-reference'])
def test_real_commit_then_ack_loss_never_returns_success_and_replay_uses_exact_reference(case, monkeypatch, commit_number):
    real_session, committed = service.Session, []
    class LostAckSession(real_session):
        def commit(self):
            super().commit()
            committed.append(True)
            if len(committed) == commit_number:
                raise OSError('Synthetic committed transaction acknowledgement loss')
    with monkeypatch.context() as patch:
        patch.setattr(service, 'Session', LostAckSession)
        with pytest.raises(OSError):
            author.execute(case)
    state = author.status(case)
    first = planned(case)
    assert len(first) == 1 and len(state[1]) == 1
    identity = first[0]['descriptor']['id']
    assert state == (None, [(identity, 'pending')], 0) if commit_number == 1 else state == (identity, [(identity, 'ready')], 0)
    assert author.execute(case)['applied'] == 1
    assert author.status(case) == (identity, [(identity, 'ready')], 0) and planned(case) == first
    assert case.original.read_bytes() == case.data and current_tenant.get() == ''


def test_final_session_close_failure_cannot_ack_an_already_committed_reference(case, monkeypatch):
    real_session, closed = service.Session, []
    class FailedCloseSession(real_session):
        def close(self):
            super().close()
            closed.append(True)
            if len(closed) == 3:
                raise OSError('Synthetic final Session close failure')
    with monkeypatch.context() as patch:
        patch.setattr(service, 'Session', FailedCloseSession)
        with pytest.raises(OSError):
            author.execute(case)
    assert len(closed) == 3
    first = author.status(case)
    assert first[0] is not None and first[1] == [(first[0], 'ready')] and first[2] == 0
    assert author.execute(case)['applied'] == 1 and author.status(case) == first
    assert len(planned(case)) == 1 and current_tenant.get() == ''


@pytest.mark.parametrize('drift', ['owner-deleted', 'client-foreign'])
def test_canonical_tenant_drift_during_put_never_attaches_published_bytes(case, monkeypatch, drift):
    real_put = case.store.put
    def change_authority(*args, **kwargs):
        real_put(*args, **kwargs)
        with Session(case.engine) as db:
            if drift == 'owner-deleted':
                db.get(Usuario, 'apply-a').deleted_at = datetime.now(UTC)
            else:
                db.scalar(select(Cliente).where(Cliente.id_cliente == 'client-a')).gym_id = 'apply-b'
            db.commit()
    monkeypatch.setattr(case.store, 'put', change_authority)
    with pytest.raises(service.ApplyError):
        author.execute(case)
    state = author.status(case)
    assert state[0] is None and len(state[1]) == 1 and state[1][0][1] == 'pending' and state[2] == 0
    assert case.original.read_bytes() == case.data and current_tenant.get() == ''
    with Session(case.engine) as db:
        assert db.get(Usuario, 'apply-b').activo is True
        foreign = db.scalar(select(Cliente).where(Cliente.id_cliente == 'client-b'))
        assert foreign.gym_id == 'apply-b' and foreign.total_planes_generados == 0


def test_a_valid_journal_hash_chain_cannot_authorize_another_tenants_descriptor(case, monkeypatch):
    foreign = describe('apply-b', 'plan_pdf', case.data, 'application/pdf')
    with service.Journal(case.journal, case.bundle.binding) as journal:
        journal.append({'event': 'planned', 'entry_sha256': service.entry_key(case.bundle.selected[0]),
                        'descriptor': asdict(foreign)})
    original_journal = case.journal.read_bytes()
    statements = []
    event.listen(case.engine, 'before_cursor_execute',
        lambda _c, _u, sql, *_args: statements.append(sql.split()[0].upper()))
    monkeypatch.setattr(case.store, 'put', lambda *_a, **_k: pytest.fail('Foreign descriptor reached PUT'))
    with pytest.raises(ObjectAccessDenied):
        author.execute(case)
    assert not set(statements) & {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}
    assert author.status(case) == (None, [], 0) and case.journal.read_bytes() == original_journal
    assert case.original.read_bytes() == case.data and current_tenant.get() == ''


def test_renewed_operator_window_reuses_the_same_mapping_journal_and_ready_object(case):
    assert author.execute(case)['applied'] == 1
    first, first_planned = author.status(case), planned(case)
    renewal = case.now + timedelta(hours=2)
    value = json.loads(case.approval.read_bytes())
    value.update(issued_at=renewal.isoformat(), expires_at=(renewal + timedelta(hours=1)).isoformat())
    case.approval.write_bytes(service.canonical(value))
    assert author.execute(case, clock=lambda: renewal)['applied'] == 1
    assert author.status(case) == first and planned(case) == first_planned
    assert case.original.read_bytes() == case.data and current_tenant.get() == ''


def test_source_capability_drift_after_put_leaves_pending_and_can_resume_only_after_restoration(case, monkeypatch):
    baseline, changed = case.bundle.source_check(), []
    monkeypatch.setattr(case.bundle, 'source_check',
        lambda: {**baseline, 'commit': '0' * 40} if changed else baseline)
    real_put = case.store.put
    def change_source(*args, **kwargs):
        real_put(*args, **kwargs)
        changed.append(True)
    monkeypatch.setattr(case.store, 'put', change_source)
    with pytest.raises(service.ApplyError, match='artifact_binding_changed'):
        author.execute(case)
    first = author.status(case)
    assert first[0] is None and first[1][0][1] == 'pending' and first[2] == 0
    assert len(planned(case)) == 1
    changed.clear()
    monkeypatch.setattr(case.store, 'put', real_put)
    assert author.execute(case)['applied'] == 1
    assert author.status(case) == (first[1][0][0], [(first[1][0][0], 'ready')], 0)
    assert len(planned(case)) == 1 and case.original.read_bytes() == case.data and current_tenant.get() == ''
