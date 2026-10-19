"""UTC writes for the existing TIMESTAMP WITHOUT TIME ZONE schema.

Adopting this type changes Python bind processing, not the SQL column type.
Historical naive values are returned unchanged: their original timezone cannot
be recovered from storage. Untyped raw SQL must call as_utc_naive explicitly.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def as_utc_naive(value: datetime | None) -> datetime | None:
    """Normalize an instant for a legacy UTC-naive column, preserving naive input.

    None stays None. A naive value already follows the legacy UTC convention;
    it is never interpreted in the machine or database session timezone.
    """
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError("Expected datetime or None for UTC timestamp")
    if value.tzinfo is None:
        return value
    if value.utcoffset() is None:
        return value.replace(tzinfo=None)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class UTCDateTime(TypeDecorator):
    """DateTime(timezone=False) with UTC normalization for typed bound values.

    Applies equally to inserts, updates and typed comparison parameters, even
    through a direct Session/Connection. Results are not shifted or relabelled.
    This does not protect SQL text without a declared UTCDateTime bind type.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self):
        super().__init__(timezone=False)

    @property
    def python_type(self):
        return datetime

    def process_bind_param(self, value, dialect):
        return as_utc_naive(value)

    def process_result_value(self, value, dialect):
        return value
