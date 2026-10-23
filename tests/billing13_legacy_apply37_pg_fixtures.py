"""Current37 PG companions: one owned UUID, normal app Session, explicit operator.

Import is inert. Root source/profile/generation ACK is checked before connecting.
Seed and observation use the existing migrator; only R07 uses that role as SUT.
"""
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests import test_billing_reconciliation13 as original_billing
from tests.account37_qa_pg_fixtures import assert_blank_pool, witness
from tests.billing13_legacy_apply37_pg_contract import private_workspace
from web.database.models import (
    Cliente,
    PlanGenerado,
    PurchaseIntent,
    Subscription,
    UserRole,
    UserSubscription,
    Usuario,
)
from web.database.tenant_context import current_tenant
from web.services import legacy_object_apply as objects
from web.services import legacy_object_inventory as inventory
from web.services.billing_integrity import current_quota_period, price_in_cents
from web.services.legacy_object_apply_boundary import create_private_directory
from web.storage.configuration import ObjectStoreConfiguration
from web.storage.local import LocalObjectStore

ProviderFacts = original_billing.ProviderFacts
manifest = original_billing.manifest


def record(name, value):
    root = Path(os.environ['B13_R07_PG_PRIVATE']).resolve(strict=True)
    assert root.is_relative_to(private_workspace())
    target = root / 'witnesses'
    with (target / (name + '-' + uuid.uuid4().hex + '.json')).open('x', encoding='utf8') as stream:
        json.dump(value, stream, default=str, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


@pytest.fixture(scope='session')
def database_schema():
    """Override unrelated root SQLite bootstrap: this phase owns its PG only."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    """No unrelated default-DB cleanup; every companion seeds unique UUID rows."""
    yield


@pytest.fixture(scope='module')
def pg37(tmp_path_factory):
    from tests.ci_web37.pg_close import owned_database
    from tests.billing13_legacy_apply37_pg_contract import (
        check_generation,
        checked_runtime,
    )
    from tests.billing13_legacy_apply37_pg_generation import creation_generation_guard
    from tests.integration_provider_subjects import application_engine
    from tests.integration_schema_migrations import run_migration
    contract, profile = checked_runtime()
    os.environ.update(profile)
    check_generation(contract, profile)  # First SQL; fresh Root ACK required above.
    with creation_generation_guard(contract, profile), owned_database('postgresql', tmp_path_factory.mktemp('billing13-objects37')) as (url, admin):
        check_generation(contract, profile, engine=admin)
        run_migration(url, 'db_bootstrap.py', '--revision', '20261020_account_security')
        app = application_engine(url, admin)
        try:
            record('schema-role-pool', witness(app))
            with admin.connect() as connection:
                from sqlalchemy import text
                flags = tuple(connection.execute(text('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user')).one())
                assert any(flags), 'R07 requires the existing explicit global operator, never app privilege escalation'
                record('existing-operator', {'global_visibility': True, 'role_flags': flags, 'pool': 1})
            yield SimpleNamespace(admin=admin, app=app, contract=contract)
        finally:
            app.dispose()


@pytest.fixture(autouse=True)
def released(pg37):
    yield
    assert current_tenant.get() == ''
    assert_blank_pool(pg37.app)
    assert pg37.admin.pool.checkedout() == 0


def seed_billing(pg37, *, provider='stripe'):
    subject, foreign, intent = (str(uuid.uuid4()) for _ in range(3))
    amount = price_in_cents('pro_usuario')
    with Session(pg37.admin) as db:
        for identity in (subject, foreign):
            db.add(Usuario(id=identity, email=uuid.uuid4().hex + '@example.invalid', nombre='Synthetic PG B13',
                password_hash='unused-not-a-login', tipo='usuario', role=UserRole.VIEWER))
        db.flush()
        db.add(UserSubscription(user_id=subject, plan='starter', status='active', max_planes_mes=1,
            planes_usados_mes=1, mes_actual=current_quota_period()))
        purchase = PurchaseIntent(id=intent, subject_id=subject, provider=provider,
            operation='preference' if provider == 'mercadopago' else 'elements', plan='pro_usuario',
            amount_cents=amount, currency='mxn', request_key=uuid.uuid4().hex, status='provider_created',
            provider_reference_id=('pref_' if provider == 'mercadopago' else 'sub_') + uuid.uuid4().hex,
            provider_customer_id='cus_' + uuid.uuid4().hex)
        payment = str(int(uuid.uuid4().hex[:12], 16))
        db.add(purchase)
        row = Subscription(gym_id=subject, plan='pro_usuario', provider=provider, status='incomplete',
            stripe_subscription_id=purchase.provider_reference_id if provider == 'stripe' else None,
            stripe_customer_id=purchase.provider_customer_id if provider == 'stripe' else None,
            provider_payment_id=payment if provider == 'mercadopago' else None)
        db.add(row)
        db.flush()
        subscription, reference, customer = row.id, purchase.provider_reference_id, purchase.provider_customer_id
        db.commit()
    return SimpleNamespace(engine=pg37.app, admin=pg37.admin,
        factory=sessionmaker(bind=pg37.app, expire_on_commit=True, autoflush=False),
        oracle_factory=sessionmaker(bind=pg37.admin), subject=subject, foreign=foreign, intent=intent,
        subscription=subscription, reference=reference, customer=customer, amount=amount, payment=payment)


def billing_facts(case):
    """Literal original business oracle, explicitly transported to admin only."""
    oracle = SimpleNamespace(**{**vars(case), 'factory': case.oracle_factory})
    return original_billing.facts(oracle)


@pytest.fixture
def billing_case(pg37):
    return seed_billing(pg37)


@pytest.fixture
def object_case(pg37, tmp_path):
    from scripts.apply_legacy_objects import source_check
    assert tmp_path.resolve().is_relative_to(private_workspace())
    subject, foreign, client, foreign_client = (str(uuid.uuid4()) for _ in range(4))
    with Session(pg37.admin) as db:
        for identity in (subject, foreign):
            db.add(Usuario(id=identity, email=uuid.uuid4().hex + '@example.invalid', nombre='Synthetic PG R07',
                password_hash='unused-not-a-login', tipo='gym', role=UserRole.OWNER))
        db.flush()
        db.add_all([Cliente(id_cliente=client, gym_id=subject, nombre='Synthetic'),
                    Cliente(id_cliente=foreign_client, gym_id=foreign, nombre='Synthetic')])
        db.commit()
    pdf, logo = tmp_path / 'private-pdf', tmp_path / 'old/web/static/uploads/logos'
    pdf.mkdir()
    logo.mkdir(parents=True)
    data = b'%PDF-inert-PG-companion-only-1234567'
    original = pdf / 'inert.pdf'
    original.write_bytes(data)
    with Session(pg37.admin) as db:
        row = PlanGenerado(gym_id=subject, id_cliente=client, ruta_pdf=str(original))
        db.add(row)
        db.flush()
        row_id = row.id
        db.commit()
    private = create_private_directory(tmp_path / 'private')
    roots = inventory.InventoryRoots(pdf, logo)
    inv = private / 'inventory.jsonl'
    with inventory.readonly_inventory_connection(pg37.admin) as connection:
        inventory.write_inventory(connection, roots, inv)
    records = [json.loads(line) for line in inv.read_text(encoding='utf8').splitlines()]
    configuration = ObjectStoreConfiguration(backend='local', local_root=tmp_path / 'objects')
    mapping = private / 'mapping.json'
    write_private(mapping, objects.canonical({'format': 1, 'inventory_sha256': objects.digest(inv.read_bytes()),
        'source': source_check(), 'destination_sha256': objects.destination_binding(configuration),
        'entries': [{'entry_sha256': objects.entry_key(entry),
            'apply': entry['kind'] == 'plan_pdf' and entry['row_id'] == row_id,
            'provenance_reference': 'synthetic-created-in-test-not-real-provenance'} for entry in records[1:-1]]}))
    bundle = objects.Bundle(mapping, inv, roots, configuration, source_check=source_check)
    now = datetime.now(UTC)
    approval = private / 'approval.json'
    write_private(approval, objects.canonical({'approved': True, 'binding': bundle.binding,
        'entries': [objects.entry_key(entry) for entry in bundle.selected], 'issued_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=1)).isoformat(),
        'quiescence_reference': 'synthetic-single-writer-not-a-real-maintenance-attestation'}))
    assert len(bundle.selected) == 1
    return SimpleNamespace(engine=pg37.admin, app=pg37.app, bundle=bundle, approval=approval,
        journal=private / 'journal.jsonl', store=LocalObjectStore(configuration.local_root),
        original=original, data=data, row_id=row_id, subject=subject, foreign=foreign,
        client=client, foreign_client=foreign_client, private=private, inv=inv, roots=roots)


def execute(case, **changes):
    return objects.run(case.engine, case.bundle, approval=case.approval,
        journal=case.journal, store=case.store, **changes)


def object_status(case):
    from web.database.models import StoredObject
    with Session(case.engine) as db:
        return (db.get(PlanGenerado, case.row_id).pdf_object_id,
            [(row.id, row.status) for row in db.scalars(select(StoredObject).where(StoredObject.gym_id == case.subject))],
            db.scalar(select(Cliente).where(Cliente.id_cliente == case.client)).total_planes_generados)


def write_private(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
