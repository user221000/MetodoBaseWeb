"""Own loopback UI/auth fixture, base28. Browser R12 endpoints are explicit doubles."""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets, prepare_environment


def main():
    own = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    os.environ['BASE_URL'] = 'http://127.0.0.1:8782'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8782,http://testserver'
    from web.database.engine import get_engine
    from web.database.models import Base
    from web.database.schema_control import expected_head
    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(own):
        raise RuntimeError('Own ephemeral SQLite required')
    Base.metadata.create_all(engine)
    from web.main_web import create_app
    import uvicorn
    source = Path(__file__).resolve().parents[2]
    paths = ['web/routes/pages.py','web/static/js/api.js','web/static/js/vinculos-contexto.js',
        'web/static/js/vinculos-ui.js','web/static/js/vinculos-invitacion.js','web/static/js/vinculos-profesional.js',
        'web/static/js/vinculos-lectura.js','web/templates/accept_client_link.html','web/templates/cliente_vinculacion.html',
        'web/templates/usuario_vinculos.html','web/static/css/vinculos.css','web/database/models.py',
        'web/database/schema_control.py','web/routes/auth.py','web/middleware/security_headers.py',
        'tests/e2e/member_links_ui_server.py']
    print(json.dumps({'fixture':'r12-ui-base28','model_target_revision':expected_head(),'tables':len(Base.metadata.tables),
        'preparation':'Own ORM metadata only, no executed migration; no R12 API29 composed, providers disabled',
        'sources':{p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in paths}}),flush=True)
    uvicorn.run(create_app(),host='127.0.0.1',port=8782,log_level='warning')


if __name__ == '__main__':
    main()
