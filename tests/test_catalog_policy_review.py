"""Independent expiry/trial boundary review of the canonical B2B policy."""
from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.parametrize("plan,status,end,trial,expected", [
    ("standard", "active", 1, None, True),
    ("standard", "active", 0, None, False),
    ("clinica", "active", -1, None, False),
    ("clinica", "past_due", 1, None, False),
    ("clinica", "canceled", 1, None, False),
    ("clinica", "trialing", -1, 1, True),
    ("clinica", "trialing", 1, -1, False),
    ("standard", "trialing", 1, None, True),
    ("standard", "active", None, None, True),
    ("standard", "active", "invalid", None, False),
    ("pro_usuario", "active", 1, None, False),
    ("unknown", "active", 1, None, False),
])
def test_effective_gym_entitlement_respects_expiry_trial_and_legacy_mapping(plan, status, end, trial, expected):
    from core.subscription_policy import gym_subscription_is_current
    now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    def value(days):
        return now + timedelta(days=days) if isinstance(days, int) else days
    assert gym_subscription_is_current(plan=plan, status=status, period_end=value(end),
        trial_end=value(trial), now=now) is expected


def test_historical_naive_timestamps_are_consistently_utc():
    from core.subscription_policy import gym_subscription_is_current
    now = datetime(2026, 10, 18, 12)
    assert gym_subscription_is_current(plan="standard", status="active",
        period_end=now + timedelta(seconds=1), now=now)
    assert not gym_subscription_is_current(plan="standard", status="active", period_end=now, now=now)
