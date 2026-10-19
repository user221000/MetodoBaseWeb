"""Pure operational classification. No medical, payment or staffing decisions."""
from datetime import datetime, timezone


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def describe(row, now, cutoff):
    causes = []
    if row.plan_count == 0:
        causes.append('no_saved_plan')
    elif row.last_plan_at is None:
        causes.append('plan_date_missing')
    elif utc(row.last_plan_at) < cutoff:
        causes.append('no_plan_in_window')
    if row.membership_end and utc(row.membership_end) < now:
        causes.append('membership_date_passed')
    return {
        'id_cliente': row.id_cliente, 'nombre': row.nombre,
        'causes': causes, 'priority': row.priority,
        'last_plan_at': utc(row.last_plan_at).isoformat() if row.last_plan_at else None,
        'elapsed_days': max(0, (now - utc(row.last_plan_at)).days) if row.last_plan_at else None,
        'membership_end': row.membership_end.isoformat() if row.membership_end else None,
        'responsible': None,
        'next_step': 'review_plan_history' if causes[0] != 'membership_date_passed' else 'review_membership_date',
    }
