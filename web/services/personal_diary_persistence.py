"""Bounded personal diary reads and a single account-locked CAS transaction."""
from datetime import date, datetime, timedelta, timezone
import json
import logging
import math
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from web.database.models import PersonalDiaryDay, Usuario, UserRole
from web.database.tenant_context import bind_verified_subject
from web.personal_diary_schemas import CompletionOperation, MealOperation, MealSelection, WaterOperation
from web.services.personal_diary_service import (
    DIARY_TIMEZONE, MACRO_FIELDS, MAX_MEAL_FOODS, MEALS, _clock, local_today,
    require_calendar_range, require_writable_day, resolve_consumed_meal,
)

MAX_DAY_JSON_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_VERSION = 2147483647
logger = logging.getLogger(__name__)


def _fail(status, code, message, **extra):
    raise HTTPException(status, {'code':code, 'message':message, **extra})


def _state_error():
    _fail(409, 'diary_state_unavailable', 'No fue posible verificar este registro. Solicita una revision autorizada.')


def personal_space_supported(user) -> bool:
    """Personal and member scope; historical OWNER authority needs review."""
    valid_roles = set(UserRole)
    return user.role in valid_roles and user.role != UserRole.OWNER and (
        user.tipo == 'usuario' or bool(user.team_gym_id))


def require_personal_subject(db: Session, subject_id: str, *, lock=False) -> Usuario:
    """Revalidate persisted identity; the HTTP adapter supplies only its bearer ID."""
    query = select(Usuario).where(Usuario.id == subject_id, Usuario.activo.is_(True), Usuario.deleted_at.is_(None))
    user = db.execute(query.execution_options(populate_existing=True)).scalar_one_or_none()
    if user is None or user.invitation_token:
        _fail(401, 'diary_identity_unavailable', 'Inicia sesion nuevamente.')
    try:
        bind_verified_subject(db, user.id)
    except ValueError:
        _fail(403, 'diary_context_mismatch', 'Abre tu espacio personal para registrar tu consumo.')
    if lock:
        if db.query(Usuario).filter(Usuario.id == subject_id, Usuario.activo.is_(True),
                Usuario.deleted_at.is_(None)).update({Usuario.id:Usuario.id}, synchronize_session=False) != 1:
            _fail(401, 'diary_identity_unavailable', 'Inicia sesion nuevamente.')
        user = db.execute(query.execution_options(populate_existing=True)).scalar_one_or_none()
    if user is not None and user.tipo == 'usuario' and user.role == UserRole.OWNER:
        _fail(409, 'diary_context_requires_review', 'La autoridad de este espacio requiere una revision antes de usar el diario.')
    if user is None or user.invitation_token or not personal_space_supported(user):
        _fail(403, 'diary_personal_space_required', 'El diario pertenece al espacio personal.')
    if user.team_gym_id:
        owner = db.execute(select(Usuario.id).where(Usuario.id == user.team_gym_id, Usuario.activo.is_(True),
            Usuario.deleted_at.is_(None), Usuario.tipo == 'gym')).scalar_one_or_none()
        if owner is None:
            _fail(403, 'diary_personal_space_required', 'La pertenencia profesional ya no esta disponible.')
    return user


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate diary object member')
        result[key] = value
    return result


def decode_meals(raw: str) -> dict:
    """Validate complete stored snapshots before returning or changing any field."""
    if not isinstance(raw, str) or len(raw) > MAX_DAY_JSON_BYTES or len(raw.encode('utf-8')) > MAX_DAY_JSON_BYTES:
        _state_error()
    try:
        meals = json.loads(raw, object_pairs_hook=_pairs)
        if not isinstance(meals, dict) or set(meals) - MEALS:
            _state_error()
        for name, snapshot in meals.items():
            required = {'source_plan_id','meal','selections','foods','totals','recorded_at','completed'}
            if not isinstance(snapshot, dict) or set(snapshot) != required or snapshot['meal'] != name:
                _state_error()
            if (type(snapshot['source_plan_id']) is not int or not 0 < snapshot['source_plan_id'] <= MAX_VERSION
                    or type(snapshot['completed']) is not bool):
                _state_error()
            MealSelection.model_validate(snapshot['selections'])
            stamp = datetime.fromisoformat(snapshot['recorded_at'])
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                _state_error()
            foods = snapshot['foods']
            if not isinstance(foods, list) or len(foods) > MAX_MEAL_FOODS:
                _state_error()
            for food in foods:
                if (not isinstance(food, dict) or set(food) != {'food_id','grams','equivalence','macros'}
                        or not isinstance(food['food_id'], str) or not 1 <= len(food['food_id']) <= 200
                        or type(food['grams']) not in {int,float} or not math.isfinite(food['grams']) or food['grams'] <= 0
                        or (food['equivalence'] is not None and (not isinstance(food['equivalence'], str) or len(food['equivalence']) > 500))):
                    _state_error()
                _macros(food['macros'])
            _macros(snapshot['totals'])
            actual = {key:round(math.fsum(food['macros'][key] for food in foods),1) for key in MACRO_FIELDS}
            if snapshot['totals'] != actual:
                _state_error()
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        _state_error()
    return meals


