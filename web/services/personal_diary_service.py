"""R14 date and consumed-food snapshots used by authenticated persistence.

The adapter authenticates the persisted personal subject, fetches that subject's
source plan, and commits these values using the diary's conditional version.
Snapshots preserve a meal's source when another menu is generated that day.
"""
from datetime import date, datetime, timezone
import json
import math
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from web.personal_diary_schemas import MealName, MealSelection

DIARY_TIMEZONE = 'America/Mexico_City'
MEALS = {'desayuno', 'almuerzo', 'comida', 'cena'}
MACRO_FIELDS = {'kcal':'kcal', 'protein_g':'proteina', 'carbs_g':'carbs', 'fat_g':'grasa'}
MAX_SOURCE_PLAN_BYTES = 256 * 1024
MAX_MEAL_FOODS = 32
MAX_GROUP_OPTIONS = 256


def _fail(status: int, code: str, message: str):
    raise HTTPException(status, {'code':code, 'message':message})


def _clock(now: datetime | None) -> datetime:
    instant = datetime.now(timezone.utc) if now is None else now
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Diary clock requires an explicit timezone')
    return instant.astimezone(timezone.utc)


def local_today(now: datetime | None = None) -> date:
    return _clock(now).astimezone(ZoneInfo(DIARY_TIMEZONE)).date()


def require_writable_day(day: date, *, now: datetime | None = None) -> date:
    if type(day) is not date or day > local_today(now):
        _fail(422, 'invalid_diary_day', 'Elige hoy o una fecha anterior para registrar tu consumo.')
    return day


def require_calendar_range(start: date, end: date) -> tuple[date, date]:
    if type(start) is not date or type(end) is not date or not 0 <= (end-start).days < 62:
        _fail(422, 'invalid_diary_range', 'Consulta un periodo de hasta 62 días.')
    return start, end


def _unsupported():
    _fail(409, 'diary_source_unavailable', 'No fue posible verificar los alimentos de ese plan. Vuelve a consultar tu menú.')


def _number(value, *, positive: bool = False) -> float:
    if type(value) not in {int, float}:
        _unsupported()
    try:
        number = float(value)
    except OverflowError:
        _unsupported()
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        _unsupported()
    return number


def _food(option: dict) -> dict:
    if not isinstance(option, dict):
        _unsupported()
    food_id = option.get('alimento')
    if not isinstance(food_id, str) or not food_id or len(food_id) > 200:
        _unsupported()
    grams = _number(option.get('gramos'), positive=True)
    equivalence = option.get('equivalencia')
    if equivalence is not None and (not isinstance(equivalence, str) or len(equivalence) > 500):
        _unsupported()
    try:
        food_id.encode('utf-8')
        if equivalence is not None:
            equivalence.encode('utf-8')
    except UnicodeError:
        _unsupported()
    macros = option.get('macros')
    if macros is None or macros == {}:
        # Legacy plan options sometimes lack macros. Resolve them from the
        # same server catalog used by the plan engine, never from HTTP totals.
        from src.alimentos_base import ALIMENTOS_BASE
        canonical = ALIMENTOS_BASE.get(food_id)
        if not canonical:
            _unsupported()
        macros = {name: _number(canonical.get(name)) * grams / 100 for name in MACRO_FIELDS.values()}
    if not isinstance(macros, dict):
        _unsupported()
    return {'food_id':food_id, 'grams':grams, 'equivalence':equivalence,
            'macros':{key:_number(macros.get(source)) for key,source in MACRO_FIELDS.items()}}


def resolve_consumed_meal(plan_record, user_id: str, meal: MealName,
                          selections: MealSelection, *, now: datetime | None = None) -> dict:
    """Resolve one explicit consumption against an already-loaded own plan.

    The mounted diary service fetches this record using persisted ownership.
    This repeated check rejects accidental cross-account or deleted sources;
    a request body never supplies user_id, gym_id, macros or food labels.
    """
    if (not isinstance(user_id, str) or not user_id
            or getattr(plan_record, 'gym_id', None) != user_id
            or getattr(plan_record, 'deleted_at', None) is not None):
        _fail(404, 'diary_plan_unavailable', 'No se encontró ese plan personal.')
    if meal not in MEALS or not isinstance(selections, MealSelection):
        _fail(422, 'invalid_diary_meal', 'Selecciona una comida y alimentos válidos.')
    source_id = getattr(plan_record, 'id', None)
    if type(source_id) is not int or source_id <= 0:
        _unsupported()
    raw = getattr(plan_record, 'plan_json', None)
    if (not isinstance(raw, str) or len(raw) > MAX_SOURCE_PLAN_BYTES
            or len(raw.encode('utf-8')) > MAX_SOURCE_PLAN_BYTES):
        _unsupported()
    try:
        source = json.loads(raw)
    except (ValueError, RecursionError):
        _unsupported()
    if not isinstance(source, dict) or not isinstance(source.get(meal), dict):
        _unsupported()
    return resolve_verified_meal(source_id, source[meal], meal, selections, now=now)


def resolve_verified_meal(source_id: int, meal_data: dict, meal: MealName,
                          selections: MealSelection, *, now=None) -> dict:
    """Pure value extraction after the caller proves personal/publication authority.

    This helper grants no source access. It accepts no request-provided foods,
    grams or totals, and never manufactures a model with a different owner.
    """
    if type(source_id) is not int or source_id<=0 or meal not in MEALS or not isinstance(meal_data,dict):
        _unsupported()
    chosen = selections.model_dump(exclude_none=True, exclude={'include_vegetables','include_fixed_menu'})
    foods = []
    if selections.include_fixed_menu:
        if chosen or selections.include_vegetables or meal_data.get('tipo_plan')=='opciones' or 'proteinas' in meal_data:
            _fail(422,'invalid_diary_selection','Selecciona el menu fijo completo o las opciones, sin mezclarlos.')
        fixed=meal_data.get('alimentos')
        if not isinstance(fixed,dict) or len(fixed)>MAX_MEAL_FOODS:_unsupported()
        foods=[_food({'alimento':name,'gramos':grams}) for name,grams in fixed.items()]
        chosen={'include_fixed_menu':True}
    elif isinstance(meal_data.get('alimentos'),dict) and 'proteinas' not in meal_data:
        _fail(422,'invalid_diary_selection','Confirma explicitamente el menu fijo completo para registrarlo.')
    if chosen or selections.include_vegetables:
        for group,index in chosen.items():
            if group=='include_fixed_menu':continue
            group_data = meal_data.get(group)
            options = group_data.get('opciones') if isinstance(group_data, dict) else None
            if not isinstance(options, list) or len(options) > MAX_GROUP_OPTIONS:
                _unsupported()
            if index >= len(options):
                _fail(422, 'invalid_diary_option', 'Una opción cambió. Vuelve a consultar el menú antes de guardar.')
            foods.append(_food(options[index]))
        if selections.include_vegetables:
            vegetables = meal_data.get('vegetales', [])
            if not isinstance(vegetables, list) or len(foods) + len(vegetables) > MAX_MEAL_FOODS:
                _unsupported()
            foods.extend(_food(option) for option in vegetables)
    try:
        totals = {key:round(math.fsum(food['macros'][key] for food in foods),1) for key in MACRO_FIELDS}
    except OverflowError:
        _unsupported()
    if any(not math.isfinite(value) for value in totals.values()):
        _unsupported()
    return {'source_plan_id':source_id, 'meal':meal,
            'selections':{**chosen, 'include_vegetables':selections.include_vegetables},
            'foods':foods, 'totals':totals, 'recorded_at':_clock(now).isoformat()}
