import os, sys, pathlib, socket, tempfile
root = pathlib.Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
qa = pathlib.Path(tempfile.mkdtemp(prefix='metodobase-qa-'))
qa.mkdir(parents=True, exist_ok=True)
for dirname in ('home', 'appdata', 'localappdata', 'config', 'registros', 'output', 'planes'):
    (qa / dirname).mkdir(exist_ok=True)
for key in list(os.environ):
    if any(part in key.upper() for part in ('STRIPE', 'MERCADOPAGO', 'RESEND', 'SMTP', 'SENTRY', 'RAILWAY', 'REDIS', 'DATABASE_URL')):
        os.environ[key] = ''
os.environ.update({
    'METODOBASE_ENV':'testing', 'METODOBASE_DATA_DIR':str(qa),
    'METODOBASE_TEST_CONFIG':str(qa / 'config'), 'APPDATA':str(qa/'appdata'),
    'LOCALAPPDATA':str(qa/'localappdata'), 'USERPROFILE':str(qa/'home'),
    'DATABASE_URL':'sqlite:///' + (qa/'qa.db').as_posix(),
    'DB_PATH':str(qa/'legacy.db'), 'WEB_SECRET_KEY':'audit-local-only-secret-at-least-thirty-two-characters',
    'METODO_BASE_SALT':'audit-local-only-salt', 'RATE_LIMIT_ENABLED':'false',
    'METRICS_ENABLED':'false', 'ALERT_ENABLED':'false', 'QT_QPA_PLATFORM':'offscreen',
    'SENTRY_DSN':'', 'RESEND_API_KEY':'', 'REDIS_URL':'',
    'STRIPE_SECRET_KEY':'', 'STRIPE_WEBHOOK_SECRET':'', 'MERCADOPAGO_ACCESS_TOKEN':'',
    'MERCADOPAGO_WEBHOOK_SECRET':'', 'METODOBASE_SEED_DEMO':'0',
    'PYTHONIOENCODING':'utf-8', 'PYTHONDONTWRITEBYTECODE':'1',
})
os.chdir(root)
sys.path.insert(0, str(root))
_original_connect=socket.socket.connect
def offline_connect(sock, address):
    if isinstance(address,tuple) and address[0] not in ('127.0.0.1','localhost','::1'):
        raise RuntimeError('QA offline harness blocked outbound connection')
    return _original_connect(sock,address)
socket.socket.connect=offline_connect
if '--seed-schema' in sys.argv:
    sys.argv.remove('--seed-schema')
    from web.database.engine import init_db, get_engine
    from web.database.models import Base
    init_db(); Base.metadata.create_all(get_engine())
if '--serve-web' in sys.argv:
    import uvicorn
    from web.main_web import create_app
    uvicorn.run(create_app(),host='127.0.0.1',port=8765,log_level='warning')
else:
    import pytest
    raise SystemExit(pytest.main(sys.argv[1:]))


