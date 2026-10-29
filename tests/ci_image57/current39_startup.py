"""Start the explicit current57 image against a fresh synthetic PostgreSQL39.

This separate Linux gate preserves all historical33 browser sources. It verifies
the real SaaS entrypoint and restricted schema39; it does not accept browsers,
external providers, production configuration or SBOM/SCA.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import ProxyHandler, build_opener

from tests.isolation import validate_postgres_test_url

from . import authority, context

ROOT = Path(__file__).resolve().parents[2]
REVISION = '20261023_privacy_disposition'
IMAGE_PATTERN = r'sha256:[0-9a-f]{64}'
OWNER_LABEL = 'metodobase.ci39.startup'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def database_configuration(environment):
    """Only the dedicated fresh CI image service; never use DATABASE_URL."""
    values = {}
    for key in ('METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL'):
        value = environment[key]
        require(type(value) is str and all(32 <= ord(char) < 127 for char in value),
                'Synthetic connection values cannot contain control characters')
        validate_postgres_test_url(value)
        parsed = urlsplit(value)
        require(parsed.hostname == '127.0.0.1' and parsed.port == 55483
                and parsed.path == '/metodobase_test_image' and bool(parsed.password),
                'The dedicated loopback image database is required')
        values[key] = value
    admin, app = (urlsplit(values[key]) for key in values)
    require(unquote(admin.username or '') == 'metodobase_test_admin'
            and unquote(app.username or '') == 'metodobase_test_app',
            'Separate synthetic image roles are required')
    return values


def validate_image(value, image_id, source):
    require(re.fullmatch(IMAGE_PATTERN, image_id) is not None,
            'An immutable image ID is required')
    require(type(value) is dict and value.get('Id') == image_id
            and value.get('Config', {}).get('Labels', {}).get('org.opencontainers.image.revision') == source,
            'Current image source or immutable identity differs')
    require(value['Config'].get('Cmd') == ['/app/entrypoint.sh']
            and value['Config'].get('Entrypoint') in (None, [])
            and value['Config'].get('User') in ('appuser', '999', '999:999'),
            'Current image SaaS command or nonroot user differs')


def validate_container(value, container_id, image_id, owner):
    require(type(container_id) is str and re.fullmatch(r'[0-9a-f]{64}', container_id) is not None,
            'The owned container ID is required')
    require(value.get('Id') == container_id and value.get('Image') == image_id
            and value.get('Config', {}).get('Labels', {}).get(OWNER_LABEL) == owner,
            'Container ownership or image identity differs')
    host = value.get('HostConfig', {})
    limits = {'Memory': 512 * 1024**2, 'NanoCpus': 1000000000, 'PidsLimit': 128,
              'ReadonlyRootfs': True, 'NetworkMode': 'host', 'PidMode': '',
              'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges:true']}
    require(all(type(host.get(key)) is type(expected) and host[key] == expected
                for key, expected in limits.items()), 'The owned startup isolation or limits differ')
    state = value.get('State', {})
    require(type(state.get('Running')) is bool and type(state.get('ExitCode')) is int,
            'The owned container state is not typed')


def validate_ready(status, content_type, raw, url):
    require(status == 200 and url == 'http://127.0.0.1:8765/health/ready'
            and content_type.split(';', 1)[0].strip().lower() == 'application/json'
            and len(raw) <= 1024, 'The actual readiness response differs')
    value = context.json_object(raw)
    require(type(value) is dict and set(value) == {'ready'} and value['ready'] is True,
            'The database readiness observation is not true')


WITNESS = br'''import hashlib,json,os
from pathlib import Path
from urllib.request import ProxyHandler,build_opener
from sqlalchemy import inspect,text
from web.database.models import Base
from web.database.engine import get_engine
from web.database.schema_control import expected_head,verify_runtime_schema
assert expected_head()=='20261023_privacy_disposition'
assert len(Base.metadata.tables)==44
assert os.getuid()==999 and 'MIGRATOR_DATABASE_URL' not in os.environ
parent=Path('/proc/1')
assert b'MIGRATOR_DATABASE_URL=' not in (parent/'environ').read_bytes()
assert b'web/main_web.py' in (parent/'cmdline').read_bytes()
def owned_listener():
    owned=set()
    for path in (parent/'fd').iterdir():
        try:
            target=os.readlink(path)
        except FileNotFoundError:
            continue
        if target.startswith('socket:['):
            owned.add(target[8:-1])
    listeners=set()
    for table in ('/proc/net/tcp','/proc/net/tcp6'):
        for line in Path(table).read_text().splitlines()[1:]:
            row=line.split()
            if row[3]=='0A' and int(row[1].rsplit(':',1)[1],16)==8765 and row[9] in owned:
                listeners.add(row[9])
    assert listeners
    return listeners
before_listener=owned_listener()
with build_opener(ProxyHandler({})).open('http://127.0.0.1:8765/health/ready',timeout=5) as response:
    body=response.read(1025)
    assert response.status==200 and response.geturl()=='http://127.0.0.1:8765/health/ready'
    assert response.headers.get_content_type()=='application/json' and len(body)<=1024
    assert json.loads(body)=={'ready':True} and type(json.loads(body)['ready']) is bool
assert owned_listener()==before_listener
status=dict(line.split(':',1) for line in (parent/'status').read_text().splitlines() if ':' in line)
assert status['NoNewPrivs'].strip()=='1' and int(status['CapEff'].strip(),16)==0
engine=get_engine()
assert engine.pool.size()==1 and engine.pool._max_overflow==0
verify_runtime_schema(engine,expected_revision='20261023_privacy_disposition')
with engine.connect() as db:
    tables=set(inspect(db).get_table_names())
    assert tables==set(Base.metadata.tables)|{'alembic_version'} and len(tables)==45
    assert db.scalar(text('SELECT version_num FROM alembic_version'))=='20261023_privacy_disposition'
    flags=tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') FROM pg_roles WHERE rolname=current_user")).one())
    assert flags==(False,)*5
    assert db.scalar(text('SELECT datdba<>(SELECT oid FROM pg_roles WHERE rolname=current_user) FROM pg_database WHERE datname=current_database()')) is True
    owned=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)"))
    assert owned==0
    force=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
    assert force==35
engine.dispose()
files={p.relative_to('/app').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').rglob('*') if p.is_file()}
print(json.dumps({'revision':expected_head(),'ORM_tables':44,'physical_tables':45,'FORCE_RLS':force,'role_five_flags':list(flags),'owned_tables':owned,'uid':os.getuid(),'pid1_main_web':True,'pid1_owns_ready_listener':True,'owned_ready_HTTP_200':True,'migrator_absent':True,'no_new_privileges':True,'effective_capabilities':0,'pool_size':1,'max_overflow':0,'source_hashes':files}))
'''


def validate_witness(value, contract):
    exact = {'revision': REVISION, 'ORM_tables': 44, 'physical_tables': 45, 'FORCE_RLS': 35,
             'role_five_flags': [False] * 5, 'owned_tables': 0, 'uid': 999,
             'pid1_main_web': True, 'migrator_absent': True, 'no_new_privileges': True,
             'pid1_owns_ready_listener': True, 'owned_ready_HTTP_200': True,
             'effective_capabilities': 0, 'pool_size': 1, 'max_overflow': 0}
    require(type(value) is dict and set(value) == set(exact) | {'source_hashes'},
            'The complete current39 startup witness is required')
    for name, expected in exact.items():
        require(type(value[name]) is type(expected) and value[name] == expected,
                'A typed current39 schema or privilege observation differs')
    require(all(type(flag) is bool for flag in value['role_five_flags'])
            and value['source_hashes'] == contract['app_hashes'],
            'Current39 roles or complete source inventory differs')


def execute(argv, private, name, *, stdin=None, timeout=180):
    with (private / (name + '.stdout.private')).open('xb') as output, \
            (private / (name + '.stderr.private')).open('xb') as errors:
        result = subprocess.run(argv, cwd=ROOT, input=stdin, stdout=output, stderr=errors,
                                timeout=timeout, check=False)
    require(result.returncode == 0, 'An owned startup command failed; private originals retained')
    return (private / (name + '.stdout.private')).read_bytes()


def inspect_one(docker, kind, target, private, name):
    values = context.json_object(execute([docker, kind, 'inspect', target], private, name))
    require(type(values) is list and len(values) == 1, 'One exact Docker object is required')
    return values[0]


@contextmanager
def container(docker, image_id, private, name, envfile, *, command=()):
    owner = uuid.uuid4().hex
    cidfile = private / (name + '-cid.private.txt')
    container_id = None
    try:
        argv = [docker, 'create', '--cidfile', str(cidfile), '--name', 'metodobase-ci39-' + owner,
                '--label', OWNER_LABEL + '=' + owner, '--network', 'host', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges:true', '--read-only',
                '--memory', '512m', '--cpus', '1', '--pids-limit', '128',
                '--tmpfs', '/data:rw,nosuid,nodev,mode=1777',
                '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777', '--env-file', str(envfile)]
        if command:
            argv += ['--entrypoint', 'python']
        raw = execute([*argv, image_id, *command], private, name + '-create')
        container_id = raw.decode('ascii').strip()
        before = inspect_one(docker, 'container', container_id, private, name + '-before')
        validate_container(before, container_id, image_id, owner)
        execute([docker, 'start', container_id], private, name + '-start')
        yield container_id
    finally:
        if container_id is None and cidfile.exists():
            authority.regular_file(cidfile)
            container_id = cidfile.read_text(encoding='ascii').strip()
        if container_id is not None:
            current = inspect_one(docker, 'container', container_id, private, name + '-cleanup-before')
            validate_container(current, container_id, image_id, owner)
            if current['State']['Running'] is True:
                execute([docker, 'stop', '--time', '30', container_id], private, name + '-stop', timeout=60)
            execute([docker, 'logs', container_id], private, name + '-closed-logs')
            closed = inspect_one(docker, 'container', container_id, private, name + '-closed')
            validate_container(closed, container_id, image_id, owner)
            require(closed['State']['Running'] is False and closed['State']['ExitCode'] == 0,
                    'The owned container did not close normally')
            execute([docker, 'rm', container_id], private, name + '-remove')


def run(contract, image_id, private, environment, docker):
    require(os.name == 'posix', 'Current39 startup requires a coordinated Linux Docker runner')
    require(re.fullmatch(IMAGE_PATTERN, image_id) is not None, 'An immutable image ID is required')
    configuration = database_configuration(environment)
    image = inspect_one(docker, 'image', image_id, private, 'image-before')
    validate_image(image, image_id, contract['source'])
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 8765))
    runtime = {'METODOBASE_ENV': 'testing', 'PYTHON_DOTENV_DISABLED': '1',
        'DATABASE_URL': configuration['METODOBASE_TEST_POSTGRES_URL'],
        'WEB_SECRET_KEY': base64.urlsafe_b64encode(os.urandom(48)).decode(),
        'MFA_ENCRYPTION_KEY': base64.urlsafe_b64encode(os.urandom(32)).decode(),
        'METODOBASE_DATA_DIR': '/data', 'OBJECT_STORAGE_BACKEND': 'local',
        'OBJECT_STORAGE_LOCAL_ROOT': '/tmp/current39-objects', 'METODOBASE_SEED_DEMO': '0',
        'PORT': '8765', 'BASE_URL': 'http://127.0.0.1:8765', 'CORS_ORIGINS': 'http://127.0.0.1:8765',
        'RATE_LIMIT_ENABLED': 'true', 'WEB_WORKERS': '1', 'DB_POOL_SIZE': '1', 'DB_MAX_OVERFLOW': '0',
        'RAILWAY_ENVIRONMENT': 'ci39-synthetic'}
    bootstrap = dict(runtime, MIGRATOR_DATABASE_URL=configuration['METODOBASE_TEST_MIGRATOR_URL'])
    for name, values in (('runtime', runtime), ('bootstrap', bootstrap)):
        with (private / (name + '.env.private')).open('x', encoding='utf8') as stream:
            stream.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
        (private / (name + '.env.private')).chmod(0o600)
    child_env = dict(environment, **configuration)
    for stage in ('before', 'after'):
        # Original role helper is independent of schema revision; preserve it.
        with (private / ('roles-' + stage + '.private.log')).open('xb') as log:
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                str(ROOT / 'tests/ci_google33/image_roles.py'), stage], cwd=ROOT,
                env=child_env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=False)
        require(result.returncode == 0, 'Fresh restricted image role setup failed')
        if stage == 'before':
            with container(docker, image_id, private, 'bootstrap', private / 'bootstrap.env.private',
                           command=('/app/db_bootstrap.py',)) as owned:
                result = execute([docker, 'wait', owned], private, 'bootstrap-wait', timeout=300)
                require(result.strip() == b'0', 'Image migration did not complete successfully')
    with container(docker, image_id, private, 'runtime', private / 'runtime.env.private') as owned:
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            observed = inspect_one(docker, 'container', owned, private, 'ready-inspect-' + uuid.uuid4().hex)
            require(observed['State']['Running'] is True, 'Owned SaaS stopped before readiness')
            try:
                with opener.open('http://127.0.0.1:8765/health/ready', timeout=1) as response:
                    if response.status == 200:
                        raw = response.read(1025)
                        (private / 'ready-response.private.json').write_bytes(raw)
                        validate_ready(response.status, response.headers.get('Content-Type', ''),
                                       raw, response.geturl())
                        break
            except OSError:
                time.sleep(.25)
        else:
            raise TimeoutError('Current39 SaaS readiness was not observed')
        (private / 'current39-witness.raw.py').write_bytes(WITNESS)
        raw = execute([docker, 'exec', '-i', owned, 'python', '-'], private, 'current39-witness', stdin=WITNESS)
        validate_witness(context.json_object(raw), contract)
    validate_image(inspect_one(docker, 'image', image_id, private, 'image-after'), image_id, contract['source'])
    return {'accepted': True, 'source': contract['source'], 'image_id': image_id,
            'revision': REVISION, 'ORM_tables': 44, 'physical_tables': 45, 'FORCE_RLS': 35,
            'restricted_nonowner': True, 'actual_main_web_entrypoint': True,
            'ready_HTTP_200': True, 'PID1_listener_and_readiness_bound': True,
            'normal_container_closure': True,
            'environment': 'synthetic_testing', 'browser_executed': False,
            'production_settings_accepted': False, 'SBOM_SCA_complete': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args(argv)
    authority.regular_file(args.contract)
    require(args.contract.stat().st_size <= 8 * 1024**2, 'Bounded current57 contract required')
    raw = args.contract.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == args.contract_sha256, 'Current57 contract hash differs')
    contract = context.json_object(raw)
    context.validate_contract(args.contract.parent, contract)
    require(args.output.is_absolute() and not args.output.exists()
            and not args.output.resolve().is_relative_to(ROOT)
            and not args.output.resolve().is_relative_to(args.private.resolve()),
            'Fresh public output outside source/private evidence is required')
    authority.regular_directory(args.output.parent)
    authority.private_directory(args.private, ROOT)
    evidence = authority.evidence()
    acl = evidence['boundary_before_payload'](args.private)
    try:
        result = run(contract, args.image_id, args.private, dict(os.environ), args.docker)
        require(args.contract.read_bytes() == raw, 'The current57 contract changed during startup')
        context.validate_contract(args.contract.parent, contract)
    except Exception as error:  # noqa: BLE001 -- seal rejected real gates without exposing credentials
        (args.private / 'failure.private.log').write_text(traceback.format_exc(), encoding='utf8')
        result = {'accepted': False, 'error_class': type(error).__name__, 'source': contract['source'],
                  'actual_startup_accepted': False, 'SBOM_SCA_complete': False}
    evidence['seal'](args.private, args.output, result, acl)
    print(json.dumps(result))
    return int(not result['accepted'])


if __name__ == '__main__':
    raise SystemExit(main())
