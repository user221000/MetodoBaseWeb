"""Serialize gym quota decisions before CPU work, shared by every worker."""
from datetime import datetime, timezone
import hashlib
import json
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import exists

from web.database.models import Cliente, GymGenerationReservation, PlanGenerado, Subscription, Usuario
from web.services.quota_calendar import quota_calendar, utc_storage_boundary


def _fail(code, message, *, status=403, **extra):
    raise HTTPException(status, {"code": code, "message": message, **extra})


def request_fingerprint(payload: dict) -> str:
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        _fail('invalid_generation_request', 'Solicitud de generacion invalida.', status=422)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def lock_gym_account(db, gym_id):
    if db.query(Usuario).filter_by(id=gym_id).update({Usuario.id: Usuario.id}, synchronize_session=False) != 1:
        _fail('account_unavailable', 'Cuenta no disponible.')


def _current_plan(db, gym_id):
    from web.subscription_guard import _get_gym_plan, _get_plan_config
    db.query(Subscription).filter_by(gym_id=gym_id).populate_existing().first()
    plan = _get_gym_plan(db, gym_id)
    return plan, _get_plan_config(plan)


def check_gym_client_capacity(db, gym_id: str, *, now=None) -> None:
    """Hold account lock through the caller's client INSERT/commit."""
    lock_gym_account(db, gym_id)
    _, limits = _current_plan(db, gym_id)
    maximum = limits['max_clientes']
    used = db.query(Cliente).filter_by(gym_id=gym_id, activo=True, deleted_at=None).count()
    if maximum > 0 and used >= maximum:
        _fail('client_limit_reached', 'Has alcanzado el limite de clientes activos.', current=used, limit=maximum)
    maximum = limits['max_registros_diarios']
    if maximum > 0:
        window = quota_calendar(now)
        used = db.query(Cliente).filter(Cliente.gym_id == gym_id,
            Cliente.fecha_registro >= utc_storage_boundary(window.day_start),
            Cliente.fecha_registro < utc_storage_boundary(window.day_end)).count()
        if used >= maximum:
            _fail('daily_registration_limit', 'Has alcanzado el limite de registros de hoy.', current=used, limit=maximum)


def _usage(db, gym_id, window, client_id=None, *, monthly=False):
    reservations = db.query(GymGenerationReservation).filter(
        GymGenerationReservation.gym_id == gym_id,
        GymGenerationReservation.status.in_(['reserved', 'completed']))
    start, end = (window.month_start, window.month_end) if monthly else (window.day_start, window.day_end)
    if monthly:
        reservations = reservations.filter(GymGenerationReservation.period == window.month)
    else:
        reservations = reservations.filter(GymGenerationReservation.local_date == window.local_date)
    if client_id is not None:
        reservations = reservations.filter(GymGenerationReservation.client_id == client_id)
    # Linked plans already consume the reservation's captured period, including
    # a worker that finishes after local midnight/month rollover.
    linked = exists().where(GymGenerationReservation.gym_id == gym_id,
        GymGenerationReservation.plan_id == PlanGenerado.id)
    historical = db.query(PlanGenerado).filter(PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= utc_storage_boundary(start),
        PlanGenerado.fecha_generacion < utc_storage_boundary(end), ~linked)
    if client_id is not None:
        historical = historical.filter(PlanGenerado.id_cliente == client_id)
    return reservations.count() + historical.count()


