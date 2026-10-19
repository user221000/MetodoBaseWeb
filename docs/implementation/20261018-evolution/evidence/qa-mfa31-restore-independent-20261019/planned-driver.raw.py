"""QA-only observer around immutable restore31; sensitive artifacts stay private."""
import argparse, contextlib, ctypes, hashlib, importlib.metadata, json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--reserved-window-ack', action='store_true')
args = parser.parse_args()
assert args.reserved_window_ack
ROOT = Path('F:/mb-mfa31-summary-after-qa-20261019')
TEMP = Path(__file__).parent
OUT = Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-mfa31-restore-independent-20261019')
PRIVATE = TEMP/'private'
CONFIG = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
HEAD = '4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae'
SHA = lambda b: hashlib.sha256(b).hexdigest()
PRIVATE.mkdir(exist_ok=False)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
for key in list(os.environ):
    upper = key.upper()
    if upper == 'DATABASE_URL' or upper.endswith('_DATABASE_URL') or upper.startswith(('PG','AWS_','S3_','METODOBASE_TEST_','_METODOBASE_TEST')) or any(x in upper for x in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):
        os.environ.pop(key, None)
os.environ.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url
prepare_environment(discard_inherited=True)
block_external_sockets()
conf = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    os.environ[key] = conf[key]
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
    validate_postgres_test_url(os.environ[key])
os.environ['METODOBASE_TEST_EVIDENCE_DIR'] = str(PRIVATE)
git = lambda *a: subprocess.check_output(['git','--no-replace-objects',*a], cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip() == HEAD
assert not git('status','--porcelain').strip()
names = [n for n in git('ls-files','-co','--exclude-standard','-z').decode().split('\0') if n]
pgbin = Path(conf['METODOBASE_TEST_PG_BIN']).resolve()
def photo():
    return {'head':git('rev-parse','HEAD').decode().strip(), 'sources':{n:SHA((ROOT/n).read_bytes()) for n in names},
            'own_helpers':{p.name:SHA(p.read_bytes()) for p in TEMP.glob('*.py')},
            'packages':sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions()),
            'Python_executable_SHA':SHA(Path(sys.executable).read_bytes()),
            'Python_base_executable_SHA':SHA(Path(sys._base_executable).read_bytes()),
            'private_config_SHA':SHA(CONFIG.read_bytes()),
            'PG_bin_files':{str(p.relative_to(pgbin)):SHA(p.read_bytes()) for p in pgbin.rglob('*') if p.is_file()}}
before = photo()
assert len(before['packages']) == 89
(OUT/'before.json').write_text(json.dumps(before,indent=2)+'\n')
pip = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.log').write_bytes(pip.stdout+pip.stderr)
assert pip.returncode == 0

def birth():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    values = [ctypes.c_ulonglong() for _ in range(4)]
    assert kernel.GetProcessTimes(ctypes.c_void_p(kernel.GetCurrentProcess()), *[ctypes.byref(v) for v in values])
    return datetime.fromtimestamp(values[0].value/10000000-11644473600,timezone.utc).isoformat()
identity = {'pid':os.getpid(),'birth_UTC':birth(),'executable_SHA':SHA(Path(sys.executable).read_bytes()),'driver_SHA':SHA(Path(__file__).read_bytes())}
(OUT/'execution-plan.json').write_text(json.dumps({'identity':identity,'head':HEAD,'two_UUIDs':'Names generated only by immutable historical fixture; observer records both before first CREATE, never overrides UUIDs.',
 'nodeid':'tests/integration_mfa31_restore.py::test_revision31_restore_preserves_mfa_and_all_revision26_27_28_29_30_contracts',
 'transport':'Existing local dedicated PG55483; child-only config; no listener/browser/provider/global roles/HBA',
 'artifacts':'Full log/XML/dumps/objects and configuration remain private; publication uses explicit safe projections and file hashes.'},indent=2)+'\n')

import psycopg2
from psycopg2.extensions import connection as PGConnection, cursor as PGCursor
original_connect = psycopg2.connect
control_dsn = conf['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)
owned = []
events = []
def receipt(event, **fields):
    events.append({'event':event,'at_UTC':datetime.now(timezone.utc).isoformat(),'process':identity,**fields})
    (OUT/'database-observation.json').write_text(json.dumps(events,indent=2)+'\n')
def independent_state(target_names):
    db = original_connect(control_dsn,connect_timeout=5)
    try:
        with db.cursor() as cur:
            cur.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s) ORDER BY datname',(target_names,))
            remaining = [r[0] for r in cur.fetchall()]
            cur.execute('SELECT datname,pid,backend_start,state FROM pg_stat_activity WHERE datname=ANY(%s) ORDER BY datname,pid',(target_names,))
            sessions = [{'database':r[0],'backend_pid':r[1],'birth_UTC':r[2].isoformat(),'state':r[3]} for r in cur.fetchall()]
        return {'remaining':remaining,'sessions':sessions}
    finally:
        db.close()
