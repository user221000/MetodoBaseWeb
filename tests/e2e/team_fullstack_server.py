"""Prepare only local synthetic Clinic fixtures before the real web factory.

No billing or authentication adapter is replaced. The browser logs in through
the real endpoint. Provider keys are removed and non-loopback sockets blocked
before importing product code; inherited DATABASE_URL is always discarded.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.isolation import block_external_sockets, prepare_environment


def main():
    for key in ('_METODOBASE_TEST_ROOT', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_REDIS_URL', 'PYTEST_XDIST_WORKER'):
        os.environ.pop(key, None)
    temporary_root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    os.environ['BASE_URL'] = 'http://127.0.0.1:8767'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8767,http://testserver'

    from sqlalchemy.orm import Session
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, Cliente, Subscription, Usuario, UserRole

    engine = get_engine()
    database_path = Path(engine.url.database or '').resolve()
    if engine.dialect.name != 'sqlite' or not database_path.is_relative_to(temporary_root):
        raise RuntimeError('The R11 fixture requires its own temporary SQLite database')
    Base.metadata.create_all(engine)
    password_hash = hash_password('Synthetic-Fullstack-Password-2026!')
    with Session(engine) as db:
        db.add(Usuario(id='synthetic-clinic-owner', email='r11-clinic-owner@example.invalid', nombre='Synthetic R11 Clinic', password_hash=password_hash, tipo='gym', role=UserRole.OWNER, activo=True, session_version=0))
        db.commit()
        db.add(Subscription(gym_id='synthetic-clinic-owner', plan='clinica', status='active', current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.add(Usuario(id='synthetic-legacy-professional', email='r11-legacy-professional@example.invalid', nombre='Synthetic Legacy Professional', password_hash=password_hash, tipo='gym', role=UserRole.VIEWER, team_gym_id='synthetic-clinic-owner', activo=True, session_version=0))
        db.commit()
        db.add(Cliente(id_cliente='synthetic-legacy-personal', gym_id='synthetic-legacy-professional', nombre='Synthetic Legacy Personal', peso_kg=68.5))
        db.commit()

    import uvicorn
    from web.main_web import create_app
    uvicorn.run(create_app(), host='127.0.0.1', port=8767, log_level='warning')


if __name__ == '__main__':
    main()
