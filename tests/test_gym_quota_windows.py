"""Mexico City quota days, including historical DST and UTC midnight."""
from datetime import datetime, timezone

import pytest


@pytest.mark.parametrize('instant,expected', [
    (datetime(2026, 10, 18, 5, 59, tzinfo=timezone.utc), datetime(2026, 10, 17, 6, tzinfo=timezone.utc)),
    (datetime(2026, 10, 18, 6, tzinfo=timezone.utc), datetime(2026, 10, 18, 6, tzinfo=timezone.utc)),
    (datetime(2021, 10, 31, 12, tzinfo=timezone.utc), datetime(2021, 10, 31, 5, tzinfo=timezone.utc)),
])
def test_daily_guard_starts_at_product_local_midnight(monkeypatch, instant, expected):
    from web import subscription_guard
    class SyntheticClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(subscription_guard, 'datetime', SyntheticClock)
    assert subscription_guard._today_start() == expected


@pytest.mark.parametrize('instant,hours', [
    (datetime(2021, 10, 31, 12, tzinfo=timezone.utc), 25),
    (datetime(2021, 4, 4, 12, tzinfo=timezone.utc), 23),
    (datetime(2026, 10, 18, 12, tzinfo=timezone.utc), 24),
])
def test_quota_calendar_uses_actual_local_day_length(instant, hours):
    from web.services.quota_calendar import quota_calendar
    window = quota_calendar(instant)
    assert (window.day_end - window.day_start).total_seconds() == hours * 3600
    assert window.day_start <= instant < window.day_end


def test_calendar_month_resets_at_local_midnight_and_storage_is_utc():
    from web.services.quota_calendar import quota_calendar, utc_storage_boundary
    previous = quota_calendar(datetime(2026, 11, 1, 5, 59, tzinfo=timezone.utc))
    current = quota_calendar(datetime(2026, 11, 1, 6, tzinfo=timezone.utc))
    assert previous.month == '2026-10' and current.month == '2026-11'
    assert previous.month_end == current.month_start == datetime(2026, 11, 1, 6, tzinfo=timezone.utc)
    assert utc_storage_boundary(current.day_start) == datetime(2026, 11, 1, 6)


def test_calendar_rejects_ambiguous_naive_clock():
    from web.services.quota_calendar import quota_calendar
    with pytest.raises(ValueError, match='offset'):
        quota_calendar(datetime(2026, 10, 18))
