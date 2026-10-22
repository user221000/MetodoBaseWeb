"""Synthetic operator apply against a real migrated37 SQLite copy, no provider."""
import inspect
import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from tests import account_security37_fixtures
from web.database.models import (
    Cliente,
    GymProfile,
    PlanGenerado,
    StoredObject,
    UserRole,
    Usuario,
)
from web.database.tenant_context import tenant_scope
from web.services import legacy_object_apply as service
from web.services import legacy_object_inventory as inventory
from web.storage.configuration import ObjectStoreConfiguration
from web.storage.local import LocalObjectStore
from web.storage.objects import ObjectUnavailable

account37_engine = account_security37_fixtures.account37_engine


@pytest.fixture
def case(account37_engine, tmp_path):
    from web.services.legacy_object_apply_boundary import create_private_directory
    source = tmp_path / 'current37.db'
    shutil.copyfile(account37_engine.url.database, source)
    engine = create_engine('sqlite:///' + source.as_posix())
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _record):
        connection.execute('PRAGMA foreign_keys=ON')
    with Session(engine) as db:
        for suffix in ('a', 'b'):
            db.add(Usuario(id='apply-' + suffix, email='apply-' + suffix + '@example.invalid', nombre='Synthetic',
                password_hash='unused-no-login', tipo='gym', role=UserRole.OWNER))
        db.flush()
        for suffix in ('a', 'b'):
            db.add(Cliente(id_cliente='client-' + suffix, gym_id='apply-' + suffix, nombre='Synthetic'))
        db.commit()
    pdf, logo = tmp_path / 'private-pdf', tmp_path / 'old/web/static/uploads/logos'
    pdf.mkdir()
    logo.mkdir(parents=True)
    data = b'%PDF-inert-migration-only-1234567'
    original = pdf / 'inert.pdf'
    original.write_bytes(data)
    with Session(engine) as db:
        row = PlanGenerado(gym_id='apply-a', id_cliente='client-a', ruta_pdf=str(original))
        db.add(row)
        db.flush()
        row_id = row.id
        db.commit()
    private = create_private_directory(tmp_path / 'private')
    roots = inventory.InventoryRoots(pdf, logo)
    inv = private / 'inventory.jsonl'
    with inventory.readonly_inventory_connection(engine) as connection:
        inventory.write_inventory(connection, roots, inv)
    records = [json.loads(line) for line in inv.read_text(encoding='utf8').splitlines()]
    configuration = ObjectStoreConfiguration(backend='local', local_root=tmp_path / 'objects')
    manifest = private / 'mapping.json'
    manifest.write_bytes(service.canonical({'format': 1, 'inventory_sha256': service.digest(inv.read_bytes()),
        'source': service.source_binding(), 'destination_sha256': service.destination_binding(configuration),
        'entries': [{'entry_sha256': service.entry_key(entry), 'apply': True,
            'provenance_reference': 'synthetic-generated-here-not-an-operational-approval'} for entry in records[1:-1]]}))
    manifest.chmod(0o600)
    bundle = service.Bundle(manifest, inv, roots, configuration)
    now = datetime.now(UTC)
    approval = private / 'approval.json'
    approval.write_bytes(service.canonical({'approved': True, 'binding': bundle.binding,
        'entries': [service.entry_key(entry) for entry in bundle.selected], 'issued_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=1)).isoformat(),
        'quiescence_reference': 'synthetic-single-test-writer-not-production-attestation'}))
    approval.chmod(0o600)
    value = SimpleNamespace(engine=engine, bundle=bundle, approval=approval, journal=private / 'journal.jsonl',
        store=LocalObjectStore(configuration.local_root), original=original, data=data, row_id=row_id, private=private,
        manifest=manifest, inv=inv, roots=roots, configuration=configuration, now=now)
    try:
        yield value
    finally:
        engine.dispose()


def execute(case, **changes):
    options = {'approval': case.approval, 'journal': case.journal, 'store': case.store, **changes}
    return service.run(case.engine, case.bundle, **options)


def status(case):
    with Session(case.engine) as db:
        return (db.get(PlanGenerado, case.row_id).pdf_object_id,
            [(row.id, row.status) for row in db.scalars(select(StoredObject))],
            db.scalar(select(Cliente).where(Cliente.id_cliente == 'client-a')).total_planes_generados)


def test_plan_has_no_DML_no_journal_and_no_provider_call(case, monkeypatch):
    statements = []
    event.listen(case.engine, 'before_cursor_execute', lambda _c, _u, sql, *_args: statements.append(sql.split()[0].upper()))
    monkeypatch.setattr(case.store, 'put', lambda *_a, **_k: pytest.fail('plan PUT'))
    assert service.run(case.engine, case.bundle) == {'complete': True, 'mode': 'plan', 'eligible': 1, 'applied': 0}
    assert not set(statements) & {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}
    assert not case.journal.exists() and status(case) == (None, [], 0)
    assert case.original.read_bytes() == case.data


