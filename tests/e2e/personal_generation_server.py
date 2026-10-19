"""Own worktree browser fixture: real auth/quota/worker, temporary SQLite/objects."""
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
    os.environ['BASE_URL'] = 'http://127.0.0.1:8773'
    os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:8773,http://testserver'
    from sqlalchemy.orm import Session
    from web.auth import hash_password
    from web.database.engine import get_engine
    from web.database.models import Base, Cliente, Subscription, Usuario, UserRole, UserSubscription
    from web.services.billing_integrity import current_quota_period
    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(temporary_root):
        raise RuntimeError('Personal UI fixture requires its own temporary SQLite')
    Base.metadata.create_all(engine)
    password = hash_password('Synthetic-Personal-Password-2026!')
    with Session(engine) as db:
        for suffix in ('owner','other','quota','member','failure'):
            db.add(Usuario(id='synthetic-personal-'+suffix, email='personal-'+suffix+'@example.invalid',
                nombre='Synthetic '+suffix, password_hash=password, tipo='usuario', role=UserRole.OWNER, activo=True))
        db.add(Usuario(id='synthetic-professional-parent', email='personal-parent@example.invalid',
            nombre='Synthetic Professional', password_hash=password, tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        member = db.get(Usuario, 'synthetic-personal-member')
        member.tipo = 'gym'; member.role = UserRole.VIEWER; member.team_gym_id = 'synthetic-professional-parent'
        for suffix in ('owner','other','quota','member','failure'):
            db.add(Cliente(id_cliente='synthetic-personal-profile-'+suffix, gym_id='synthetic-personal-'+suffix,
                nombre='Synthetic '+suffix, edad=30, peso_kg=75, estatura_cm=175, sexo='M',
                objetivo='mantenimiento', nivel_actividad='moderada', activo=True))
        for suffix in ('owner','other','member'):
            db.add(Subscription(gym_id='synthetic-personal-'+suffix, plan='pro_usuario', status='active',
                current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.add(UserSubscription(user_id='synthetic-personal-quota', plan='starter', status='active',
            max_planes_mes=1, planes_usados_mes=1, mes_actual=current_quota_period()))
        db.commit()
    import uvicorn
    from web.main_web import create_app
    root = Path(__file__).resolve().parents[2]
    sources = ['web/database/models.py','web/database/engine.py','web/database/repository.py','web/services/generation_quota.py',
        'web/services/plan_generation.py','web/services/billing_integrity.py','web/services/plan_documents.py','web/routes/usuario.py',
        'web/routes/planes.py','web/routes/auth.py','web/auth.py','web/auth_deps.py','web/main_web.py','web/middleware/security_headers.py',
        'web/storage/configuration.py','web/storage/runtime.py','web/storage/objects.py','web/storage/local.py',
        'requirements_web.lock','requirements_web-windows.lock','requirements-test.lock','requirements-test-windows.lock']
    print(json.dumps({'fixture':'personal-generation-worktree','tables':len(Base.metadata.tables),
        'model_target_revision':'20261018_individual_publication', 'preparation':'metadata-only synthetic fixture',
        'database':'own-temporary-sqlite','objects':'own-temporary-local','sources':{
        name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}}), flush=True)
    uvicorn.run(create_app(), host='127.0.0.1', port=8773, log_level='warning')


if __name__ == '__main__':
    main()
