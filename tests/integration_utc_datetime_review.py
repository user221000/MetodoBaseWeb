"""Independent UTC bind review: real ORM writes, historical rows and raw SQL.

Only synthetic metadata in fixture-owned databases is used. Application models,
schema history and database defaults are not modified by these cases.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, Table, select, text, update
from sqlalchemy.orm import Session, registry

from tests.integration_schema_migrations import migration_database
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.utc_datetime import UTCDateTime


@pytest.mark.parametrize("zone", ["UTC", "America/Mexico_City"])
def test_direct_session_insert_update_filter_and_history(migration_database, zone):
    _, engine = migration_database
    original = Table("qa_utc_session", MetaData(), Column("id", Integer, primary_key=True),
                     Column("instant", DateTime(timezone=False)))
    original.metadata.create_all(engine)
    historical = datetime(2003, 4, 5, 6, 7, 8, 123456)
    with engine.begin() as connection:
        connection.execute(original.insert(), {"id": 1, "instant": historical})
        before = schema_signature(connection)

    mapped = Table("qa_utc_session", MetaData(), Column("id", Integer, primary_key=True),
                   Column("instant", UTCDateTime()))
    mapper = registry()

    class SyntheticInstant:
        pass

    mapper.map_imperatively(SyntheticInstant, mapped)
    fixed = datetime(2026, 10, 18, 23, 59, 59, 654321, tzinfo=timezone.utc)
    alternate = fixed.astimezone(timezone(timedelta(hours=14)))
    try:
        with engine.connect() as connection:
            if engine.dialect.name == "postgresql":
                connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {"zone": zone})
                assert connection.execute(text("SHOW TimeZone")).scalar_one() == zone
                connection.commit()
            try:
                with Session(connection, expire_on_commit=False) as db:
                    value = SyntheticInstant()
                    value.id, value.instant = 2, alternate
                    db.add(value)
                    db.commit()
                    db.expire_all()
                    assert db.get(SyntheticInstant, 2).instant == fixed.replace(tzinfo=None)
                    replacement = fixed + timedelta(seconds=1)
                    db.execute(update(mapped).where(mapped.c.id == 2).values(instant=replacement))
                    db.commit()
                    db.expire_all()
                    assert db.get(SyntheticInstant, 2).instant == replacement.replace(tzinfo=None)
                    # A typed comparison must normalize its parameter too.
                    assert db.scalars(select(mapped.c.id).where(mapped.c.instant > alternate)).all() == [2]
                    db.rollback()
                    assert db.get(SyntheticInstant, 1).instant == historical
                    db.rollback()
                assert schema_signature(connection) == before
                assert connection.execute(select(original.c.instant).where(original.c.id == 1)).scalar_one() == historical
            finally:
                connection.rollback()
                if engine.dialect.name == "postgresql":
                    connection.execute(text("RESET TIME ZONE"))
                    connection.commit()
    finally:
        mapper.dispose()


@pytest.mark.parametrize("migration_database", ["postgresql"], indirect=True)
@pytest.mark.parametrize("zone, expected_raw_shift", [("UTC", 0), ("America/Mexico_City", -21600)])
def test_positive_typed_fix_is_distinguished_from_untyped_driver_shift(
        migration_database, zone, expected_raw_shift):
    _, engine = migration_database
    mapped = Table("qa_utc_driver_control", MetaData(), Column("id", Integer, primary_key=True),
                   Column("instant", UTCDateTime()))
    mapped.metadata.create_all(engine)
    fixed = datetime(2026, 10, 18, 18, 30, 11, 987654, tzinfo=timezone.utc)
    with engine.connect() as connection:
        connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {"zone": zone})
        assert connection.execute(text("SHOW TimeZone")).scalar_one() == zone
        connection.commit()
        try:
            with connection.begin():
                # This deliberately untyped control reproduces psycopg2's old
                # aware-to-TIMESTAMP conversion only in this synthetic table.
                connection.execute(text("INSERT INTO qa_utc_driver_control VALUES (1, :instant)"), {"instant": fixed})
                connection.execute(mapped.insert(), {"id": 2, "instant": fixed})
            values = dict(connection.execute(select(mapped.c.id, mapped.c.instant)).all())
            assert values[1] == fixed.replace(tzinfo=None) + timedelta(seconds=expected_raw_shift)
            assert values[2] == fixed.replace(tzinfo=None)
        finally:
            connection.rollback()
            connection.execute(text("RESET TIME ZONE"))
            connection.commit()
