"""Current41 full-schema synthetic capture/restore on a Root-owned PG18 cluster.

The resource fixture retains its explicit loopback ACK, database/role OIDs and
normal-close guards. No production URL, provider or serving process is used.
"""
import hashlib
import json
import os
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from scripts import backup_capture_s3 as capture
from scripts.backup_restore import restore_backup
from tests import integration_backup_capture_s3_postgres as mechanism
from web.database.alembic.policy_contract_v2 import policy_signatures_equal
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.schema_contract_v2 import schema_signatures_equal
from web.database.schema_control import verify_runtime_schema
from web.storage.objects import describe

REVISION = '20261102_payment_refund_facts'
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def full_databases(tmp_path, monkeypatch):
    # Only omit the minimal illustrative schema. Creation, ownership checks,
    # roles, grants and cleanup execute the independently reviewed fixture.
    with monkeypatch.context() as isolated:
        isolated.setattr(mechanism, 'SCHEMA', 'SELECT 1')
        resources = mechanism.owned_databases.__wrapped__(tmp_path)
        context = next(resources)
        try:
            environment = dict(os.environ, DATABASE_URL=context['source'],
                               METODOBASE_TEST_DATABASE_URL='', PYTHON_DOTENV_DISABLED='1')
            with (tmp_path / 'migration.private.log').open('xb') as stream:
                migrated = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                    'db_bootstrap.py', '--revision', REVISION], cwd=ROOT, env=environment,
                    stdout=stream, stderr=subprocess.STDOUT, timeout=120, check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            assert migrated.returncode == 0, 'Synthetic full-schema migration failed; private log retained'
            yield context
        finally:
            resources.close()


def _database_state(url):
    import psycopg2
    from psycopg2 import sql
    engine = create_engine(make_url(url).set(drivername='postgresql+psycopg2'))
    try:
        verify_runtime_schema(engine)
        with engine.connect() as connection:
            schema = schema_signature(connection)
    finally:
        engine.dispose()
    with closing(psycopg2.connect(url, connect_timeout=5)) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchall() == [(REVISION,)]
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = [row[0] for row in cursor.fetchall()]
        assert 30 < len(tables) < 160
        rows = {}
        for table in tables:
            cursor.execute(sql.SQL("SELECT count(*), COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text, '[]') FROM public.{} t").format(sql.Identifier(table)))
            count, content = cursor.fetchone()
            assert count < 100 and len(content.encode()) < 1024 * 1024
            rows[table] = {'rows': count, 'sha256': hashlib.sha256(content.encode()).hexdigest()}
        cursor.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename")
        sequences = {}
        for name in [row[0] for row in cursor.fetchall()]:
            cursor.execute(sql.SQL('SELECT last_value,is_called FROM public.{}').format(sql.Identifier(name)))
            sequences[name] = cursor.fetchone()
        cursor.execute("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname")
        flags = cursor.fetchall()
        cursor.execute("SELECT tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname")
        policies = cursor.fetchall()
    assert policies and any(enabled and forced for _, enabled, forced in flags)
    return {'schema': schema, 'rows': rows, 'sequences': sequences, 'flags': flags, 'policies': policies}


def _seed(context, store):
    from web.database.models import (
        Cliente,
        GymProfile,
        PlanGenerado,
        StoredObject,
        UserRole,
        Usuario,
    )
    owners = [str(uuid4()), str(uuid4())]
    ready = []
    engine = create_engine(make_url(context['source']).set(drivername='postgresql+psycopg2'))
    try:
        with Session(engine) as database:
            for index, owner in enumerate(owners):
                database.add(Usuario(id=owner, email=f'synthetic-{index}@example.invalid',
                    nombre='Synthetic owner', tipo='gym', role=UserRole.OWNER,
                    password_hash='synthetic-unused-hash', activo=True))
            database.flush()
            for index, owner in enumerate(owners):
                client = str(uuid4())
                database.add(Cliente(id_cliente=client, gym_id=owner, nombre='Synthetic client'))
                payload = ('%PDF SYNTHETIC TENANT ' + str(index)).encode()
                descriptor = describe(owner, 'plan_pdf', payload, 'application/pdf')
                ready.append(descriptor)
                store.contents[descriptor.key] = payload
                database.add(StoredObject(id=descriptor.id, gym_id=owner, kind=descriptor.kind,
                    key=descriptor.key, content_type=descriptor.content_type, byte_size=descriptor.byte_size,
                    sha256=descriptor.sha256, storage_backend='s3', status='ready'))
                database.flush()
                database.add(PlanGenerado(gym_id=owner, id_cliente=client,
                    pdf_object_id=descriptor.id, plan_json='{"synthetic":true}'))
            logo = describe(owners[0], 'gym_logo', b'SYNTHETIC PNG BYTES', 'image/png')
            ready.append(logo)
            store.contents[logo.key] = b'SYNTHETIC PNG BYTES'
            pending = describe(owners[1], 'gym_logo', b'SYNTHETIC NOT COMMITTED BYTES', 'image/png')
            for descriptor, status in [(logo, 'ready'), (pending, 'pending')]:
                database.add(StoredObject(id=descriptor.id, gym_id=descriptor.owner_id, kind=descriptor.kind,
                    key=descriptor.key, content_type=descriptor.content_type, byte_size=descriptor.byte_size,
                    sha256=descriptor.sha256, storage_backend='s3', status=status))
            database.flush()
            database.add(GymProfile(gym_id=owners[0], nombre_negocio='Synthetic gym', logo_object_id=logo.id))
            database.commit()
    finally:
        engine.dispose()
    return owners, ready, pending


