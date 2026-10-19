"""Pure B2B entitlement decisions shared by guards and feature consumers."""
from __future__ import annotations

from datetime import datetime, timezone


def gym_subscription_is_current(*, plan: str, status: str,
    period_end: datetime | None, trial_end: datetime | None = None,
    now: datetime | None = None) -> bool:
    """Grant supported gym capabilities only for a current active/trial state.

    Historical active mappings lacking period data retain their existing
    rights pending explicit reconciliation. This is compatibility, not a new
    grace period. Unknown plans/states/types fail closed; B2C is separate.
    Stored naive historical timestamps are interpreted as UTC deliberately.
    """
    if plan not in {"standard", "gym_comercial", "clinica"} or status not in {"active", "trialing"}:
        return False
    end = trial_end if status == "trialing" and trial_end is not None else period_end
    if end is None:
        return True
    if not isinstance(end, datetime):
        return False
    end = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
    current = now or datetime.now(timezone.utc)
    current = current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current
    return end > current
