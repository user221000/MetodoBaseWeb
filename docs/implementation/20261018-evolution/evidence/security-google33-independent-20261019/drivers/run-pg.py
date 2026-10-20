from pathlib import Path
from urllib.parse import urlsplit
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-peer-20261019');sys.path.insert(0,str(R));sys.dont_write_bytecode=True
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-google33-peer-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
PROFILE=T/'metodobase-qa-pg55483-private-ok6hrpyq/env.json';sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
phase=sys.argv[1] if len(sys.argv)>1 else 'pg-functional'
assert phase in {'pg-functional','pg-migration-restore'}
profile_raw=PROFILE.read_bytes();profile=json.loads(profile_raw);assert set(profile)=={'METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN'}
from tests.isolation import validate_postgres_test_url
for name in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
    parsed=urlsplit(validate_postgres_test_url(profile[name]));assert parsed.hostname in {'127.0.0.1','localhost'} and parsed.port==55483
import psycopg2
with psycopg2.connect(profile['METODOBASE_TEST_POSTGRES_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as db,db.cursor() as cursor:
    cursor.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,inet_server_port() FROM pg_roles WHERE rolname=current_user')
    observed=cursor.fetchone();assert observed==(False,False,False,False,55483)
save(phase+'-profile-binding.json',{'profile_sha256':sha(profile_raw),'loopback_port':55483,'app_four_flags_false':True,'private_profile_values_published':False,'global_roles_HBA_services_altered':False})
leases=P/'metodobase-google33-author-helper-independent-peer-20261019/leases';leases.mkdir(parents=True,exist_ok=True)
evidence=P/'restore-evidence';evidence.mkdir(exist_ok=True)
receipts=P/(phase+'-association-receipts');receipts.mkdir()
def photo():
    names=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','tests','scripts','requirements*','Dockerfile','db_bootstrap.py','pyproject.toml'],cwd=R).decode().split('\0')
    names+=['tests/test_security_google33_peer.py','tests/test_security_google33_postgres_peer.py']
    return {'source':{n:sha((R/n).read_bytes()) for n in names if n and (R/n).is_file()},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();assert len(before['packages'])==92;save(phase+'-before.json',before)
files=['tests/test_security_google33_postgres_peer.py','tests/integration_google33_guards.py'] if phase=='pg-functional' else ['tests/integration_google33_migrations.py','tests/integration_google33_onboarding.py','tests/integration_google33_restore.py']
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*files,'-q','--tb=short','--basetemp='+str(P/('pytest-'+phase)),'--junitxml='+str(P/(phase+'.xml'))]
environment=dict(os.environ,**profile,GOOGLE33_PRIVATE_LEASES=str(leases),SEC_GOOGLE_PRIVATE_RECEIPTS=str(receipts),METODOBASE_TEST_EVIDENCE_DIR=str(evidence),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
run=subprocess.run(cmd,cwd=R,env=environment,capture_output=True,timeout=480)
(P/(phase+'-stdout.RAW.log')).write_bytes(run.stdout);(P/(phase+'-stderr.RAW.log')).write_bytes(run.stderr)
cases=ET.parse(P/(phase+'.xml')).findall('.//testcase');rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases];save(phase+'-cases.STRUCTURAL.json',rows)
after=photo();save(phase+'-after.json',after)
states=[json.loads(p.read_bytes()) for p in leases.glob('lease-*.json')]
closed=all(s['state']=='closed_absent' and s['sessions_before_drop']==0 and s['absence_verified']=='fresh_control_connection' for s in states)
save(phase+'-closures.STRUCTURAL.json',{'scope':'Only independently owned UUID receipts in this private helper-coordinate subtree; no foreign databases or FORCE termination. Exact initial open xb precedes CREATE.','all_closed_absent':closed,'leases':[{'plan_id':s['plan_id'],'database':s['database'],'oid':s.get('oid'),'state':s['state'],'sessions_before_drop':s.get('sessions_before_drop'),'absence_verified':s.get('absence_verified'),'initial_creation':s['initial_creation'],'launcher_pid':s['launcher_pid'],'launcher_birth':s['launcher_birth'],'launcher_birth_after_create':s.get('launcher_birth_after_create'),'created_at':s.get('created_at'),'closed_at':s.get('closed_at')} for s in states]})
summary={'exit':run.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows) for k in ['passed','failure','error','skipped']},'source_packages_Python_quiet':before==after,'private_profile_bytes_unchanged':sha(PROFILE.read_bytes())==sha(profile_raw),'recorded_own_UUIDs_cumulative':len(states),'all_closed_absent':closed};save(phase+'-summary.json',summary);print(json.dumps(summary))
assert before==after and sha(PROFILE.read_bytes())==sha(profile_raw) and closed
