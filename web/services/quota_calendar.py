"""Calendar quota boundaries in product time, compared as UTC in storage."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class QuotaCalendar:
    local_date: date
    month: str
    day_start: datetime
    day_end: datetime
    month_start: datetime
    month_end: datetime
    timezone: str


def quota_calendar(now: datetime | None = None, *, timezone_name: str = 'America/Mexico_City') -> QuotaCalendar:
    """Compute each local midnight separately; DST days need not last 24 hours."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Quota time requires an explicit UTC offset')
    zone = ZoneInfo(timezone_name)
    local = instant.astimezone(zone)
    first = local.date().replace(day=1)
    next_month = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
    def midnight(day):
        return datetime.combine(day, time.min, tzinfo=zone).astimezone(timezone.utc)
    return QuotaCalendar(local_date=local.date(), month=local.strftime('%Y-%m'),
        day_start=midnight(local.date()), day_end=midnight(local.date() + timedelta(days=1)),
        month_start=midnight(first), month_end=midnight(next_month), timezone=timezone_name)


def utc_storage_boundary(value: datetime) -> datetime:
    """Existing TIMESTAMP WITHOUT TIME ZONE columns have an explicit UTC contract."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Storage boundary requires an explicit UTC offset')
    return value.astimezone(timezone.utc).replace(tzinfo=None)
