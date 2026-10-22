"""Separate27-case current37 PG phase. No connection at import/collection.

B13 runs with the restricted normal app factory. R07 deliberately uses the
existing global operator, and separately proves the app role cannot substitute.
These are companions, never a claim that74+48 SQLite cases ran on PostgreSQL.
"""
import json
from dataclasses import asdict
from datetime import UTC, datetime
from threading import Event, Thread

import pytest
from sqlalchemy import event, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from tests import billing13_legacy_apply37_pg_fixtures as fixtures
from tests.billing13_legacy_apply37_pg_fixtures import (
    ProviderFacts,
    billing_facts,
    execute,
    manifest,
    object_status,
    record,
    seed_billing,
)
from web.database.models import Cliente, PlanGenerado, PurchaseIntent, Usuario
from web.database.tenant_context import current_tenant, tenant_scope
from web.services import billing_reconciliation as billing
from web.services import legacy_object_apply as objects
from web.services import legacy_object_inventory as inventory
from web.services.billing_reconciliation_providers import RetryableRead
from web.storage.objects import ObjectAccessDenied, ObjectUnavailable, describe

database_schema = fixtures.database_schema
isolated_database = fixtures.isolated_database
pg37 = fixtures.pg37
released = fixtures.released
billing_case = fixtures.billing_case
object_case = fixtures.object_case


def apply_billing(case, reader, selection=None, **options):
    return billing.run(selection or manifest(case), apply=True, factory=case.factory,
        reader_factory=reader.factory, **options)


def test_current37_physical_role_and_blank_purposes(pg37):
    from tests.account37_qa_pg_fixtures import witness
    value = witness(pg37.app)
    assert value['role_flags_and_owner_membership'] == [False] * 5
    assert value['FORCE_RLS'] == 32 and value['physical'] == 42 and value['ORM'] == 41
    record('physical-current37', value)


def test_b13_plan_binds_real_GUC_without_DML_or_SDK_and_restores_caller(billing_case):
    case = billing_case
    constructions, observed, writes = [], [], []
    probing = False
    def factory():
        constructions.append(current_tenant.get())
        return case.factory()
    def observe(connection, _cursor, sql, *_args):
        nonlocal probing
        if probing:
            return
        if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}:
            writes.append(sql)
        if 'FROM subscriptions' in sql:
            probing = True
            try:
                observed.append(tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),"
                    "current_setting('statement_timeout'),current_setting('lock_timeout')")).one()))
            finally:
                probing = False
    before = billing_facts(case)
    event.listen(case.engine, 'before_cursor_execute', observe)
    token = current_tenant.set(case.foreign)
    try:
        reply = billing.run(manifest(case), factory=factory,
            reader_factory=lambda *_: pytest.fail('Plan constructed provider'))
        assert current_tenant.get() == case.foreign
    finally:
        current_tenant.reset(token)
        event.remove(case.engine, 'before_cursor_execute', observe)
    assert reply['planned'] == 1 and reply['provider_reads'] == 0 and not writes
    assert constructions == [''] and observed == [(case.subject, '5s', '1s')]
    assert billing_facts(case) == before
    record('b13-plan', {'GUC_timeouts': observed, 'factory_context': constructions, 'DML': 0, 'SDK': 0})


@pytest.mark.parametrize('provider', ['stripe', 'mercadopago'], ids=['stripe', 'mp'])
def test_b13_lost_callback_repairs_and_replays_same_business_facts(pg37, provider):
    case = seed_billing(pg37, provider=provider)
    reader = ProviderFacts(case)
    before = billing_facts(case)
    selected = manifest(case, provider=provider)
    assert apply_billing(case, reader, selected)['reconciled'] == 1
    first = billing_facts(case)
    assert first['subscription'][1] == 'active' and first['quota'][:4] == ('pro', 'active', 5, 1)
    assert first['user'] == before['user'] and len(first['payments']) == int(provider == 'mercadopago')
    assert apply_billing(case, reader, selected)['reconciled'] == 1
    assert billing_facts(case) == first
    record('b13-replay', {'provider': provider, 'business_facts_identical': True,
        'used_quota': 1, 'operational_updated_at_excluded_as_in_original': True})


