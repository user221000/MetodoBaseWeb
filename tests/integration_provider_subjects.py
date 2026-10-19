"""Legacy provider identity preparation on real migration paths.

SQLite checks compatibility; PostgreSQL additionally executes callbacks with
the restricted application role. No RLS policies are enabled by these tests.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration, ROOT
from web.database.alembic.schema_contract_v1 import schema_signature


def seed_legacy(url, engine, *, conflict=False):
    from web.database.models import Usuario, UserRole, Subscription, StripeCustomer, UserSubscription, GymLicense
    run_migration(url, 'db_bootstrap.py', '--revision', '20261018_schema_reconciliation')
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        for suffix in ('a', 'b'):
            db.add(Usuario(id='legacy-' + suffix, email='legacy-' + suffix + '@example.test',
                nombre='Synthetic', password_hash='unused-synthetic', tipo='gym', role=UserRole.OWNER))
        db.commit()
        db.add(Subscription(gym_id='legacy-a', plan='pro_usuario', status='active', provider='stripe',
            stripe_customer_id='cus_legacy', stripe_subscription_id='sub_legacy', max_clientes=1,
            current_period_start=now - timedelta(days=1), current_period_end=now + timedelta(days=29)))
        db.add(StripeCustomer(gym_id='legacy-b' if conflict else 'legacy-a', stripe_customer_id='cus_legacy'))
        db.add(UserSubscription(user_id='legacy-a', plan='pro', max_planes_mes=5, planes_usados_mes=3,
            mes_actual=now.strftime('%Y-%m'), status='active'))
        license = GymLicense(gym_id='legacy-a', license_key='synthetic-only-issued-license', plan_tier='clinica', max_clients=0)
        db.add(license)
        db.commit()
        license_id = license.id
    with engine.begin() as db:
        db.execute(text("INSERT INTO license_activations(hardware_id,clave_hash,email,plan,activa,revocada,expira) VALUES('synthetic-hardware',:hash,'synthetic@example.test','clinica',true,false,'2027-10-01')"),
                   {'hash': hashlib.sha256(b'synthetic-only-issued-license').hexdigest()})
    return license_id


def application_engine(url, engine):
    if engine.dialect.name == 'sqlite':
        return engine
    import psycopg2
    from psycopg2 import sql
    from tests.isolation import validate_postgres_test_url
    app_url = os.environ['METODOBASE_TEST_POSTGRES_URL']
    validate_postgres_test_url(app_url)
    app = urlsplit(app_url)
    admin = urlsplit(url)
    assert (app.hostname, app.port) == (admin.hostname, admin.port)
    target = urlunsplit(app._replace(path=admin.path))
    with psycopg2.connect(url.replace('postgresql+psycopg2://', 'postgresql://', 1)) as db, db.cursor() as cursor:
        role = sql.Identifier(app.username)
        cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(role))
        cursor.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}').format(role))
        cursor.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}').format(role))
    from web.database.tenant_context import configure_tenant_engine
    from web.database.tenant_policy import verify_application_database_role
    application = configure_tenant_engine(create_engine(target, pool_size=1, max_overflow=0))
    verify_application_database_role(application)
    return application


def legacy_snapshot():
    now = int(datetime.now(timezone.utc).timestamp())
    return {'id': 'sub_legacy', 'status': 'active', 'customer': 'cus_legacy', 'metadata': {},
        'current_period_start': now - 86400, 'current_period_end': now + 29 * 86400,
        'items': {'data': [{'quantity': 1, 'price': {'currency': 'mxn', 'unit_amount': 7900,
            'recurring': {'interval': 'month', 'interval_count': 1}}}]},
        'latest_invoice': {'paid': True, 'status': 'paid', 'currency': 'mxn', 'amount_paid': 7900,
            'charge': {'id': 'ch_legacy', 'customer': 'cus_legacy', 'paid': True, 'captured': True,
                'refunded': False, 'amount_refunded': 0, 'currency': 'mxn', 'amount': 7900}}}


@pytest.mark.parametrize('callback', ['invoice', 'refund', 'cancel'])
def test_legacy_callbacks_without_purchase_intent_still_reconcile(migration_database, callback):
    from web.database.models import ProviderSubjectAssociation, Subscription, UserSubscription, LicenseActivation
    from web.services.stripe_service import _on_invoice_paid, _on_charge_refunded, _on_subscription_deleted
    url, engine = migration_database
    license_id = seed_legacy(url, engine)
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    target = json.loads((ROOT / 'web/database/alembic/schema_targets' /
                         ('20261018_prepared_' + engine.dialect.name + '.json')).read_text())['signature']
    with engine.connect() as db:
        assert schema_signature(db) == target
    app = application_engine(url, engine)
    snapshot = legacy_snapshot()
    try:
        with Session(app) as db:
            links = db.query(ProviderSubjectAssociation).all()
            assert {(row.resource_type, row.subject_id, row.provenance) for row in links} == {
                ('customer', 'legacy-a', 'legacy_subscription'), ('subscription', 'legacy-a', 'legacy_subscription')}
        with Session(engine) as db:
            assert db.query(UserSubscription).filter_by(user_id='legacy-a').one().planes_usados_mes == 3
        with patch('stripe.Subscription.retrieve', return_value=snapshot), Session(app) as db:
            if callback == 'invoice':
                _on_invoice_paid(db, {'id': 'in_legacy', 'customer': 'cus_legacy', 'currency': 'mxn', 'amount_paid': 7900})
            elif callback == 'refund':
                snapshot['latest_invoice']['charge']['refunded'] = True
                snapshot['latest_invoice']['charge']['amount_refunded'] = 7900
                _on_charge_refunded(db, {'id': 'ch_legacy', 'customer': 'cus_legacy', 'refunded': True})
            else:
                snapshot['status'] = 'canceled'
                _on_subscription_deleted(db, {'id': 'sub_legacy'})
            db.commit()
            assert db.query(Subscription).filter_by(gym_id='legacy-a').one().status == {
                'invoice': 'active', 'refund': 'unpaid', 'cancel': 'canceled'}[callback]
            assert db.query(UserSubscription).filter_by(user_id='legacy-a').one().planes_usados_mes == 3
        # Backfill only associates exact issued license identity, never rewrites
        # legacy activation rights, dates, active flags or subscription counters.
        with Session(engine) as db:
            activation = db.query(LicenseActivation).one()
            assert (activation.gym_id, activation.issued_license_id, activation.plan, activation.activa) == ('legacy-a', license_id, 'clinica', True)
            assert activation.expira.date().isoformat() == '2027-10-01'
    finally:
        if app is not engine:
            app.dispose()


def test_conflicting_legacy_association_aborts_preparation_without_losing_rows(migration_database):
    url, engine = migration_database
    seed_legacy(url, engine, conflict=True)
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py'], cwd=ROOT,
        env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    with engine.connect() as db:
        assert 'provider_subject_associations' not in inspect(db).get_table_names()
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '20261018_schema_reconciliation'
        assert db.execute(text('SELECT count(*) FROM subscriptions')).scalar_one() == 1
        assert db.execute(text('SELECT planes_usados_mes FROM user_subscriptions')).scalar_one() == 3


def test_provider_namespace_and_ambient_subject_cannot_be_confused(migration_database):
    from web.database.tenant_context import tenant_scope
    from web.database.models import ProviderSubjectAssociation
    from web.services.provider_subjects import record_provider_subject
    from web.services.stripe_service import _bind_customer_purchase
    url, engine = migration_database
    seed_legacy(url, engine)
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    app = application_engine(url, engine)
    try:
        with Session(app) as db:
            record_provider_subject(db, 'stripe', 'payment', 'same-provider-id', 'legacy-a', 'verified-a')
            db.commit()
        with Session(app) as db:
            record_provider_subject(db, 'mercadopago', 'payment', 'same-provider-id', 'legacy-b', 'verified-b')
            db.commit()
        with Session(app) as db:
            assert db.query(ProviderSubjectAssociation).filter_by(resource_id='same-provider-id').count() == 2
        with tenant_scope('legacy-b'), Session(app) as db:
            with pytest.raises(ValueError, match='mismatch'):
                _bind_customer_purchase(db, 'cus_legacy')
            db.rollback()
        with Session(engine) as db:
            assert db.query(ProviderSubjectAssociation).filter_by(provider='stripe', resource_type='customer', resource_id='cus_legacy').one().subject_id == 'legacy-a'
    finally:
        if app is not engine:
            app.dispose()