def _macros(values):
    if not isinstance(values, dict) or set(values) != set(MACRO_FIELDS):
        _state_error()
    for value in values.values():
        if type(value) not in {int,float} or not math.isfinite(value) or value < 0:
            _state_error()


def _utc(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.astimezone(timezone.utc).isoformat()


def _bounded(result, *, maximum=MAX_RESPONSE_BYTES):
    try:
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, OverflowError):
        _state_error()
    if len(encoded) > maximum:
        _fail(413, 'diary_volume_limit', 'El registro supera el volumen permitido. Consulta un periodo menor o solicita una revision.')
    return result


def diary_state(row, day: date, *, now=None):
    result = {'local_date':day.isoformat(), 'timezone':DIARY_TIMEZONE, 'today':local_today(now).isoformat(),
        'version':0, 'water_ml':0, 'meals':{}, 'created_at':None, 'updated_at':None}
    if row is not None:
        if (row.timezone != DIARY_TIMEZONE or type(row.version) is not int or not 1 <= row.version <= MAX_VERSION
                or type(row.water_ml) is not int or not 0 <= row.water_ml <= 20000):
            _state_error()
        result.update(version=row.version, water_ml=row.water_ml, meals=decode_meals(row.meals_json),
            created_at=_utc(row.created_at), updated_at=_utc(row.updated_at))
    try:
        result['totals'] = {key:round(math.fsum(meal['totals'][key] for meal in result['meals'].values()),1)
            for key in MACRO_FIELDS}
    except OverflowError:
        _state_error()
    _macros(result['totals'])
    return _bounded(result)


def read_diary_day(db: Session, subject_id: str, day: date, *, now=None):
    require_personal_subject(db, subject_id)
    row = db.execute(select(PersonalDiaryDay).where(PersonalDiaryDay.user_id == subject_id,
        PersonalDiaryDay.local_date == day).execution_options(populate_existing=True)).scalar_one_or_none()
    return diary_state(row, day, now=now)


def read_diary_range(db: Session, subject_id: str, start: date, end: date, *, now=None):
    instant = _clock(now)
    require_calendar_range(start, end)
    require_personal_subject(db, subject_id)
    rows = db.execute(select(PersonalDiaryDay).where(PersonalDiaryDay.user_id == subject_id,
        PersonalDiaryDay.local_date >= start, PersonalDiaryDay.local_date <= end)
        .order_by(PersonalDiaryDay.local_date).limit(62).execution_options(populate_existing=True)).scalars()
    stored = {row.local_date:row for row in rows}
    days = []
    for offset in range((end-start).days+1):
        day = start+timedelta(days=offset)
        days.append(diary_state(stored.get(day), day, now=instant))
    return _bounded({'timezone':DIARY_TIMEZONE, 'today':local_today(instant).isoformat(), 'days':days})


def _rollback(db):
    try:
        db.rollback()
    except Exception as error:
        logger.error('Diary rollback failed class=%s', type(error).__name__)
        _fail(503, 'diary_save_unconfirmed', 'No fue posible confirmar el guardado. Recarga el dia antes de reintentar.')


