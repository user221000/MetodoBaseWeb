"""Single maintained populated PG restore with additive controls, or one own SQLite focal."""
from support import *
import time,xml.etree.ElementTree as ET
mode=sys.argv[1];assert mode in {'historical29-SQLite','restore30-PG'}
phase=TEMP/mode;phase.mkdir(exist_ok=False);evidence=phase/'evidence';evidence.mkdir()
before=photo(mode+'-before')
env=os.environ.copy()
for name in list(env):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_','METODOBASE_TEST_','_METODOBASE_TEST')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):env.pop(name,None)
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(OUT))
command=[str(PYTHON),'-X','utf8','-B','tests/run_isolated.py']
if mode=='restore30-PG':
    configuration=json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
    for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:env[key]=configuration[key]
    env['METODOBASE_TEST_EVIDENCE_DIR']=str(evidence)
    command+=['-p','qa_restore30_plugin','tests/integration_personal_history_index_restore.py::test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts']
else:command+=[str(OUT/'test_historical29_target_review.py')]
command+=['-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
started=time.monotonic()
with (phase/'stdout.private.log').open('xb') as stdout,(phase/'stderr.private.log').open('xb') as stderr:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=230)
after=photo(mode+'-after');assert before==after
cases=ET.parse(phase/'junit.xml').findall('.//testcase')
assert len(cases)==1
status={'exit':result.returncode,'cases':1,'passed':sum(not any(case.find(k) is not None for k in ['failure','error','skipped']) for case in cases),'failure_nodeids':[case.attrib.get('name') for case in cases if case.find('failure') is not None or case.find('error') is not None]}
if mode=='restore30-PG':
    created=json.loads((evidence/'history-index30-author-owned-created.json').read_bytes());closed=json.loads((evidence/'history-index30-author-owned-closed.json').read_bytes());assert created['names']==closed['names'] and closed['remaining']==[]
    import psycopg2
    with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as db,db.cursor() as cursor:
        cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(created['names'],));remaining=[row[0] for row in cursor.fetchall()]
    assert remaining==[];save('independent-two-UUID-absence.json',{'exact_owned_names':created['names'],'remaining':remaining,'count':2,'actual_query_after_fixture_finalizer':True})
    own=json.loads((evidence/'qa-restored-negative-controls.json').read_bytes());status.update(own_restored_controls=own['total'],own_restored_controls_passed=own['passed'],owned_UUIDs_closed=2)
outputs=[publish(path,mode+'-'+path.relative_to(phase).as_posix().replace('/','-')) for path in sorted(phase.rglob('*')) if path.is_file()]
save(mode+'-result.json',{'head':HEAD,'results':status,'seconds':time.monotonic()-started,'command':command,'sources_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'outputs':outputs,'scope':'One actual maintained populated restore on two own PG UUIDs plus additive controls, or one own historical SQLite focal. No Chrome/CI30/performance claim.'})
print(json.dumps({'mode':mode,**status,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True}))
assert result.returncode==0 and status['passed']==1
