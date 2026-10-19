"""Accepted head24 + actual ORM/session bindings, without DDL/data reinterpretation."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select, text, update
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.schema_control import verify_runtime_schema


@pytest.fixture
def actual_utc_models(migration_database):
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    with admin.begin() as connection:
        connection.execute(text("""INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro)
            VALUES('utc-legacy-owner','utc-legacy@example.test','unused-synthetic','Synthetic','','gym','OWNER',true,0,'2001-02-03 04:05:06.123456')"""))
        connection.execute(text("""INSERT INTO clientes(id_cliente,gym_id,nombre,fecha_registro,ultimo_plan,fecha_suscripcion,fecha_fin_suscripcion)
            VALUES('utc-legacy-client','utc-legacy-owner','Synthetic','2001-02-03 04:05:06.123456','2001-02-03 04:05:06.123456','2001-02-03 00:00:00','2001-03-03 23:59:59')"""))
        connection.execute(text("""INSERT INTO planes_generados(id_cliente,gym_id,fecha_generacion)
            VALUES('utc-legacy-client','utc-legacy-owner','2001-02-03 04:05:06.123456')"""))
    def legacy_snapshot():
        with admin.connect() as connection:
            return (connection.execute(text("SELECT fecha_registro FROM usuarios WHERE id='utc-legacy-owner'")).one(),
                connection.execute(text("SELECT fecha_registro,ultimo_plan,fecha_suscripcion,fecha_fin_suscripcion FROM clientes WHERE id_cliente='utc-legacy-client'")).one(),
                connection.execute(text("SELECT fecha_generacion FROM planes_generados WHERE id_cliente='utc-legacy-client'")).one())
    original_rows = legacy_snapshot()
    with admin.connect() as connection:
        original_schema, original_security = schema_signature(connection), tenant_security_signature(connection)
    app = application_engine(url, admin)
    try:
        yield admin, app
        assert legacy_snapshot() == original_rows
        with admin.connect() as connection:
            assert schema_signature(connection) == original_schema
            assert tenant_security_signature(connection) == original_security
        verify_runtime_schema(app)
    finally:
        app.dispose()


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('zone', ['UTC','America/Mexico_City'])
@pytest.mark.parametrize('offset', [-6,0,5.5])
def test_current_orm_instants_and_typed_filters_have_same_utc_storage(actual_utc_models, zone, offset):
    from web.database.models import Cliente, Invoice, PlanGenerado, Subscription, Usuario, UserRole
    from web.database.tenant_context import tenant_scope
    from web.database.utc_datetime import UTCDateTime
    _, app = actual_utc_models
    with app.connect() as connection:
        connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {'zone':zone})
        connection.commit()
    fixed = datetime(2032,11,1,12,30,17,123456,tzinfo=timezone.utc)
    value = fixed.astimezone(timezone(timedelta(hours=offset)))
    expected, end = fixed.replace(tzinfo=None), fixed + timedelta(days=1)
    with tenant_scope('utc-current-owner'), Session(app) as db:
        db.add(Usuario(id='utc-current-owner',email='utc-current@example.test',nombre='Synthetic',
            password_hash='unused-synthetic',tipo='gym',role=UserRole.OWNER,fecha_registro=value,
            invitation_expires=value+timedelta(hours=1)))
        db.flush()
        db.add(Cliente(id_cliente='utc-current-client',gym_id='utc-current-owner',nombre='Synthetic',fecha_registro=value))
        db.flush()
        db.add(Subscription(gym_id='utc-current-owner',plan='standard',status='active',
            current_period_start=value,current_period_end=value+timedelta(days=1),trial_start=value,
            trial_end=value+timedelta(hours=1),created_at=value,updated_at=value))
        db.add(PlanGenerado(gym_id='utc-current-owner',id_cliente='utc-current-client',fecha_generacion=value))
        db.add(Invoice(gym_id='utc-current-owner',stripe_invoice_id='in_utc_synthetic',amount_due=100,total=100,
            status='paid',period_start=value,period_end=value+timedelta(days=1),due_date=value,paid_at=value,created_at=value))
        db.commit()
        # Untyped reads prove the driver stored UTC; a result processor cannot
        # disguise a wrong persisted wall-clock value in these assertions.
        assert db.execute(text("SELECT fecha_registro,invitation_expires FROM usuarios WHERE id='utc-current-owner'")).one() == (expected, expected+timedelta(hours=1))
        assert db.execute(text("SELECT current_period_start,current_period_end,trial_start,trial_end FROM subscriptions WHERE gym_id='utc-current-owner'")).one() == (expected,end.replace(tzinfo=None),expected,expected+timedelta(hours=1))
        assert db.execute(text("SELECT fecha_generacion FROM planes_generados WHERE gym_id='utc-current-owner'")).scalar_one() == expected
        assert db.scalar(select(Subscription.id).where(Subscription.gym_id=='utc-current-owner',Subscription.current_period_end==end))
        assert db.scalar(select(PlanGenerado.id).where(PlanGenerado.gym_id=='utc-current-owner',PlanGenerado.fecha_generacion==expected))
        assert db.scalar(select(Invoice.id).where(Invoice.gym_id=='utc-current-owner',Invoice.period_start<=value,Invoice.period_end>value))
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        db.execute(update(Subscription).where(Subscription.gym_id=='utc-current-owner').values(current_period_end=end+timedelta(hours=1)))
        db.commit()
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        stored_end, updated_at = db.execute(text("SELECT current_period_end,updated_at FROM subscriptions WHERE gym_id='utc-current-owner'")).one()
        assert stored_end == (end+timedelta(hours=1)).replace(tzinfo=None)
        assert before <= updated_at <= after
    # These are civil membership dates emitted without offsets by datepickers.
    assert not isinstance(Cliente.fecha_suscripcion.type, UTCDateTime)
    assert not isinstance(Cliente.fecha_fin_suscripcion.type, UTCDateTime)
    assert inspect(app).get_columns('subscriptions')[0]  # Reflection remains usable.


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('zone', ['UTC','America/Mexico_City'])
def test_actual_invitation_near_expiry_is_accepted_under_either_database_timezone(actual_utc_models, zone):
    from web.database.models import Subscription, Usuario, UserRole
    from web.database.tenant_context import tenant_scope
    from web.services import team_invitation_service as invitations
    _, app = actual_utc_models
    with app.connect() as connection:
        connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {'zone':zone})
        connection.commit()
    actor = {'id':'utc-inviting-owner','role':'owner'}
    now = datetime.now(timezone.utc)
    with tenant_scope(actor['id']), Session(app) as db:
        db.add(Usuario(id=actor['id'],email='utc-inviting@example.test',nombre='Synthetic',password_hash='unused',
            tipo='gym',role=UserRole.OWNER))
        db.flush()
        db.add(Subscription(gym_id=actor['id'],plan='clinica',status='active',
            current_period_end=(now+timedelta(days=1)).replace(tzinfo=None)))
        db.commit()
        offered = invitations.issue(db,actor=actor,gym_id=actor['id'],email='utc-invited@example.test',
            nombre='Synthetic',apellido='',role=UserRole.VIEWER,base_url='http://127.0.0.1:8765')
        pending = invitations.find_invitation(db,offered['invitation_token'])
        pending.invitation_expires = now+timedelta(minutes=30)
        db.commit()
        identity = invitations.consume(db,offered['invitation_token'],'Synthetic-invitation-password-2026')
        assert identity['team_gym_id'] == actor['id'] and identity['role'] == 'viewer'
