"""Only synthetic local recovery UI: real auth/DB, mail acceptance port offline."""
from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import sys

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets,prepare_environment


def main():
    for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','PYTEST_XDIST_WORKER'):
        os.environ.pop(key,None)
    root=prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    os.environ['BASE_URL']='http://127.0.0.1:8784'
    os.environ['CORS_ORIGINS']='http://127.0.0.1:8784,http://testserver'
    from sqlalchemy.orm import Session
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import Base,Usuario,UserRole
    from web.services import email_service
    from web.services.password_recovery import digest
    from web.settings import get_settings
    engine=get_engine()
    if engine.dialect.name!='sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(root):
        raise RuntimeError('Recovery browser fixture requires its own temporary SQLite')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Usuario(id='browser-recovery',email='recovery-browser@example.invalid',nombre='Synthetic',
            tipo='usuario',role=UserRole.VIEWER,activo=True,password_hash=auth.hash_password('SyntheticOldPassword123'),
            password_reset_hash=digest('b'*43),password_reset_session_version=0,
            password_reset_expires_at=datetime.now(timezone.utc)+timedelta(minutes=15)))
        db.commit()
    # Acceptance is a synthetic mail port, never a delivery/provider claim.
    email_service.send_password_reset=lambda *args:True
    email_service.send_password_changed=lambda *args:True
    get_settings().RESEND_API_KEY='synthetic-not-used-with-provider'
    def forbidden(*args,**kwargs): raise AssertionError('Real transport forbidden')
    email_service._send=forbidden
    import uvicorn
    from web.main_web import create_app
    uvicorn.run(create_app(),host='127.0.0.1',port=8784,log_level='warning',access_log=False)


if __name__=='__main__': main()
