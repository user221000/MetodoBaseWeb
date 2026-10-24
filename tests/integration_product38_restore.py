"""New38 facts restore: two sequential UUIDs, genuine target and two tenants.

This extends schema coverage, not the prior retained37 kit or its custody/RPO
claims. Uses the unchanged backup core, a synthetic encryption key and local
private objects. No product backup implementation is replaced.
"""
import base64
import os
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.account37_qa_restore_helpers import private_backup_temporaries
from tests.ci_web38.pg_fixtures import (database_schema, isolated_database, pg38_runtime)  # noqa: F401
from tests.ci_web38.pg_physical import physical_contract
from tests.ci_web38.pg_tools import observe_restore_tools
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from scripts.backup_restore import create_backup, restore_backup, verified_artifacts
from web.database.models import Cliente, PlanGenerado, ProductAnalyticsFact as Fact, Usuario, UserRole
from web.database.repository import registrar_plan
from web.database.tenant_context import tenant_scope
from web.services.product_analytics_v2 import origin
from web.storage.local import LocalObjectStore
from web.storage.objects import ObjectAccessDenied, describe


def fact_snapshot(engine):
    with Session(engine) as db:
        return [tuple(row) for row in db.execute(select(Fact.id, Fact.owner_id, Fact.context,
            Fact.client_id, Fact.event_type, Fact.source_id, Fact.source_version, Fact.origin,
            Fact.occurred_at).order_by(Fact.id))]


def test_restore38_preserves_two_tenant_origin_plan_snapshots_times_and_RLS(pg38_runtime, tmp_path, monkeypatch):
    private_backup_temporaries(monkeypatch, tmp_path)
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY', base64.b64encode(os.urandom(32)).decode('ascii'))
    roots = (str(uuid.uuid4()), str(uuid.uuid4()))
    clients = (str(uuid.uuid4()), str(uuid.uuid4()))
    objects = LocalObjectStore((tmp_path / 'source-objects').resolve())
    descriptors = []
    for index, owner in enumerate(roots):
        content = b'%PDF-1.7\nSynthetic38-restore-' + str(index).encode()
        descriptor = describe(owner, 'plan_pdf', content, 'application/pdf')
        objects.put(descriptor, content, owner_id=owner)
        descriptors.append((descriptor, content))
    pg_bin = Path(pg38_runtime.profile['METODOBASE_TEST_PG_BIN'])
    with pg38_runtime.database(tmp_path / 'source-lease') as (source_url, admin):
        run_migration(source_url, 'db_bootstrap.py', '--revision', '20261023_product_facts')
        with Session(admin) as db:
            for owner, client in zip(roots, clients):
                db.add(Usuario(id=owner, email=owner + '@example.invalid', password_hash='not-a-login',
                    nombre='Synthetic38', tipo='gym', role=UserRole.OWNER))
                db.flush()
                db.add(Cliente(id_cliente=client, gym_id=owner, nombre='Synthetic38'))
            db.commit()
        source_app = application_engine(source_url, admin)
        try:
            physical_contract(source_app)
            for owner, client, label in zip(roots, clients, ('demo', 'customer')):
                principal = {'id': owner, 'tipo': 'gym', 'role': 'owner',
                             'team_gym_id': None, 'session_version': 0}
                with Session(source_app) as db:
                    origin(db, principal, 'gym', client, value=label, expected_version=0)
                with tenant_scope(owner), Session(source_app) as db:
                    plan_id = registrar_plan(db, owner, client, {'plan_json': '{"synthetic":true}'}, return_id=True)
                    assert type(plan_id) is int
                    db.commit()
            # A later classification must not rewrite the saved plan snapshot.
            principal = {'id': roots[0], 'tipo': 'gym', 'role': 'owner',
                         'team_gym_id': None, 'session_version': 0}
            with Session(source_app) as db:
                origin(db, principal, 'gym', clients[0], value='unknown', expected_version=1)
            expected = fact_snapshot(admin)
            assert len(expected) == 5
            assert {(row[1], row[7]) for row in expected if row[4] == 'plan_saved'} == {(roots[0], 'demo'), (roots[1], 'customer')}
            with observe_restore_tools(pg38_runtime, source_url, admin, source_app, 'source', tmp_path):
                manifest = create_backup(tmp_path / 'encrypted-backup', database_url=source_url,
                    expected_database=urlsplit(source_url).path.lstrip('/'), objects_root=objects.root, pg_bin=pg_bin)
            source_name = urlsplit(source_url).path.lstrip('/')
        finally:
            assert source_app.pool.checkedout() == 0  # e905 validates all lifetimes then disposes.
    # Source commonclose/owned603f has already demanded zero/normal DROP/fresh
    # absence before verify and before a different target UUID can be created.
    assert pg38_runtime.closed == pg38_runtime.created == 1 and pg38_runtime.active == 0
    with verified_artifacts(manifest) as (metadata, artifacts):
        assert metadata['encryption'] == 'AES-256-GCM'
        assert metadata['authentication'] == 'HMAC-SHA256-HKDF-v1'
        assert set(artifacts) == {'postgres', 'objects'}
    with pg38_runtime.database(tmp_path / 'target-lease') as (target_url, admin):
        assert urlsplit(target_url).path.lstrip('/') != source_name
        with observe_restore_tools(pg38_runtime, target_url, admin, None, 'target', tmp_path):
            result = restore_backup(manifest, database_url=target_url,
                expected_database=urlsplit(target_url).path.lstrip('/'),
                objects_destination=tmp_path / 'restored-objects', pg_bin=pg_bin)
        assert result['restored'] == ['objects', 'postgres'] and result['objects'] == 2
        assert fact_snapshot(admin) == expected  # Includes exact original timestamps/IDs/source snapshots.
        app = application_engine(target_url, admin)
        try:
            physical_contract(app)
            with Session(app) as db:
                assert db.scalars(select(Fact.id)).all() == []
            for owner, other in ((roots[0], roots[1]), (roots[1], roots[0])):
                with tenant_scope(owner), Session(app) as db:
                    assert {row.owner_id for row in db.scalars(select(Fact)).all()} == {owner}
                    assert db.scalars(select(Fact).where(Fact.owner_id == other)).all() == []
                    assert len(db.scalars(select(PlanGenerado).where(PlanGenerado.gym_id == owner)).all()) == 1
        finally:
            assert app.pool.checkedout() == 0  # Final generation/loan checks belong to e905.
        restored = LocalObjectStore((tmp_path / 'restored-objects').resolve())
        for descriptor, content in descriptors:
            assert restored.read(descriptor, owner_id=descriptor.owner_id) == content
            other = roots[1] if descriptor.owner_id == roots[0] else roots[0]
            with pytest.raises(ObjectAccessDenied):
                restored.read(descriptor, owner_id=other)