def test_apply_is_atomic_idempotent_same_descriptor_and_never_changes_original_or_quota(case):
    assert execute(case)['applied'] == 1
    first = status(case)
    assert first[0] is not None and first[1] == [(first[0], 'ready')] and first[2] == 0
    assert execute(case)['applied'] == 1 and status(case) == first
    planned = [json.loads(line)['data'] for line in case.journal.read_text().splitlines()
        if json.loads(line)['data']['event'] == 'planned']
    assert len(planned) == 1 and planned[0]['descriptor']['id'] == first[0]
    assert case.original.read_bytes() == case.data


@pytest.mark.parametrize('published', [False, True])
def test_uncertain_PUT_resumes_same_key_without_association_or_refund(case, monkeypatch, published):
    original = case.store.put
    seen = []
    def uncertain(descriptor, data, **kwargs):
        seen.append(descriptor)
        assert status(case)[1] == [(descriptor.id, 'pending')]
        if published:
            original(descriptor, data, **kwargs)
        raise ObjectUnavailable('inert-uncertain-PUT')
    monkeypatch.setattr(case.store, 'put', uncertain)
    with pytest.raises(ObjectUnavailable):
        execute(case)
    assert status(case) == (None, [(seen[0].id, 'pending')], 0)
    monkeypatch.setattr(case.store, 'put', original)
    assert execute(case)['applied'] == 1 and status(case)[0] == seen[0].id


def test_after_commit_response_loss_reconciles_current_reference_not_a_new_object(case, monkeypatch):
    original = service.Journal.append
    def lose_ack(journal, data):
        if data['event'] == 'reference_committed':
            raise OSError('inert-after-commit-ACK-loss')
        return original(journal, data)
    monkeypatch.setattr(service.Journal, 'append', lose_ack)
    with pytest.raises(OSError):
        execute(case)
    first = status(case)
    assert first[0] == first[1][0][0] and first[1][0][1] == 'ready'
    monkeypatch.setattr(service.Journal, 'append', original)
    assert execute(case)['applied'] == 1 and status(case) == first


@pytest.mark.parametrize('change', ['owner', 'client', 'legacy', 'deleted', 'duplicate'])
def test_persisted_or_global_reference_drift_refuses_before_PUT(case, monkeypatch, change):
    with Session(case.engine) as db:
        row = db.get(PlanGenerado, case.row_id)
        if change == 'owner':
            db.get(Usuario, 'apply-a').activo = False
        elif change == 'client':
            row.id_cliente = 'client-b'
        elif change == 'legacy':
            row.ruta_pdf = str(case.original) + '.different'
        elif change == 'deleted':
            row.deleted_at = datetime.now(UTC)
        else:
            db.add(PlanGenerado(gym_id='apply-b', id_cliente='client-b', ruta_pdf=str(case.original)))
        db.commit()
    monkeypatch.setattr(case.store, 'put', lambda *_a, **_k: pytest.fail('drift PUT'))
    with pytest.raises(service.ApplyError):
        execute(case)
    assert status(case)[0] is None and status(case)[1] == []


@pytest.mark.parametrize('change', ['manifest', 'approval', 'source', 'configuration', 'expired', 'too-long', 'missing'])
def test_admission_mutation_refuses_before_SQL_or_journal(case, monkeypatch, change):
    if change == 'manifest':
        case.manifest.write_bytes(case.manifest.read_bytes() + b' ')
    elif change == 'approval':
        value = json.loads(case.approval.read_bytes())
        value['approved'] = 1
        case.approval.write_bytes(service.canonical(value))
    elif change == 'source':
        monkeypatch.setattr(service, 'source_binding', lambda: {'commit': 'changed', 'files_sha256': 'changed'})
    elif change == 'configuration':
        object.__setattr__(case.configuration, 'local_root', case.private / 'changed')
    elif change == 'missing':
        case.approval.unlink()
    else:
        value = json.loads(case.approval.read_bytes())
        value['expires_at'] = (case.now + timedelta(hours=5) if change == 'too-long' else case.now).isoformat()
        case.approval.write_bytes(service.canonical(value))
    statements = []
    event.listen(case.engine, 'before_cursor_execute', lambda *_args: statements.append(True))
    with pytest.raises((service.ApplyError, OSError)):
        execute(case)
    assert statements == [] and not case.journal.exists()


