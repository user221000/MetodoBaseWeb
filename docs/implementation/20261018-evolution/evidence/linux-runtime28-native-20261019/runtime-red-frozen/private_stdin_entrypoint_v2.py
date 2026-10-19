"""Prepared launcher: consumes private stdin once, then execs unchanged product CLI."""
import argparse, json, os, re, struct, sys
from urllib.parse import urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode', choices=['migrate', 'web'])
args = parser.parse_args()
required = {'WEB_SECRET_KEY', 'METODO_BASE_SALT', 'DATABASE_URL', 'MIGRATOR_DATABASE_URL',
            'STRIPE_SECRET_KEY', 'STRIPE_PUBLISHABLE_KEY', 'STRIPE_WEBHOOK_SECRET',
            'STRIPE_PRICE_STANDARD', 'STRIPE_PRICE_GYM_COMERCIAL', 'STRIPE_PRICE_CLINICA', 'STRIPE_PRICE_PRO_USUARIO'}
header = sys.stdin.buffer.read(4)
assert len(header) == 4, 'Private frame header incomplete'
size = struct.unpack('!I', header)[0]
assert 1 <= size <= 65536, 'Private bootstrap frame too large'
raw = sys.stdin.buffer.read(size)
assert len(raw) == size, 'Private frame incomplete'
values = json.loads(raw)
assert isinstance(values, dict) and set(values) == required, 'Unexpected private bootstrap fields'
assert all(isinstance(v, str) and v and not any(c in v for c in ['\0', '\n', '\r']) for v in values.values()), 'Invalid private field encoding'
app, migrator = (urlsplit(values[key]) for key in ['DATABASE_URL', 'MIGRATOR_DATABASE_URL'])
for url in [app, migrator]:
    assert url.scheme == 'postgresql+psycopg2' and url.hostname == '172.30.28.1' and url.port == 15483
    assert re.fullmatch(r'/metodobase_test_runtime28_[0-9a-f]{32}', url.path)
    assert url.username and url.password and not url.query and not url.fragment
assert app.path == migrator.path
assert re.fullmatch(r'mb28_a_[0-9a-f]{32}', app.username)
assert re.fullmatch(r'mb28_m_[0-9a-f]{32}', migrator.username)
assert app.username != migrator.username
# Synthetic QA values are structurally accepted by production validators; they
# do not authenticate to any provider. The network gate must already be proven.
assert values['STRIPE_SECRET_KEY'].startswith('sk_live_lab28_')
assert values['STRIPE_PUBLISHABLE_KEY'].startswith('pk_live_lab28_')
assert values['STRIPE_WEBHOOK_SECRET'].startswith('whsec_lab28_')
assert all(values[key].startswith('price_lab28_') for key in required if key.startswith('STRIPE_PRICE_'))
environment = {key: os.environ[key] for key in ['PATH', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED'] if key in os.environ}
environment.update(METODOBASE_ENV='production', METODOBASE_DATA_DIR='/data', PORT='8000', WEB_WORKERS='2',
                   BASE_URL='https://metodobase-runtime28.example.test',
                   CORS_ORIGINS='https://metodobase-runtime28.example.test',
                   REDIS_URL='redis://172.30.28.1:16379/15',
                   OBJECT_STORAGE_BACKEND='local', OBJECT_STORAGE_LOCAL_ROOT='/data/private-objects',
                   DB_MIGRATION_PHASE='4', FEATURE_FLAGS_STRICT='true')
environment.update(values)
os.environ.clear()
os.environ.update(environment)
from config.settings import get_settings
settings = get_settings()
assert settings.is_production and settings.ENV == 'production'
assert 'RAILWAY_ENVIRONMENT' not in os.environ
print(json.dumps({'production_settings_validated': True, 'mode': args.mode,
                  'provider_credentials': 'synthetic QA only; provider authentication not tested',
                  'secrets_emitted': False}), flush=True)
if args.mode == 'migrate':
    os.execve(sys.executable, [sys.executable, '-B', '/app/db_bootstrap.py'], os.environ)
else:
    os.execve('/app/entrypoint.sh', ['/app/entrypoint.sh'], os.environ)