@pytest.mark.parametrize('provider', ['stripe', 'mercadopago'], ids=['stripe', 'mp'])
def test_b13_selected_purchase_cannot_adopt_second_intent_same_actor(pg37, provider):
    import uuid
    case = seed_billing(pg37, provider=provider)
    reader = ProviderFacts(case)
    other = str(uuid.uuid4())
    with Session(case.admin) as db:
        intent = db.get(PurchaseIntent, case.intent)
        intent.operation = 'checkout' if provider == 'stripe' else 'preference'
        intent.provider_reference_id = 'cs_b13' if provider == 'stripe' else 'pref_b13'
        db.add(PurchaseIntent(id=other, subject_id=case.subject, provider=provider,
            operation='elements' if provider == 'stripe' else 'preference', plan='pro_usuario',
            amount_cents=case.amount, currency='mxn', request_key=uuid.uuid4().hex,
            status='provider_created', provider_reference_id='other_' + uuid.uuid4().hex,
            provider_customer_id=case.customer))
        db.commit()
    if provider == 'stripe':
        reader.subscription_fact['metadata']['purchase_intent_id'] = other
    else:
        reader.payment_fact['external_reference'] = other
        reader.payment_fact['metadata']['purchase_intent_id'] = other
    before = billing_facts(case)
    reply = apply_billing(case, reader, manifest(case, provider=provider, kind='purchase_intent'))
    assert reply['manual'] == 1 and reply['reconciled'] == 0 and billing_facts(case) == before
    with Session(case.admin) as db:
        assert db.get(PurchaseIntent, other).status == 'provider_created'


def test_b13_each_resource_uses_own_tenant_and_cursor_cannot_adopt_foreign(billing_case, pg37):
    first, second = billing_case, seed_billing(pg37)
    readers = {case.subject: ProviderFacts(case) for case in (first, second)}
    document = json.loads(manifest(first))
    document['resources'] = [
        {**document['resources'][0], 'subject_id': first.foreign},
        document['resources'][0], json.loads(manifest(second))['resources'][0],
    ]
    raw = json.dumps(document).encode()
    observed = []
    def reader_factory(budget):
        observed.append(current_tenant.get())
        return readers[current_tenant.get()].factory(budget)
    cursor = None
    for expected in ('manual', 'reconciled', 'reconciled'):
        reply = billing.run(raw, apply=True, factory=first.factory, reader_factory=reader_factory,
            cursor=cursor, max_items=1)
        assert reply[expected] == 1 and reply['visited'] == 1
        cursor = reply['next_cursor']
    assert reply['complete'] and cursor is None and observed == [first.subject, second.subject]
    assert billing_facts(first)['quota'][3] == billing_facts(second)['quota'][3] == 1
    with pytest.raises(ValueError):
        billing.run(raw + b' ', cursor=billing._cursor('0' * 64, 1), factory=first.factory)
    record('b13-resource-contexts', {'subjects': observed, 'foreign_provider_reads': 0, 'cursor_advanced_per_exact_resource': True})


def test_b13_provider_timeout_rolls_back_and_retains_exact_cursor(billing_case):
    case = billing_case
    reader = ProviderFacts(case)
    before = billing_facts(case)
    reader.failure = RetryableRead('synthetic-provider-timeout')
    reply = apply_billing(case, reader)
    assert reply['retryable'] == 1 and not reply['complete'] and reply['next_cursor']
    assert billing_facts(case) == before
    reader.failure = None
    assert apply_billing(case, reader, cursor=reply['next_cursor'])['reconciled'] == 1