def test_lease_expiring_during_PUT_rolls_back_attachment_but_permits_context_cleanup(case, monkeypatch):
    now = [case.now]
    original = case.store.put
    def expire(*args, **kwargs):
        original(*args, **kwargs)
        now[0] += timedelta(hours=2)
    monkeypatch.setattr(case.store, 'put', expire)
    with pytest.raises(service.ApplyError, match='finite_window_required'):
        execute(case, clock=lambda: now[0])
    assert status(case)[0] is None and status(case)[1][0][1] == 'pending'
    monkeypatch.setattr(case.store, 'put', original)
    assert execute(case)['applied'] == 1


def test_destination_changed_bytes_never_attach_or_overwrite_existing_object(case, monkeypatch):
    original = case.store.put
    def publish_wrong(descriptor, data, **kwargs):
        original(descriptor, data, **kwargs)
        (case.store.root / descriptor.key).write_bytes(b'different')
    monkeypatch.setattr(case.store, 'put', publish_wrong)
    with pytest.raises(ObjectUnavailable):
        execute(case)
    monkeypatch.setattr(case.store, 'put', original)
    with pytest.raises(ObjectUnavailable):
        execute(case)
    assert status(case)[0] is None and status(case)[1][0][1] == 'pending'


def test_source_drift_during_PUT_refuses_ready_and_keeps_original_as_changed_by_writer(case, monkeypatch):
    original = case.store.put
    def drift(*args, **kwargs):
        original(*args, **kwargs)
        case.original.write_bytes(b'%PDF-inert-concurrent-writer')
    monkeypatch.setattr(case.store, 'put', drift)
    with pytest.raises(service.ApplyError, match='source_file_changed'):
        execute(case)
    assert status(case)[0] is None and status(case)[1][0][1] == 'pending'


def test_journal_chain_damage_and_exclusive_second_operator_refuse(case):
    with (service.Journal(case.journal, case.bundle.binding), pytest.raises((OSError, service.ApplyError)),
            service.Journal(case.journal, case.bundle.binding)):
        pytest.fail('second journal owner')
    raw = bytearray(case.journal.read_bytes())
    raw[25] ^= 1
    case.journal.write_bytes(raw)
    with pytest.raises((service.ApplyError, ValueError)):
        execute(case)
    assert status(case) == (None, [], 0)


def test_request_tenant_cannot_adopt_operator_authority(case):
    with tenant_scope('apply-b'), pytest.raises(service.ApplyError, match='operator_context_required'):
        execute(case)
    assert status(case) == (None, [], 0)


def test_entry_and_file_budgets_and_incomplete_inventory_fail_before_database(case):
    mapping = json.loads(case.manifest.read_bytes())
    mapping['entries'] *= 101
    case.manifest.write_bytes(service.canonical(mapping))
    with pytest.raises(service.ApplyError):
        service.Bundle(case.manifest, case.inv, case.roots, case.configuration)
    case.manifest.write_bytes(b'x' * (service.MAX_DOCUMENT + 1))
    with pytest.raises(service.ApplyError, match='artifact_budget_exceeded'):
        service.Bundle(case.manifest, case.inv, case.roots, case.configuration)
    assert status(case) == (None, [], 0)


def test_CLI_fixed_opaque_error_never_reflects_arguments_or_inherited_application_URL(case, monkeypatch, capsys):
    from scripts.apply_legacy_objects import main
    monkeypatch.setenv('DATABASE_URL', 'not-an-authorized-apply-destination')
    marker = 'inert-private-argument-not-for-output'
    assert main(['--unknown-' + marker]) == 2
    result = capsys.readouterr()
    assert result.out == '' and marker not in result.err
    assert json.loads(result.err) == {'complete': False, 'status': 503, 'code': 'legacy_apply_unavailable'}
    assert status(case) == (None, [], 0)


def test_ready_and_reference_rollback_together_on_failure_inside_final_transaction(case, monkeypatch):
    original = service._attach
    def refuse(*args):
        original(*args)
        raise ObjectUnavailable('inert-before-final-commit')
    monkeypatch.setattr(service, '_attach', refuse)
    with pytest.raises(ObjectUnavailable):
        execute(case)
    assert status(case)[0] is None and status(case)[1][0][1] == 'pending'
    monkeypatch.setattr(service, '_attach', original)
    assert execute(case)['applied'] == 1


def test_foreign_owner_pending_metadata_is_not_adopted_or_overwritten(case, monkeypatch):
    original = case.store.put
    monkeypatch.setattr(case.store, 'put', lambda *_a, **_k: (_ for _ in ()).throw(ObjectUnavailable()))
    with pytest.raises(ObjectUnavailable):
        execute(case)
    with Session(case.engine) as db:
        db.scalar(select(StoredObject)).gym_id = 'apply-b'
        db.commit()
    monkeypatch.setattr(case.store, 'put', original)
    with pytest.raises(service.ApplyError, match='pending_descriptor_changed'):
        execute(case)
    with Session(case.engine) as db:
        assert db.scalar(select(StoredObject)).gym_id == 'apply-b'
    assert status(case)[0] is None


