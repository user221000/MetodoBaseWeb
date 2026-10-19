"""Public landing fixture: own ephemeral SQLite and loopback only; no accounts/providers."""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets, prepare_environment


def main():
    root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    os.environ['BASE_URL'] = 'http://127.0.0.1:8793'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8793,http://testserver'
    from web.database.engine import get_engine
    from web.database.models import Base
    from web.database.schema_control import expected_head
    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(root):
        raise RuntimeError('Own temporary SQLite required')
    Base.metadata.create_all(engine)
    from web.main_web import create_app
    import uvicorn
    source = Path(__file__).resolve().parents[2]
    names = ['web/routes/pages.py','web/templates/landing.html','core/plan_catalog.py',
        'web/static/css/landing.css','web/static/data/landing-example.json','web/main_web.py','api/app.py',
        'web/middleware/security_headers.py','web/database/models.py','web/database/schema_control.py',
        'web/templates/registro.html','tests/e2e/package-lock.json','tests/e2e/landing_server.py']
    print(json.dumps({'fixture':'public-landing','model_target_revision':expected_head(),'tables':len(Base.metadata.tables),
        'preparation':'Own SQLite ORM metadata only, not an executed migration; no account seeded or provider enabled',
        'sources':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names if (source/name).is_file()}}),flush=True)
    uvicorn.run(create_app(),host='127.0.0.1',port=8793,log_level='warning')


if __name__ == '__main__':
    main()