def test_b13_existing_actor_lock_conflicts_with_real_SELECT_FOR_UPDATE(billing_case):
    case = billing_case
    reader = ProviderFacts(case)
    before, observed, states = billing_facts(case), [], []
    def statement(_connection, _cursor, sql, *_args):
        if sql.lower().lstrip().startswith('update usuarios set'):
            observed.append(sql)
    def failed(context):
        states.append(getattr(context.original_exception, 'pgcode', None))
    event.listen(case.engine, 'before_cursor_execute', statement)
    event.listen(case.engine, 'handle_error', failed)
    try:
        with Session(case.admin) as holder:
            holder.execute(select(Usuario.id).where(Usuario.id == case.subject).with_for_update()).one()
            reply = apply_billing(case, reader)
            holder.rollback()
    finally:
        event.remove(case.engine, 'before_cursor_execute', statement)
        event.remove(case.engine, 'handle_error', failed)
    assert reply['unconfirmed'] == 1 and not reply['complete'] and reply['next_cursor']
    assert observed and '55P03' in states and billing_facts(case) == before
    assert apply_billing(case, reader, cursor=reply['next_cursor'])['reconciled'] == 1
    record('b13-physical-lock', {'product_SQL': observed, 'holder': 'SELECT usuarios.id FOR UPDATE',
        'SQLSTATE': states, 'timeout_ms': 1000, 'unconfirmed_without_cursor_advance': True})


@pytest.mark.parametrize('provider', ['stripe', 'mercadopago'], ids=['stripe', 'mp'])
def test_b13_second_provider_read_after_physical_lock_observes_current_reversal(pg37, provider):
    case = seed_billing(pg37, provider=provider)
    reader = ProviderFacts(case)
    selected = manifest(case, provider=provider)
    assert apply_billing(case, reader, selected)['reconciled'] == 1
    first_read, lock_attempt, replies, errors = Event(), Event(), [], []
    original_read = reader.read
    reads = []
    def reading(label, value):
        snapshot = original_read(label, value)
        if label[0] in {'subscription', 'payment'}:
            reads.append(label)
            if len(reads) == 1:
                first_read.set()
        return snapshot
    reader.read = reading
    def statement(_connection, _cursor, sql, *_args):
        if sql.lower().lstrip().startswith('update usuarios set'):
            lock_attempt.set()
    def worker():
        try:
            replies.append(apply_billing(case, reader, selected))
        except Exception as error:  # noqa: BLE001 -- retain failure type; normal join and assertions below reject it.
            errors.append(type(error).__name__)
    thread = Thread(target=worker, name='bounded-b13-pg-lock')
    event.listen(case.engine, 'before_cursor_execute', statement)
    try:
        with Session(case.admin) as holder:
            holder.execute(select(Usuario.id).where(Usuario.id == case.subject).with_for_update()).one()
            thread.start()
            try:
                assert first_read.wait(5) and lock_attempt.wait(5)
                if provider == 'stripe':
                    reader.subscription_fact['status'] = 'canceled'
                else:
                    reader.payment_fact['status'] = 'refunded'
            finally:
                holder.rollback()
    finally:
        if thread.ident is not None:
            thread.join(15)  # Normal bounded SDK/SQL completion; never kill/terminate.
        event.remove(case.engine, 'before_cursor_execute', statement)
    assert not thread.is_alive() and not errors and replies[0]['reconciled'] == 1 and len(reads) >= 2
    state = billing_facts(case)
    assert state['subscription'][1] in {'canceled', 'unpaid'} and state['quota'][0] == 'starter' and state['quota'][3] == 1
    assert len(state['payments']) == int(provider == 'mercadopago')
    record('b13-fresh-read', {'provider': provider, 'canonical_reads': len(reads), 'joined_normally': True,
        'reversal_preserved': True, 'usage_not_reset': True})