def test_private_boundary_precedes_payload_and_rejects_extra_principals_or_public_mode(tmp_path):
    from web.services import legacy_object_apply_boundary as boundary
    private = boundary.create_private_directory(tmp_path / 'guarded')
    assert list(private.iterdir()) == []
    boundary.verify(private, directory=True)
    if os.name == 'nt':
        source = inspect.getsource(boundary._windows)
        assert source.count('(A;OICI;FA;;;SY)') == 1
        source = source.replace('(A;OICI;FA;;;SY)', '(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)')
        scope = {name: getattr(boundary, name) for name in ('csv', 'io', 'subprocess')}
        exec(compile(source, '<synthetic-third-ACE>', 'exec'), scope)
        with pytest.raises(OSError):
            scope['_windows'](private, create=True)
    else:
        private.chmod(0o755)
    with pytest.raises(OSError):
        boundary.verify(private, directory=True)


def test_logo_reencoding_keeps_source_digest_separate_and_preserves_business_timestamp(case):
    from io import BytesIO

    from PIL import Image, PngImagePlugin
    target = case.roots.logo / 'brand.png'
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('Synthetic-private-comment', 'not-for-normalized-output')
    stream = BytesIO()
    Image.new('RGB', (4, 4), 'red').save(stream, format='PNG', pnginfo=metadata)
    target.write_bytes(stream.getvalue())
    with Session(case.engine) as db:
        profile = GymProfile(gym_id='apply-a', logo_url='/static/uploads/logos/brand.png')
        db.add(profile)
        db.flush()
        profile_id, stamp = profile.id, profile.updated_at
        db.commit()
    case.inv.unlink()
    with inventory.readonly_inventory_connection(case.engine) as connection:
        inventory.write_inventory(connection, case.roots, case.inv)
    records = [json.loads(line) for line in case.inv.read_text(encoding='utf8').splitlines()]
    mapping = json.loads(case.manifest.read_bytes())
    mapping['inventory_sha256'] = service.digest(case.inv.read_bytes())
    mapping['entries'] = [{'entry_sha256': service.entry_key(entry), 'apply': True,
        'provenance_reference': 'synthetic-logo-created-in-this-test'} for entry in records[1:-1]]
    case.manifest.write_bytes(service.canonical(mapping))
    case.bundle = service.Bundle(case.manifest, case.inv, case.roots, case.configuration)
    approval = json.loads(case.approval.read_bytes())
    approval.update(binding=case.bundle.binding, entries=[service.entry_key(entry) for entry in case.bundle.selected])
    case.approval.write_bytes(service.canonical(approval))
    assert execute(case)['applied'] == 2
    with Session(case.engine) as db:
        profile = db.get(GymProfile, profile_id)
        assert profile.updated_at == stamp
        stored = db.get(StoredObject, profile.logo_object_id)
        assert stored.sha256 != service.digest(target.read_bytes()) and stored.status == 'ready'
    assert target.read_bytes() == stream.getvalue()
    assert execute(case)['applied'] == 2


def test_CLI_actual_plan_then_apply_and_replay_use_explicit_DB_and_private_storage(case, monkeypatch, capsys):
    from scripts.apply_legacy_objects import main
    storage = case.private / 'storage.json'
    storage.write_bytes(service.canonical({'backend': 'local', 'local_root': str(case.configuration.local_root)}))
    storage.chmod(0o600)
    monkeypatch.setenv('LEGACY_APPLY_DATABASE_URL', str(case.engine.url))
    args = ['--manifest', str(case.manifest), '--inventory', str(case.inv), '--storage', str(storage),
        '--pdf-root', str(case.roots.pdf), '--logo-root', str(case.roots.logo),
        '--expected-database', str(case.engine.url.database)]
    assert main(args) == 0
    result = capsys.readouterr()
    assert json.loads(result.out)['mode'] == 'plan' and result.err == '' and status(case) == (None, [], 0)
    assert main([*args, '--apply', '--approval', str(case.approval), '--journal', str(case.journal)]) == 0
    assert json.loads(capsys.readouterr().out)['applied'] == 1
    first = status(case)
    assert main([*args, '--apply', '--approval', str(case.approval), '--journal', str(case.journal)]) == 0
    assert json.loads(capsys.readouterr().out)['applied'] == 1 and status(case) == first
