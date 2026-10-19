"""Dedicated synthetic B2B browser: real auth, quota, worker and PDF API.

Own temporary SQLite only. External transports are blocked before app imports.
No privileged fixture endpoint and no live provider credentials.
"""
import os
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets, prepare_environment


def main():
    for key in ('_METODOBASE_TEST_ROOT', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_REDIS_URL', 'PYTEST_XDIST_WORKER'):
        os.environ.pop(key, None)
    temporary_root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    os.environ['BASE_URL'] = 'http://127.0.0.1:8769'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8769,http://testserver'
    from sqlalchemy.orm import Session
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, Cliente, Usuario, UserRole

    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(temporary_root):
        raise RuntimeError('B2B browser fixture requires its own temporary SQLite')
    Base.metadata.create_all(engine)
    password_hash = hash_password('Synthetic-Generation-Password-2026!')
    with Session(engine) as db:
        for suffix in ('owner', 'other'):
            db.add(Usuario(id=f'synthetic-generation-{suffix}', email=f'generation-{suffix}@example.invalid', nombre=f'Synthetic {suffix}', password_hash=password_hash, tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        for number in range(1, 5):
            db.add(Cliente(id_cliente=f'synthetic-generation-client-{number}', gym_id='synthetic-generation-owner', nombre=f'Synthetic Client {number}', edad=30, sexo='M', peso_kg=75, estatura_cm=175, objetivo='mantenimiento', nivel_actividad='moderada', activo=True))
        db.add(Cliente(id_cliente='synthetic-generation-foreign-client', gym_id='synthetic-generation-other', nombre='Other Private Client', edad=30, sexo='F', peso_kg=65, estatura_cm=165, objetivo='mantenimiento', nivel_actividad='moderada', activo=True))
        db.commit()
    import uvicorn
    from web.main_web import create_app
    root = Path(__file__).resolve().parents[2]
    sources = ['web/main_web.py', 'web/database/models.py', 'web/database/engine.py', 'web/routes/planes.py', 'web/routes/auth.py', 'web/auth.py', 'web/services/plan_documents.py', 'web/services/plan_generation.py', 'web/services/gym_generation_quota.py', 'web/services/quota_calendar.py', 'web/middleware/security_headers.py']
    print(json.dumps({'fixture': 'isolated-b2b-generation', 'tables': len(Base.metadata.tables), 'sources': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}}), flush=True)
    uvicorn.run(create_app(), host='127.0.0.1', port=8769, log_level='warning')


if __name__ == '__main__':
    main()
