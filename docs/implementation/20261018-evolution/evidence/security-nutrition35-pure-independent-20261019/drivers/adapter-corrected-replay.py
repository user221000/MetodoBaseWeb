from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-nutrition35-pure-peer-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-nutrition35-pure-independent-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
BASE='d5ef9602687730037b3e448506e14d14a3df5323';assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==BASE
own='tests/test_security_nutrition35_boundary_peer.py'
def photo():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')+[own,'tests/test_security_followup34_sql_errors_peer.py']
 return {'source':{n:sha((R/n).read_bytes())for n in names if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();save('adapter-after-before.json',before)
r=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/'adapter-after-pip-before.RAW.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
files=[own]
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*files,'-q','--tb=short','--basetemp='+str(P/'pytest-adapter-after'),'--junitxml='+str(P/'adapter-after.xml')]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
for k in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_REDIS_URL','FOLLOWUP34_PRIVATE_LEASES','SEC_FOLLOWUP34_RECEIPTS']:env.pop(k,None)
r=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=360);(P/'adapter-after-stdout.RAW.log').write_bytes(r.stdout);(P/'adapter-after-stderr.RAW.log').write_bytes(r.stderr)
cases=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(P/'adapter-after.xml').findall('.//testcase')]
save('adapter-after-cases.STRUCTURAL.json',cases);after=photo();save('adapter-after-after.json',after);assert before==after
summary={'exit':r.returncode,'cases':len(cases),'author_cases':sum('test_security_nutrition35_boundary_peer'not in c['case']for c in cases),'own_cases':sum('test_security_nutrition35_boundary_peer'in c['case']for c in cases),'outcomes':{k:sum(c['outcome']==k for c in cases)for k in ['passed','failure','error','skipped']},'source_92_metadata_bothPython_quiet':True,'PG_profile_read_or_SQL':False}
save('adapter-after-summary.json',summary)
r=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/'adapter-after-pip-after.RAW.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
print(json.dumps(summary))
