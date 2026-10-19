"""UTC normalization is deterministic and does not reinterpret legacy history."""
from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, Table
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from web.database.utc_datetime import UTCDateTime, as_utc_naive


@pytest.mark.parametrize("offset", [-12, -6, 0, 5.5, 14])
def test_aware_offsets_describe_one_utc_instant(offset):
    fixed = datetime(2026, 10, 19, 12, 30, 17, 123456, tzinfo=timezone.utc)
    value = fixed.astimezone(timezone(timedelta(hours=offset)))
    assert as_utc_naive(value) == fixed.replace(tzinfo=None)
    assert value.tzinfo is not None


def test_naive_value_is_preserved_without_attaching_machine_timezone():
    value = datetime(2026, 10, 19, 12, 30, fold=1)
    assert as_utc_naive(value) is value
    assert as_utc_naive(None) is None


class _NaiveTimezone(tzinfo):
    def utcoffset(self, dt):
        return None


def test_python_naive_tzinfo_is_not_assumed_to_be_local_time():
    value = datetime(2026, 10, 19, 12, 30, tzinfo=_NaiveTimezone())
    assert as_utc_naive(value) == datetime(2026, 10, 19, 12, 30)


@pytest.mark.parametrize("value", ["2026-10-19", date(2026, 10, 19), 0, True, object()])
def test_other_types_are_rejected_without_echoing_values(value):
    with pytest.raises(TypeError) as error:
        as_utc_naive(value)
    assert str(error.value) == "Expected datetime or None for UTC timestamp"


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_decorator_has_identical_physical_ddl_and_schema_attributes(dialect):
    old = Table("synthetic_times", MetaData(), Column("id", Integer, primary_key=True),
                Column("instant", DateTime(timezone=False)))
    new = Table("synthetic_times", MetaData(), Column("id", Integer, primary_key=True),
                Column("instant", UTCDateTime()))
    assert str(CreateTable(old).compile(dialect=dialect)) == str(CreateTable(new).compile(dialect=dialect))
    assert str(old.c.instant.type) == str(new.c.instant.type)
    from web.database.alembic.schema_contract_v1 import _type_attributes
    assert _type_attributes(old.c.instant.type) == _type_attributes(new.c.instant.type) == {"timezone": False}
    assert new.c.instant.type.cache_ok is True
    assert new.c.instant.type.python_type is datetime


@pytest.mark.parametrize("value", [None, datetime(2001, 2, 3, 4, 5),
    datetime(2001, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-6)))])
def test_result_values_are_never_reinterpreted_or_relabelled(value):
    assert UTCDateTime().process_result_value(value, postgresql.dialect()) is value


def test_typed_bind_uses_same_normalization_as_raw_sql_helper():
    value = datetime(2026, 10, 19, 12, 30, tzinfo=timezone(timedelta(hours=-6)))
    assert UTCDateTime().process_bind_param(value, postgresql.dialect()) == as_utc_naive(value)
