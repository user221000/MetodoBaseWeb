"""Application read use case; clock supplied once for a coherent window."""
from datetime import datetime, timedelta, timezone

from config.constantes import PERIODO_MES_DIAS
from web.database.followup_repository import read_followup
from web.services.followup_policy import describe


def get_followup(db, gym_id, limit):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=PERIODO_MES_DIAS)
    rows, has_more, metrics = read_followup(db, gym_id, now, cutoff, limit)
    return {'as_of': now.isoformat(), 'window_start': cutoff.isoformat(), 'window_days': PERIODO_MES_DIAS,
        'items': [describe(row, now, cutoff) for row in rows], 'limit': limit, 'has_more': has_more,
        'metrics': metrics, 'payment_evidence': 'unavailable', 'responsibility': 'not_recorded',
        'sources': {'plans': 'planes_generados', 'membership': 'clientes.fecha_fin_suscripcion',
                    'completed_operations': 'gym_generation_reservations', 'pdfs': 'stored_objects.ready'},
    }
