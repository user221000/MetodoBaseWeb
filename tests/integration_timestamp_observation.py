"""After adoption: actual model bindings preserve UTC in legacy naive columns.

The four original PostgreSQL diagnostics remain in commit b81cfc1 and the
timestamp-observation evidence. These cases now require zero stored shift.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration


@pytest.mark.parametrize("zone", ["UTC", "America/Mexico_City"])
@pytest.mark.parametrize("binding", ["aware_utc", "naive_utc"])
def test_model_timestamp_binding_has_no_session_timezone_shift(migration_database, zone, binding, record_property):
    from web.database.models import Cliente, PlanGenerado, Subscription, Usuario, UserRole

    url, engine = migration_database
    run_migration(url, "db_bootstrap.py", "--revision", "head")
    fixed = datetime(2026, 10, 19, 12, 30, tzinfo=timezone.utc)
    value = fixed if binding == "aware_utc" else fixed.replace(tzinfo=None)
    with Session(engine) as db:
        db.add(Usuario(id="timestamp-synthetic-subject", email="timestamp@example.invalid", nombre="Synthetic",
            password_hash="synthetic-only", tipo="usuario", role=UserRole.VIEWER,
            activo=True, fecha_registro=fixed.replace(tzinfo=None)))
        db.flush()
        db.add(Cliente(id_cliente="timestamp-synthetic-profile", gym_id="timestamp-synthetic-subject",
            nombre="Synthetic", fecha_registro=fixed.replace(tzinfo=None)))
        db.commit()
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {"zone": zone})
            connection.commit()
        try:
            with Session(connection) as db:
                db.add(Subscription(gym_id="timestamp-synthetic-subject", plan="pro_usuario", status="active",
                    current_period_start=fixed.replace(tzinfo=None), current_period_end=value,
                    created_at=fixed.replace(tzinfo=None), updated_at=fixed.replace(tzinfo=None)))
                db.add(PlanGenerado(id_cliente="timestamp-synthetic-profile", gym_id="timestamp-synthetic-subject",
                    fecha_generacion=value))
                db.commit()
                expiry = db.execute(select(Subscription.current_period_end)).scalar_one()
                generated = db.execute(select(PlanGenerado.fecha_generacion)).scalar_one()
            expected = fixed.replace(tzinfo=None)
            assert expiry == expected and generated == expected
            for table, field in (("subscriptions", "current_period_end"), ("planes_generados", "fecha_generacion")):
                column = next(item for item in inspect(connection).get_columns(table) if item["name"] == field)
                assert column["type"].timezone is False
            shift = int((expiry - fixed.replace(tzinfo=None)).total_seconds())
            record_property("model_binding_contract", "utc_naive_without_schema_migration")
            record_property("session_timezone", zone)
            record_property("input_binding", binding)
            record_property("stored_shift_seconds", shift)
            assert shift == 0
        finally:
            if engine.dialect.name == "postgresql":
                connection.rollback()
                connection.execute(text("RESET TIME ZONE"))
                connection.commit()
