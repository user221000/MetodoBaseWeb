"""Current private-object runtime browser; own SQLite and local object store only."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
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
    os.environ['BASE_URL'] = 'http://127.0.0.1:8770'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8770,http://testserver'
    from sqlalchemy.orm import Session
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, Cliente, Subscription, Usuario, UserRole

    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(temporary_root):
        raise RuntimeError('Branding browser requires its own temporary SQLite')
    Base.metadata.create_all(engine)
    password_hash = hash_password('Synthetic-Branding-Password-2026!')
    with Session(engine) as db:
        for suffix in ('owner', 'other'):
            db.add(Usuario(id=f'synthetic-branding-{suffix}', email=f'branding-{suffix}@example.invalid', nombre=f'Synthetic {suffix}', password_hash=password_hash, tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        db.add(Usuario(id='synthetic-branding-viewer', email='branding-viewer@example.invalid', nombre='Synthetic Viewer', password_hash=password_hash, tipo='gym', role=UserRole.VIEWER, team_gym_id='synthetic-branding-owner', activo=True))
        db.add(Subscription(gym_id='synthetic-branding-owner', plan='clinica', status='active', max_clientes=0, current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.add(Cliente(id_cliente='synthetic-branding-client', gym_id='synthetic-branding-owner', nombre='Synthetic Branding Client', edad=30, sexo='M', peso_kg=75, estatura_cm=175, objetivo='mantenimiento', nivel_actividad='moderada', activo=True))
        db.commit()
    import uvicorn
    from web.main_web import create_app
    root = Path(__file__).resolve().parents[2]
    sources = ['web/main_web.py', 'api/app.py', 'web/database/models.py', 'web/database/engine.py', 'web/database/repository.py', 'web/routes/planes.py', 'web/routes/gym_profile.py', 'web/routes/auth.py', 'web/auth.py', 'web/auth_deps.py', 'web/services/plan_documents.py', 'web/services/plan_generation.py', 'web/services/private_objects.py', 'web/services/gym_logos.py', 'web/services/gym_generation_quota.py', 'web/storage/configuration.py', 'web/storage/runtime.py', 'web/storage/objects.py', 'web/storage/local.py', 'web/storage/s3.py', 'web/settings.py', 'config/settings.py', 'web/constants.py', 'web/middleware/security_headers.py', 'requirements_web.lock', 'requirements_web-windows.lock', 'requirements-test.lock', 'requirements-test-windows.lock']
    print(json.dumps({'fixture': 'current-private-branding', 'tables': len(Base.metadata.tables), 'storage': 'own-temporary-local', 'sources': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}}), flush=True)
    uvicorn.run(create_app(), host='127.0.0.1', port=8770, log_level='warning')


if __name__ == '__main__':
    main()