class ObserverCursor(PGCursor):
    def execute(self, query, vars=None):
        rendered = query.as_string(self.connection) if hasattr(query,'as_string') else query
        if isinstance(rendered,bytes):
            rendered = rendered.decode('utf8')
        create = re.fullmatch(r'CREATE DATABASE "(metodobase_test_(?:backup|restore)_[0-9a-f]{12})"',rendered or '')
        drop = re.fullmatch(r'DROP DATABASE IF EXISTS "(metodobase_test_(?:backup|restore)_[0-9a-f]{12})" WITH \(FORCE\)',rendered or '')
        if create:
            name = create.group(1)
            if not owned:
                assert name.startswith('metodobase_test_backup_')
                token = name.removeprefix('metodobase_test_backup_')
                owned.extend(['metodobase_test_backup_'+token,'metodobase_test_restore_'+token])
                state = independent_state(owned)
                assert state == {'remaining':[],'sessions':[]}
                receipt('planned-before-first-CREATE',names=list(owned),state=state)
            assert name in owned and not any(e['event']=='created-immediate' and e['name']==name for e in events)
            receipt('before-CREATE',name=name)
            result = super().execute(query,vars)
            state = independent_state([name])
            assert state['remaining'] == [name] and state['sessions'] == []
            receipt('created-immediate',name=name,state=state)
            return result
        if drop:
            name = drop.group(1)
            assert name in owned
            state = independent_state([name])
            receipt('before-exact-DROP',name=name,state=state,forced_if_sessions_present=bool(state['sessions']))
            result = super().execute(query,vars)
            closed = independent_state([name])
            receipt('after-exact-DROP-independent-connection',name=name,state=closed)
            assert closed == {'remaining':[],'sessions':[]}
            return result
        return super().execute(query,vars)
class ObserverConnection(PGConnection):
    def cursor(self,*args,**kwargs):
        kwargs.setdefault('cursor_factory',ObserverCursor)
        return super().cursor(*args,**kwargs)
def observed_connect(*args,**kwargs):
    kwargs.setdefault('connection_factory',ObserverConnection)
    return original_connect(*args,**kwargs)
psycopg2.connect = observed_connect

import pytest
class Origins:
    def check(self):
        rows = {}
        for name,module in list(sys.modules.items()):
            if name.split('.')[0] in {'web','api','core','tests'} and getattr(module,'__file__',None):
                origin = Path(module.__file__).resolve()
                assert origin.is_relative_to(ROOT),'Loaded source outside own frozen worktree'
                rows[name] = str(origin.relative_to(ROOT))
        from web.database.models import Base
        assert Base.__module__ == 'web.database.models' and len(Base.metadata.tables) == 32
        (OUT/'module-origins.json').write_text(json.dumps(rows,indent=2)+'\n')
    def pytest_collection_modifyitems(self,session,config,items):
        assert len(items)==1
        self.check()
    def pytest_runtest_call(self,item): self.check()
    def pytest_sessionfinish(self,session,exitstatus): self.check()
start = time.monotonic()
with (PRIVATE/'pytest.private.log').open('w',encoding='utf8') as stream:
    with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        code = pytest.main(['-q','--tb=short','--noconftest','--import-mode=importlib','--rootdir',str(ROOT),
           '--basetemp',str(PRIVATE/'pytest-data'),'--junitxml',str(PRIVATE/'pytest.private.xml'),
           str(ROOT/'tests/integration_mfa31_restore.py')+'::test_revision31_restore_preserves_mfa_and_all_revision26_27_28_29_30_contracts'],plugins=[Origins()])
psycopg2.connect = original_connect
assert len(owned)==2,'Expected exact two created databases'
final = independent_state(owned)
receipt('final-independent-closure',names=list(owned),state=final)
assert final == {'remaining':[],'sessions':[]}
assert len([e for e in events if e['event']=='created-immediate']) == 2
assert len([e for e in events if e['event']=='after-exact-DROP-independent-connection']) == 2
after = photo()
(OUT/'after.json').write_text(json.dumps(after,indent=2)+'\n')
assert before == after
pip = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-after.log').write_bytes(pip.stdout+pip.stderr)
assert pip.returncode == 0
inventory = {str(p.relative_to(PRIVATE)):{'bytes':p.stat().st_size,'SHA256':SHA(p.read_bytes())} for p in PRIVATE.rglob('*') if p.is_file()}
(OUT/'private-artifact-hashes.json').write_text(json.dumps(inventory,indent=2)+'\n')
summary = {'pytest_exit':int(code),'wall_seconds':time.monotonic()-start,'source_files':len(names),'packages':89,'before_after_exact':True,
 'source_head':HEAD,'owned_UUID_count':2,'closure_exact':True,'sessions_before_each_DROP':[len(e['state']['sessions']) for e in events if e['event']=='before-exact-DROP'],
 'private_artifacts':len(inventory),'scope':'One populated maintained restore31 replay. No browser, external delivery, production recovery or business RPO/RTO approval.'}
(OUT/'execution-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
raise SystemExit(code)