def _verify_restricted_restore(context, owners):
    import psycopg2
    from psycopg2 import sql
    with closing(psycopg2.connect(context['target'], connect_timeout=5)) as admin, admin, admin.cursor() as cursor:
        # pg_restore intentionally does not recreate deployment credentials or
        # ACLs. Re-establish the already owned restricted runtime role explicitly.
        cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
            sql.Identifier(context['names'][1]), sql.Identifier(context['role'])))
        cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(context['role'])))
        cursor.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(context['role'])))
    parsed = urlsplit(context['restricted_url'])
    url = urlunsplit(parsed._replace(path='/' + context['names'][1]))
    with closing(psycopg2.connect(url, connect_timeout=5)) as restricted, restricted.cursor() as cursor:
        cursor.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')
        assert cursor.fetchone() == (False, False, False, False)
        cursor.execute('SELECT count(*) FROM clientes')
        assert cursor.fetchone() == (0,)
        for owner in owners:
            cursor.execute("SELECT set_config('app.current_tenant',%s,true)", (owner,))
            cursor.execute('SELECT gym_id FROM clientes')
            assert cursor.fetchall() == [(owner,)]
            cursor.execute('SELECT gym_id FROM planes_generados')
            assert cursor.fetchall() == [(owner,)]
        restricted.rollback()
        cursor.execute('SELECT count(*) FROM clientes')
        assert cursor.fetchone() == (0,)


def test_full_current_schema_and_two_tenants_survive_encrypted_capture_restore(full_databases, tmp_path, monkeypatch):
    context = full_databases
    store = mechanism.MemoryS3()
    owners, descriptors, pending = _seed(context, store)
    before = _database_state(context['source'])
    arguments = mechanism._arguments(context, store, monkeypatch)
    arguments['expected_revision'] = REVISION
    report = capture.capture_backup(tmp_path / 'full-capture', **arguments)
    assert report['status'] == 'verified_current_resources'
    assert report['inventory_counts']['ready_objects'] == 3
    assert sorted(store.reads) == sorted(item.key for item in descriptors)
    assert pending.key not in store.reads
    destination = tmp_path / 'full-restored-objects'
    restored = restore_backup(Path(report['manifest']), database_url=context['target'],
        expected_database=context['names'][1], objects_destination=destination, pg_bin=context['pg_bin'])
    assert restored['objects'] == 3
    assert all((destination / item.key).read_bytes() == store.contents[item.key] for item in descriptors)
    assert not (destination / pending.key).exists()
    after = _database_state(context['target'])
    for label, state in [('before', before), ('after', after)]:
        (tmp_path / ('state-' + label + '.private.json')).write_text(json.dumps(state, indent=2), encoding='utf8')
    assert schema_signatures_equal(after['schema'], before['schema'])
    assert policy_signatures_equal(
        {'dialect': 'postgresql', 'policies': [list(row) for row in after['policies']]},
        {'dialect': 'postgresql', 'policies': [list(row) for row in before['policies']]})
    assert {key: value for key, value in after.items() if key not in {'schema', 'policies'}} == {
        key: value for key, value in before.items() if key not in {'schema', 'policies'}}
    _verify_restricted_restore(context, owners)
    (tmp_path / 'full-schema-restore-receipt.json').write_text(json.dumps({
        'accepted': True, 'revision': REVISION, 'synthetic_tenants': 2,
        'complete_schema_contract_equal': True, 'runtime_startup_gate_both_databases': True,
        'existing_v2_cast_comparators': True, 'raw_signatures_equal': after == before,
        'all_table_rows_equal': len(before['rows']),
        'all_sequences_equal': len(before['sequences']), 'all_policies_equal': len(before['policies']),
        'objects_verified': 3, 'pending_metadata_preserved_without_uncommitted_bytes': True,
        'restricted_RLS_after_restore': True, 'explicit_regrant_of_runtime_role': True,
        'provider_operations': 0, 'production_data': False, 'serving': False}), encoding='utf8')
