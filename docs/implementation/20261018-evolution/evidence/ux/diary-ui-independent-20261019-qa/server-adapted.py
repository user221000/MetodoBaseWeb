"""Own head27 UI fixture: real HTTP registration, auth, quota, worker and diary.

Only welcome delivery is replaced by a no-send boundary double. All storage is
temporary and all non-loopback sockets are blocked before product imports.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.request import build_opener, ProxyHandler, Request

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets, prepare_environment


def main():
    for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','PYTEST_XDIST_WORKER'):
        os.environ.pop(key, None)
    temporary_root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    base = 'http://127.0.0.1:8778'
    os.environ['BASE_URL'] = base
    os.environ['CORS_ORIGINS'] = base+',http://testserver'
    from sqlalchemy.orm import Session
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, Cliente, PlanGenerado, Subscription, Usuario, UserRole
    from web.services import email_service
    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(temporary_root):
        raise RuntimeError('Diary UI requires its own temporary SQLite')
    Base.metadata.create_all(engine)
    password = 'Synthetic-Diary-Password-2026!'
    hashed = hash_password(password)
    email_service.send_welcome = lambda *_args, **_kwargs: {'success':True,'delivery':'synthetic_not_sent'}
    with Session(engine) as db:
        db.add(Usuario(id='synthetic-diary-parent', email='diary-parent@example.invalid', nombre='Synthetic Professional',
            password_hash=hashed,tipo='gym',role=UserRole.OWNER,activo=True))
        db.add(Usuario(id='synthetic-diary-ambiguous', email='diary-ambiguous@example.invalid', nombre='Synthetic Ambiguous',
            password_hash=hashed,tipo='usuario',role=UserRole.OWNER,activo=True))
        db.commit()
        db.add(Usuario(id='synthetic-diary-member', email='diary-member@example.invalid', nombre='Synthetic Member',
            password_hash=hashed,tipo='gym',role=UserRole.VIEWER,team_gym_id='synthetic-diary-parent',activo=True))
        for identity in ('synthetic-diary-member','synthetic-diary-ambiguous'):
            db.add(Cliente(id_cliente=identity+'-profile',gym_id=identity,nombre='Synthetic Profile',edad=30,
                peso_kg=75,estatura_cm=175,sexo='M',objetivo='mantenimiento',nivel_actividad='moderada'))
        db.add(Cliente(id_cliente='synthetic-diary-parent-portfolio',gym_id='synthetic-diary-parent',nombre='Synthetic Professional Portfolio'))
        db.flush()
        db.add(PlanGenerado(gym_id='synthetic-diary-ambiguous',id_cliente='synthetic-diary-ambiguous-profile',
            plan_json='{"synthetic_professional_portfolio":{"marker":"MUST_NOT_ADOPT"}}'))
        db.add(Subscription(gym_id='synthetic-diary-member',plan='pro_usuario',status='active',
            current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.commit()
    import uvicorn
    from web.main_web import create_app
    server = uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=8778,log_level='warning'))
    thread = threading.Thread(target=server.run,daemon=True)
    thread.start()
    for _ in range(200):
        if server.started: break
        if not thread.is_alive(): raise RuntimeError('Own diary fixture failed to start')
        time.sleep(0.05)
    if not server.started: raise RuntimeError('Own diary fixture was not ready')
    opener = build_opener(ProxyHandler({}))
    def call(path, payload, token=None, method='POST'):
        headers = {'Content-Type':'application/json'}
        if token: headers['Authorization'] = 'Bearer '+token
        request = Request(base+path,data=json.dumps(payload).encode(),headers=headers,method=method)
        with opener.open(request,timeout=10) as response:
            if response.status != 200: raise RuntimeError('Own HTTP fixture preparation failed')
            return json.load(response)
    for suffix in ('primary','other'):
        registered = call('/api/auth/registro',{'email':'diary-'+suffix+'@example.invalid','password':password,
            'nombre':'Synthetic '+suffix,'tipo':'usuario'})
        call('/api/usuario/perfil',{'edad':30,'peso_kg':75,'estatura_cm':175,'sexo':'M',
            'objetivo':'mantenimiento','nivel_actividad':'moderada'},registered['token'],'PUT')
        with Session(engine) as db:
            account = db.query(Usuario).filter_by(email='diary-'+suffix+'@example.invalid').one()
            if account.role != UserRole.VIEWER or account.tipo != 'usuario':
                raise RuntimeError('Real registration must persist an unambiguous personal VIEWER')
            db.add(Subscription(gym_id=account.id,plan='pro_usuario',status='active',
                current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
            db.commit()
    root = Path(__file__).resolve().parents[2]
    names = ['web/database/models.py','web/database/engine.py','web/database/schema_control.py','web/database/tenant_policy.py',
        'web/routes/personal_diary.py','web/services/personal_diary_persistence.py','web/services/personal_diary_service.py',
        'web/personal_diary_schemas.py','web/routes/privacy.py','web/services/privacy_export.py','web/routes/usuario.py',
        'web/services/generation_quota.py','web/services/plan_generation.py','web/services/plan_documents.py',
        'web/routes/auth.py','web/auth.py','web/auth_deps.py','web/main_web.py','web/middleware/security_headers.py',
        'web/storage/configuration.py','web/storage/runtime.py','web/storage/objects.py','web/storage/local.py',
        'requirements_web.lock','requirements_web-windows.lock','requirements-test.lock','requirements-test-windows.lock',
        'web/templates/base_usuario.html','web/templates/usuario_mi_plan.html','web/templates/usuario_historial.html',
        'web/static/js/api.js','web/static/js/usuario-diario.js','web/static/js/usuario-privacidad.js',
        'web/static/js/usuario-plan-operacion.js','web/static/js/auth-guard.js','web/static/js/dialog-focus.js',
        'web/static/css/styles-usuario.css','tests/e2e/personal_diary_server.py','tests/e2e/personal_diary.cjs',
        'tests/e2e/personal_diary_controller.cjs','tests/e2e/personal_diary_api.cjs','tests/e2e/personal_logout.cjs']
    print(json.dumps({'fixture':'personal-diary-ui','model_target_revision':'20261019_personal_diary',
        'tables':len(Base.metadata.tables),'preparation':'own metadata-only SQLite and local objects; two VIEWER accounts registered through real loopback HTTP',
        'mail':'no-send boundary double','sources':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}}),flush=True)
    thread.join()


if __name__ == '__main__':
    main()