@pytest.mark.parametrize('committed', [False, True], ids=['before-commit', 'after-commit'])
def test_b13_commit_uncertainty_retains_cursor_and_replay_does_not_duplicate(billing_case, committed):
    case = billing_case
    reader = ProviderFacts(case)
    before = billing_facts(case)
    class LostAck(Session):
        def commit(self):
            if committed:
                super().commit()
            raise OSError('synthetic-commit-uncertainty')
    bad_factory = sessionmaker(bind=case.engine, class_=LostAck, autoflush=False)
    reply = billing.run(manifest(case), apply=True, factory=bad_factory, reader_factory=reader.factory)
    assert reply['unconfirmed'] == 1 and not reply['complete'] and reply['next_cursor']
    uncertain = billing_facts(case)
    assert (uncertain == before) is (not committed)
    assert apply_billing(case, reader, cursor=reply['next_cursor'])['reconciled'] == 1
    stable = billing_facts(case)
    assert stable['quota'][3] == 1 and apply_billing(case, reader)['reconciled'] == 1
    assert billing_facts(case) == stable


@pytest.mark.parametrize('fault', ['rollback', 'close'], ids=['rollback', 'close'])
def test_b13_owned_cleanup_failure_never_acknowledges_plan(billing_case, fault):
    case = billing_case
    class FailedCleanup(Session):
        def rollback(self):
            super().rollback()
            if fault == 'rollback':
                raise OSError('synthetic-rollback-uncertainty')
        def close(self):
            super().close()
            if fault == 'close':
                raise OSError('synthetic-close-uncertainty')
    reply = billing.run(manifest(case), factory=sessionmaker(bind=case.engine, class_=FailedCleanup))
    assert reply['unconfirmed'] == 1 and reply['planned'] == 0 and reply['next_cursor'] and not reply['complete']


@pytest.mark.parametrize('apply_mode', [False, True], ids=['plan', 'apply'])
def test_b13_active_borrowed_PG_transaction_is_preserved_without_any_finalizer(billing_case, apply_mode):
    case = billing_case
    finalizers = []
    class Borrowed(Session):
        def commit(self):
            finalizers.append('commit')
            return super().commit()
        def rollback(self):
            finalizers.append('rollback')
            return super().rollback()
        def close(self):
            finalizers.append('close')
            return super().close()
        def invalidate(self):
            finalizers.append('invalidate')
            return super().invalidate()
    db = Borrowed(case.engine)
    token = current_tenant.set(case.foreign)
    try:
        marker = 'Synthetic caller-owned PG pending'
        db.execute(update(Usuario).where(Usuario.id == case.foreign).values(nombre=marker))
        reply = billing.run(manifest(case), apply=apply_mode, factory=lambda: db,
            reader_factory=lambda *_: pytest.fail('Borrowed Session reached provider'))
        assert reply['unconfirmed'] == 1 and not reply['complete'] and reply['next_cursor']
        assert db.in_transaction() and finalizers == [] and current_tenant.get() == case.foreign
        assert db.scalar(select(Usuario.nombre).where(Usuario.id == case.foreign)) == marker
    finally:
        db.rollback()
        db.close()
        current_tenant.reset(token)


def test_r07_global_inventory_is_repeatable_read_readonly_and_not_tenant_partial(object_case):
    case = object_case
    with Session(case.engine) as db:
        db.add(PlanGenerado(gym_id=case.foreign, id_cliente=case.foreign_client, ruta_pdf=str(case.original)))
        db.commit()
        expected = db.scalar(select(text('count(*)')).select_from(PlanGenerado))
    output = case.private / 'global-snapshot.jsonl'
    with inventory.readonly_inventory_connection(case.engine) as connection:
        assert connection.scalar(text('SHOW transaction_isolation')) == 'repeatable read'
        assert connection.scalar(text('SHOW transaction_read_only')) == 'on'
        summary = inventory.write_inventory(connection, case.roots, output, page_size=1)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    selected = [row for row in rows if row.get('record') == 'entry' and row.get('tenant_id') in {case.subject, case.foreign}]
    assert summary['scanned_rows'] >= expected and {row['tenant_id'] for row in selected} == {case.subject, case.foreign}
    assert all('ambiguous_path' in row['issues'] for row in selected) and rows[-1]['complete'] is True
    record('r07-global-snapshot', {'scanned_at_least_all_plans': True, 'selected_tenants': 2,
        'isolation': 'repeatable read', 'read_only': True, 'partial_inventory_never_accepted': True})


