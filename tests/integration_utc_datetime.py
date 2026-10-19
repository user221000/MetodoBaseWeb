"""Real typed binds under two PostgreSQL zones and SQLite, using own metadata.

Adoption is Python-side only. No application model or historical row is changed.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, Table, bindparam, event, select, text

from tests.integration_schema_migrations import migration_database
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.utc_datetime import UTCDateTime, as_utc_naive


@pytest.mark.parametrize("zone", ["UTC", "America/Mexico_City"])
def test_typed_binds_are_utc_and_history_schema_unchanged(migration_database, zone):
    _, engine = migration_database
    old = Table("synthetic_utc_contract", MetaData(), Column("id", Integer, primary_key=True),
                Column("instant", DateTime(timezone=False)))
    old.metadata.create_all(engine)
    historical = datetime(2001, 2, 3, 4, 5, 6)
    with engine.begin() as connection:
        connection.execute(old.insert(), {"id": 1, "instant": historical})
        before = schema_signature(connection)
    mapped = Table("synthetic_utc_contract", MetaData(), Column("id", Integer, primary_key=True),
                   Column("instant", UTCDateTime()))
    fixed = datetime(2026, 10, 19, 12, 30, 17, 123456, tzinfo=timezone.utc)
    statements = []
    def observed(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split(None, 1)[0].upper())
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {"zone": zone})
            connection.commit()
        event.listen(engine, "before_cursor_execute", observed)
        try:
            with connection.begin():
                connection.execute(mapped.insert(), [{"id": 2, "instant": fixed},
                    {"id": 3, "instant": fixed.astimezone(timezone(timedelta(hours=5, minutes=30)))},
                    {"id": 4, "instant": fixed.replace(tzinfo=None)}, {"id": 5, "instant": None}])
            with connection.begin():
                values = dict(connection.execute(select(mapped.c.id, mapped.c.instant).order_by(mapped.c.id)).all())
                assert values == {1: historical, 2: fixed.replace(tzinfo=None), 3: fixed.replace(tzinfo=None),
                                  4: fixed.replace(tzinfo=None), 5: None}
                assert list(connection.execute(select(mapped.c.id).where(mapped.c.instant >= fixed)).scalars()) == [2, 3, 4]
                assert schema_signature(connection) == before
                assert connection.execute(select(old.c.instant).where(old.c.id == 1)).scalar_one() == historical
            assert not set(statements).intersection({"UPDATE", "DELETE", "ALTER", "CREATE", "DROP"})
        finally:
            event.remove(engine, "before_cursor_execute", observed)
            if engine.dialect.name == "postgresql":
                connection.rollback()
                connection.execute(text("RESET TIME ZONE"))
                connection.commit()


@pytest.mark.parametrize("zone", ["UTC", "America/Mexico_City"])
def test_raw_sql_requires_explicit_helper_or_typed_bind(migration_database, zone):
    _, engine = migration_database
    table = Table("synthetic_raw_utc", MetaData(), Column("id", Integer, primary_key=True),
                  Column("instant", UTCDateTime()))
    table.metadata.create_all(engine)
    fixed = datetime(2026, 10, 19, 12, 30, tzinfo=timezone.utc)
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT set_config('TimeZone', :zone, false)"), {"zone": zone})
            connection.commit()
        try:
            with connection.begin():
                connection.execute(text("INSERT INTO synthetic_raw_utc(id,instant) VALUES(:id,:instant)"),
                    {"id": 1, "instant": as_utc_naive(fixed)})
                statement = text("INSERT INTO synthetic_raw_utc(id,instant) VALUES(:id,:instant)").bindparams(
                    bindparam("instant", type_=UTCDateTime()))
                connection.execute(statement, {"id": 2, "instant": fixed})
            with connection.begin():
                assert list(connection.execute(select(table.c.instant).order_by(table.c.id)).scalars()) == [fixed.replace(tzinfo=None)] * 2
        finally:
            if engine.dialect.name == "postgresql":
                connection.rollback()
                connection.execute(text("RESET TIME ZONE"))
                connection.commit()
