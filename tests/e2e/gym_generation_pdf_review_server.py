"""Own synthetic Clinic fixture for old/new PDF browser review, Git24 only.

Run from the immutable 24-table snapshot, on the dedicated 8769 port.
This creates no provider state and changes no accepted Free fixture.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
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
    from web.database.models import Base, Cliente, Subscription, Usuario, UserRole

    engine = get_engine()
    if len(Base.metadata.tables) != 24:
        raise RuntimeError('This review fixture requires the immutable 24-table source snapshot')
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(temporary_root):
        raise RuntimeError('Own temporary SQLite required')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Usuario(id='synthetic-pdf-review-owner', email='pdf-review-owner@example.invalid', nombre='Synthetic PDF Review', password_hash=hash_password('Synthetic-PDF-Review-Password-2026!'), tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        now = datetime.now(timezone.utc)
        db.add(Subscription(gym_id='synthetic-pdf-review-owner', plan='clinica', status='active', current_period_start=now - timedelta(days=1), current_period_end=now + timedelta(days=30)))
        db.add(Cliente(id_cliente='synthetic-pdf-review-client', gym_id='synthetic-pdf-review-owner', nombre='Synthetic PDF Client', edad=30, sexo='M', peso_kg=75, estatura_cm=175, objetivo='mantenimiento', nivel_actividad='moderada', activo=True))
        db.commit()
    import uvicorn
    from web.main_web import create_app
    root = Path(__file__).resolve().parents[2]
    source_names = ['web/database/models.py', 'web/routes/planes.py', 'web/templates/planes.html', 'web/static/js/api.js', 'tests/e2e/gym_generation_pdf_review_server.py']
    print(json.dumps({'fixture': 'independent-old-new-pdf', 'tables': 24, 'temporary_root': str(temporary_root), 'catalog_seed': 'persisted active Clinic, no provider IDs', 'sources': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source_names}}), flush=True)
    uvicorn.run(create_app(), host='127.0.0.1', port=8769, log_level='warning')


if __name__ == '__main__':
    main()