def test_r07_restricted_app_cannot_substitute_global_operator_or_inventory(object_case, monkeypatch):
    case = object_case
    output = case.private / 'denied-partial.jsonl'
    with Session(case.app) as db:
        assert db.scalars(select(PlanGenerado).where(PlanGenerado.id == case.row_id)).all() == []
    with tenant_scope(case.subject), Session(case.app) as db:
        assert db.scalar(select(PlanGenerado.id).where(PlanGenerado.id == case.row_id)) == case.row_id
    with tenant_scope(case.foreign), Session(case.app) as db:
        assert db.scalars(select(PlanGenerado).where(PlanGenerado.id == case.row_id)).all() == []
    with pytest.raises(inventory.InventoryError, match='global_visibility_required'), inventory.readonly_inventory_connection(case.app) as connection:
        inventory.write_inventory(connection, case.roots, output)
    assert not output.exists()
    writes = []
    def observer(_connection, _cursor, sql, *_args):
        if sql.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}:
            writes.append(sql)
    monkeypatch.setattr(case.store, 'put', lambda *_a, **_k: pytest.fail('Restricted app reached PUT'))
    event.listen(case.app, 'before_cursor_execute', observer)
    try:
        with pytest.raises(objects.ApplyError, match='operational_global_role_required'):
            objects.run(case.app, case.bundle, approval=case.approval, journal=case.journal, store=case.store)
    finally:
        event.remove(case.app, 'before_cursor_execute', observer)
    assert writes == []
    # Existing product enters the private Journal before checking its DB role.
    # A header may be durable; it must not become a planned descriptor or ACK.
    if case.journal.exists():
        assert [json.loads(line)['data']['event'] for line in case.journal.read_text().splitlines()] == ['header']
    assert object_status(case) == (None, [], 0) and case.original.read_bytes() == case.data
    record('r07-approle-denied', {'inventory_output_absent': True, 'PUT': 0, 'business_DML': 0,
        'planned_or_reference_ACK': 0, 'private_journal_header_may_precede_role_check': True})


def test_r07_local_apply_uses_real_row_locks_CAS_and_idempotent_receipts(object_case):
    case = object_case
    statements = []
    def observer(_connection, _cursor, sql, *_args):
        statements.append(sql)
    event.listen(case.engine, 'before_cursor_execute', observer)
    try:
        assert execute(case)['applied'] == 1
        first = object_status(case)
        assert execute(case)['applied'] == 1 and object_status(case) == first
    finally:
        event.remove(case.engine, 'before_cursor_execute', observer)
    assert first[0] is not None and first[1] == [(first[0], 'ready')] and first[2] == 0
    assert any('FOR UPDATE OF planes_generados' in sql for sql in statements)
    cas = [sql for sql in statements if sql.lstrip().startswith('UPDATE planes_generados SET')]
    assert len(cas) == 1 and 'pdf_object_id IS NULL' in cas[0] and 'EXISTS' in cas[0]
    rows = [json.loads(line)['data'] for line in case.journal.read_text().splitlines()]
    assert len([row for row in rows if row['event'] == 'planned']) == 1
    assert case.store.read(objects.ObjectDescriptor(**next(row['descriptor'] for row in rows if row['event'] == 'planned')),
        owner_id=case.subject) == case.data
    assert case.original.read_bytes() == case.data
    record('r07-lock-CAS', {'real_SQL': cas, 'row_lock_seen': True, 'same_descriptor_on_replay': True,
        'source_read_only': True, 'quota_unchanged': True})