def reserve_gym_generation(db, gym_id: str, payload: dict, request_key: str | None = None, *, now=None):
    """Commit one reservation, or replay a completed identical request."""
    key = request_key if request_key is not None else str(uuid.uuid4())
    if not isinstance(key, str) or not 1 <= len(key) <= 128:
        _fail('invalid_idempotency_key', 'Clave de solicitud invalida.', status=400)
    fingerprint = request_fingerprint(payload)
    lock_gym_account(db, gym_id)
    previous = db.query(GymGenerationReservation).filter_by(gym_id=gym_id, request_key=key).populate_existing().first()
    if previous:
        if previous.request_hash != fingerprint:
            _fail('idempotency_conflict', 'La clave ya pertenece a otra solicitud.', status=409)
        if previous.status == 'completed':
            plan = db.query(PlanGenerado.id).filter_by(id=previous.plan_id, gym_id=gym_id, deleted_at=None).first()
            client = db.query(Cliente.id).filter_by(id_cliente=previous.client_id, gym_id=gym_id, deleted_at=None).first()
            if not plan or not client:
                _fail('generation_result_unavailable', 'El plan solicitado ya no esta disponible.', status=410)
            db.commit()
            return previous
        _fail('generation_result_pending' if previous.persisted_at else ('generation_failed' if previous.status == 'released' else 'generation_in_progress'),
            'La solicitud ya fue recibida. Consulta el historial antes de iniciar otra.', status=409)
    client_id = payload.get('id_cliente')
    if not db.query(Cliente.id).filter_by(id_cliente=client_id, gym_id=gym_id, activo=True, deleted_at=None).first():
        _fail('client_unavailable', 'Cliente no encontrado.', status=404)
    from web.services.nutrition_profiles import require_client_automation
    require_client_automation(db, gym_id, client_id)
    window = quota_calendar(now)
    plan, limits = _current_plan(db, gym_id)
    dimensions = [
        ('max_planes_mes', 'monthly_plan_limit_gym', None, True),
        ('max_planes_diarios', 'daily_plan_limit_gym', None, False),
        ('max_planes_por_cliente_dia', 'daily_plan_limit', client_id, False),
    ]
    for field, code, selected_client, monthly in dimensions:
        maximum = limits[field]
        if maximum > 0:
            used = _usage(db, gym_id, window, selected_client, monthly=monthly)
            if used >= maximum:
                _fail(code, 'Has utilizado los planes disponibles en este periodo.', current=used, limit=maximum)
    stamp = utc_storage_boundary(now or datetime.now(timezone.utc))
    reservation = GymGenerationReservation(gym_id=gym_id, client_id=client_id, request_key=key,
        request_hash=fingerprint, period=window.month, local_date=window.local_date, timezone=window.timezone,
        catalog_plan=plan, status='reserved', created_at=stamp, updated_at=stamp)
    db.add(reservation)
    db.commit()
    return reservation


def complete_gym_generation(db, gym_id: str, reservation_id: str, result: dict) -> dict:
    lock_gym_account(db, gym_id)
    reservation = db.query(GymGenerationReservation).filter_by(id=reservation_id, gym_id=gym_id).populate_existing().one()
    if reservation.status == 'completed':
        db.commit()
        return json.loads(reservation.result_json)
    if reservation.status != 'reserved' or reservation.persisted_at is None or reservation.plan_id != result.get('plan_id'):
        raise ValueError('Generation result was not persisted with its reservation')
    if not db.query(PlanGenerado.id).filter_by(id=reservation.plan_id, gym_id=gym_id).first():
        raise ValueError('Persisted generation result is unavailable')
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    reservation.status, reservation.result_json = 'completed', encoded
    reservation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return json.loads(encoded)


def fail_gym_generation(db, gym_id: str, reservation_id: str) -> None:
    lock_gym_account(db, gym_id)
    reservation = db.query(GymGenerationReservation).filter_by(id=reservation_id, gym_id=gym_id).populate_existing().one()
    if reservation.status == 'reserved' and reservation.persisted_at is None:
        reservation.status = 'released'
        reservation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


def compensate_generation_failure(db, gym_id: str, reservation_id: str) -> None:
    """Attempt compensation without leaking database parameters on failure.

    A database error does not establish that credit was released. Preserve the
    durable reservation and return a stable reconciliation response. Rollback
    belongs inside the protected boundary because it can also fail. Callers
    capture the reservation ID before work so no expired ORM attribute is read
    from a failed transaction while handling the original exception.
    """
    try:
        db.rollback()
        fail_gym_generation(db, gym_id, reservation_id)
    except Exception as error:
        logging.getLogger(__name__).error("Generation compensation failed class=%s", type(error).__name__)
        raise HTTPException(status_code=503, detail={
            "code": "generation_reconciliation_required",
            "message": "No fue posible confirmar la generación. Consulta el historial antes de reintentar.",
        }) from None