def patch_diary_day(db: Session, subject_id: str, day: date, operation, *, now=None):
    """Exactly one service-owned COMMIT; the route dependency never autocommits."""
    try:
        instant = _clock(now)
        require_writable_day(day, now=instant)
        require_personal_subject(db, subject_id, lock=True)
        row = db.execute(select(PersonalDiaryDay).where(PersonalDiaryDay.user_id == subject_id,
            PersonalDiaryDay.local_date == day).execution_options(populate_existing=True)).scalar_one_or_none()
        version = row.version if row is not None else 0
        if version != operation.expected_version:
            _fail(409, 'diary_version_conflict', 'El dia cambio en otro dispositivo. Recargalo antes de guardar.', current_version=version)
        if version >= MAX_VERSION:
            _fail(409, 'diary_version_exhausted', 'El registro requiere una revision autorizada.')
        previous = diary_state(row, day, now=instant)
        meals, water = previous['meals'], previous['water_ml']
        if isinstance(operation, WaterOperation):
            water = operation.water_ml
        elif isinstance(operation, MealOperation):
            if operation.source_plan_id > MAX_VERSION:
                _fail(422, 'invalid_diary_plan', 'Selecciona un plan personal valido.')
            from web.services.generation_quota import read_individual_plan_result
            plan = read_individual_plan_result(db, subject_id, operation.source_plan_id)
            if plan is None:
                _fail(404, 'diary_plan_unavailable', 'No se encontro ese plan personal.')
            meals[operation.meal] = {**resolve_consumed_meal(plan, subject_id, operation.meal, operation.selections, now=instant),
                'completed':False}
        elif isinstance(operation, CompletionOperation):
            if operation.meal not in meals:
                _fail(409, 'diary_meal_required', 'Registra los alimentos de esa comida antes de completarla.')
            meals[operation.meal]['completed'] = operation.completed
        else:
            _fail(422, 'invalid_diary_operation', 'Selecciona una operacion valida.')
        encoded = json.dumps(meals, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        if len(encoded) > MAX_DAY_JSON_BYTES or len(encoded.encode('utf-8')) > MAX_DAY_JSON_BYTES:
            _fail(413, 'diary_volume_limit', 'El registro supera el volumen permitido. No se guardo ningun cambio.')
        decode_meals(encoded)
        if row is None:
            row = PersonalDiaryDay(user_id=subject_id, local_date=day, timezone=DIARY_TIMEZONE,
                water_ml=water, version=1, meals_json=encoded, created_at=instant, updated_at=instant)
            db.add(row)
        else:
            row.water_ml, row.meals_json, row.version, row.updated_at = water, encoded, version+1, instant
        db.flush()
        result = diary_state(row, day, now=instant)
        db.commit()
        return result
    except HTTPException:
        _rollback(db)
        raise
    except Exception as error:
        logger.error('Diary save failed class=%s', type(error).__name__)
        _rollback(db)
        _fail(503, 'diary_save_unconfirmed', 'No fue posible confirmar el guardado. Recarga el dia antes de reintentar.')


def export_diary_page(db, subject_id, *, limit, after=None, maximum_bytes):
    """Date-keyset page with a SQL transfer bound and complete-record budget."""
    model = PersonalDiaryDay
    query = select(model.id, model.local_date, model.timezone, model.water_ml, model.version,
        model.created_at, model.updated_at,
        case((func.length(model.meals_json) <= MAX_DAY_JSON_BYTES, model.meals_json), else_=None).label('meals_json'))
    query = query.where(model.user_id == subject_id)
    if after is not None:
        query = query.where(model.local_date > after)
    rows = db.execute(query.order_by(model.local_date).limit(limit+1).execution_options(yield_per=1)).mappings()
    records, more, used = [], False, 256
    try:
        for row in rows:
            if len(records) == limit:
                more = True
                break
            # Export has the same scalar and complete-snapshot validation as
            # interactive reads; corruption is never emitted as a partial day.
            verified = diary_state(SimpleNamespace(**row), row['local_date'])
            item = {key:(value.isoformat() if isinstance(value,date) and not isinstance(value,datetime) else _utc(value)
                if isinstance(value,datetime) else value) for key,value in row.items() if key != 'meals_json'}
            item['meals'] = verified['meals']
            item['totals'] = verified['totals']
            size = len(json.dumps(item,ensure_ascii=False,allow_nan=False,separators=(',', ':')).encode('utf-8'))+1
            if size+used > maximum_bytes:
                if not records:
                    _fail(413, 'privacy_record_requires_review', 'El registro requiere una descarga autorizada por su volumen.')
                more = True
                break
            records.append(item)
            used += size
    finally:
        rows.close()
    return {'records':records, 'next_after':records[-1]['local_date'] if more else None}
