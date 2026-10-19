"""Local synthetic export fixture; real factories, auth and export API.

Only an explicitly created temporary SQLite is populated. Export pages differ
in length so the browser must not repeat already finished collections.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.isolation import block_external_sockets, prepare_environment


def main():
    for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','PYTEST_XDIST_WORKER'):
        os.environ.pop(key, None)
    temporary_root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    os.environ['BASE_URL'] = 'http://127.0.0.1:8768'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8768,http://testserver'
    from sqlalchemy.orm import Session
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import (
        Base, Cliente, ClientProgress, GenerationReservation, PlanGenerado,
        PurchaseIntent, Usuario, UserRole, UserSubscription,
    )

    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(temporary_root):
        raise RuntimeError('Export browser fixture requires its own temporary SQLite')
    Base.metadata.create_all(engine)
    password_hash = hash_password('Synthetic-Export-Password-2026!')
    with Session(engine) as db:
        db.add_all([
            Usuario(id='synthetic-export-owner',email='export-owner@example.invalid',nombre='Synthetic Gym',password_hash=password_hash,tipo='gym',role=UserRole.OWNER,activo=True),
            Usuario(id='synthetic-export-other',email='export-other@example.invalid',nombre='Synthetic Other',password_hash=password_hash,tipo='usuario',role=UserRole.VIEWER,activo=True),
        ])
        db.commit()
        db.add(Usuario(id='synthetic-export-personal',email='export-personal@example.invalid',nombre='Synthetic Personal',password_hash=password_hash,tipo='gym',role=UserRole.VIEWER,team_gym_id='synthetic-export-owner',activo=True))
        db.commit()
        personal = Cliente(id_cliente='synthetic-export-profile',gym_id='synthetic-export-personal',nombre='Synthetic Personal',email='export-personal@example.invalid',edad=30,peso_kg=70,estatura_cm=170,sexo='M',objetivo='mantenimiento',nivel_actividad='moderada')
        db.add_all([personal,
            Cliente(id_cliente='synthetic-private-portfolio',gym_id='synthetic-export-owner',nombre='PROFESSIONAL PORTFOLIO PRIVATE'),
            Cliente(id_cliente='synthetic-private-other',gym_id='synthetic-export-other',nombre='OTHER ACCOUNT PRIVATE'),
        ])
        db.commit()
        db.add_all([PlanGenerado(gym_id='synthetic-export-personal',id_cliente=personal.id_cliente,tipo_plan='opciones',plan_json=json.dumps({'desayuno':{'kcal_objetivo':500}}) if number < 204 else 'synthetic-invalid-legacy-json') for number in range(205)])
        db.add_all([ClientProgress(gym_id='synthetic-export-personal',id_cliente=personal.id_cliente,peso_kg=70+number,notas='Synthetic measurement') for number in range(2)])
        db.add(UserSubscription(user_id='synthetic-export-personal',plan='starter',status='active',mes_actual=datetime.now(timezone.utc).strftime('%Y-%m')))
        db.add_all([PurchaseIntent(id=f'{number:08X}-ABCD-4000-8000-{number:012X}',subject_id='synthetic-export-personal',provider='stripe',operation='checkout',request_key='synthetic-export-'+str(number),plan='pro_usuario',amount_cents=7900,currency='mxn',status='pending') for number in range(102)])
        db.add_all([GenerationReservation(id=f'{number:08X}-BCDE-4000-8000-{number:012X}',user_id='synthetic-export-personal',request_key='synthetic-export-'+str(number),period='2026-10',status='released') for number in range(101)])
        db.commit()
    import uvicorn
    from web.main_web import create_app
    uvicorn.run(create_app(),host='127.0.0.1',port=8768,log_level='warning')


if __name__ == '__main__':
    main()