@pytest.mark.parametrize('published', [False, True], ids=['before-publish', 'after-publish'])
def test_r07_uncertain_local_PUT_remains_pending_and_reuses_original_key(object_case, monkeypatch, published):
    case = object_case
    put = case.store.put
    seen = []
    def uncertain(descriptor, data, **kwargs):
        seen.append(descriptor)
        assert object_status(case) == (None, [(descriptor.id, 'pending')], 0)
        if published:
            put(descriptor, data, **kwargs)
        raise ObjectUnavailable('synthetic-local-PUT-uncertainty')
    monkeypatch.setattr(case.store, 'put', uncertain)
    with pytest.raises(ObjectUnavailable):
        execute(case)
    assert object_status(case) == (None, [(seen[0].id, 'pending')], 0)
    monkeypatch.setattr(case.store, 'put', put)
    assert execute(case)['applied'] == 1 and object_status(case)[0] == seen[0].id


def test_r07_hash_valid_foreign_descriptor_cannot_gain_tenant_reference(object_case):
    case = object_case
    foreign = describe(case.foreign, 'plan_pdf', case.data, 'application/pdf')
    with objects.Journal(case.journal, case.bundle.binding) as journal:
        journal.append({'event': 'planned', 'entry_sha256': objects.entry_key(case.bundle.selected[0]),
            'descriptor': asdict(foreign)})
    before = case.journal.read_bytes()
    with pytest.raises(ObjectAccessDenied):
        execute(case)
    assert object_status(case) == (None, [], 0) and case.journal.read_bytes() == before


@pytest.mark.parametrize('drift', ['owner', 'client'], ids=['owner', 'client'])
def test_r07_canonical_drift_during_PUT_does_not_attach_published_object(object_case, monkeypatch, drift):
    case = object_case
    put = case.store.put
    def changed(*args, **kwargs):
        put(*args, **kwargs)
        with Session(case.engine) as db:
            if drift == 'owner':
                db.get(Usuario, case.subject).deleted_at = datetime.now(UTC)
            else:
                db.scalar(select(Cliente).where(Cliente.id_cliente == case.client)).gym_id = case.foreign
            db.commit()
    monkeypatch.setattr(case.store, 'put', changed)
    with pytest.raises(objects.ApplyError):
        execute(case)
    first = object_status(case)
    assert first[0] is None and len(first[1]) == 1 and first[1][0][1] == 'pending' and first[2] == 0
    assert case.original.read_bytes() == case.data


def test_r07_reference_commit_ACK_loss_reconciles_existing_ready_object(object_case, monkeypatch):
    case = object_case
    append = objects.Journal.append
    def lost(journal, data):
        if data['event'] == 'reference_committed':
            raise OSError('synthetic-after-reference-COMMIT-ACK-loss')
        return append(journal, data)
    monkeypatch.setattr(objects.Journal, 'append', lost)
    with pytest.raises(OSError):
        execute(case)
    first = object_status(case)
    assert first[0] == first[1][0][0] and first[1][0][1] == 'ready' and first[2] == 0
    monkeypatch.setattr(objects.Journal, 'append', append)
    assert execute(case)['applied'] == 1 and object_status(case) == first


def test_r07_changed_source_capability_rejects_before_any_SQL_or_journal(object_case, monkeypatch):
    case = object_case
    baseline = case.bundle.source_check()
    monkeypatch.setattr(case.bundle, 'source_check', lambda: {**baseline, 'commit': '0' * 40})
    sql = []
    def observer(*_args):
        sql.append(True)
    event.listen(case.engine, 'before_cursor_execute', observer)
    try:
        with pytest.raises(objects.ApplyError, match='artifact_binding_changed'):
            execute(case)
    finally:
        event.remove(case.engine, 'before_cursor_execute', observer)
    assert not sql and not case.journal.exists() and case.original.read_bytes() == case.data
