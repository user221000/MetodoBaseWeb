"""Loopback-only SEC03 fixture: own SQLite/objects, signed auth, no providers."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8774)
parser.add_argument('--source-report', type=Path, required=True)
args = parser.parse_args()
from tests.isolation import prepare_environment, block_external_sockets

for key in ('_METODOBASE_TEST_ROOT', 'METODOBASE_TEST_DATABASE_URL', 'METODOBASE_TEST_REDIS_URL', 'PYTEST_XDIST_WORKER'):
    os.environ.pop(key, None)
temporary = prepare_environment(discard_inherited=True).resolve()
block_external_sockets()
base = f'http://127.0.0.1:{args.port}'
os.environ['BASE_URL'] = base
os.environ['CORS_ORIGINS'] = base + ',http://testserver'
from sqlalchemy.orm import Session
from web.database.engine import get_engine
from web.database.models import Base, Usuario, UserRole
from web.auth import hash_password

engine = get_engine()
assert engine.dialect.name == 'sqlite' and Path(engine.url.database).resolve().is_relative_to(temporary)
Base.metadata.create_all(engine)
with Session(engine) as db:
    for suffix in ('owner', 'other'):
        db.add(Usuario(id='synthetic-drawer-' + suffix, email='drawer-' + suffix + '@example.invalid',
            nombre='Synthetic ' + suffix, apellido='', password_hash=hash_password('Synthetic-Drawer-Only-2026!'),
            tipo='gym', role=UserRole.OWNER, activo=True))
    db.commit()
from web.main_web import create_app

sources = ['web/templates/dashboard.html', 'web/static/js/main.js', 'web/static/js/api.js', 'web/static/js/components.js',
    'web/static/js/auth-guard.js', 'web/routes/clientes.py', 'web/schemas.py', 'api/schemas.py', 'web/profile_schemas.py',
    'web/database/repository.py', 'web/database/models.py', 'web/auth.py', 'web/auth_deps.py', 'web/main_web.py',
    'web/middleware/security_headers.py', 'web/routes/stats.py', 'api/routes/stats.py', 'tests/isolation.py',
    'requirements_web-windows.lock', 'requirements-test-windows.lock',
    'tests/e2e/dashboard_drawer_security_server.py', 'tests/e2e/dashboard_drawer_security.cjs']
snapshot = {'scope':'Own fixture SQLite/objects; no main stats changes or external providers; real auth/CRUD',
    'tables':len(Base.metadata.tables), 'port':args.port, 'pid':os.getpid(),
    'sources':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in sources}}
args.source_report.write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf8')
print('Dedicated synthetic dashboard fixture ready', flush=True)
import uvicorn
uvicorn.run(create_app(), host='127.0.0.1', port=args.port, log_level='warning')
