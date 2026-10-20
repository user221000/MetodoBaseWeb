from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-followup34-author-sec-peer-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-pg-independent-20261019';O.mkdir();(O/'.gitattributes').write_bytes(b'* -text\n')
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
base='f848256ceac6a8c6a7c2cc8e3a8159d8b61e0759';assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==base
raw=(T/'metodobase-sec-followup34-peer-postgres-prepared-20261019.py').read_bytes();sealed=subprocess.check_output(['git','show','e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee:docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019/prepared/test_security_followup34_postgres_peer.prepared.py'],cwd=R);assert raw==sealed
own='tests/test_security_followup34_postgres_peer.py';target=R/own;assert not target.exists();target.write_bytes(raw)
save('original-prepared-binding.json',{'RED_commit':'e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee','prepared_canary_SHA256':sha(raw),'copied_byte_exact_without_assertion_edits':True,'private_parent_prefix':'metodobase-followup34-author-sec-peer-20261019 is required by existing immutable lease helper; this execution is independent peer, not author.'})
def photo():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')+[own,'tests/test_security_followup34_sql_errors_peer.py']
 return {'source':{n:sha((R/n).read_bytes())for n in names if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':sha((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();save('original-PG-before.json',before)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(O/'pip-before.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
profile=json.loads((T/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes());assert set(profile)=={'METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN'}
from urllib.parse import urlsplit
for k in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
 u=urlsplit(profile[k]);assert u.hostname in {'127.0.0.1','localhost'}and u.port==55483
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',own,'-q','--tb=short','--basetemp='+str(P/'pytest-original-PG'),'--junitxml='+str(P/'original-PG.xml')]
env=dict(os.environ,**profile,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',FOLLOWUP34_PRIVATE_LEASES=str(P/'leases'))
result=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=420);(P/'original-PG-stdout.RAW.log').write_bytes(result.stdout);(P/'original-PG-stderr.RAW.log').write_bytes(result.stderr)
rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(P/'original-PG.xml').findall('.//testcase')];save('original-PG-cases.STRUCTURAL.json',rows);after=photo();save('original-PG-after.json',after);assert before==after
leases=[json.loads(p.read_bytes())for p in (P/'leases').glob('*.json')];summary={'exit':result.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows)for k in ['passed','failure','error','skipped']},'source_92_metadata_bothPython_quiet':True,'lease_count':len(leases),'all_own_leases_closed_absent':all(l['state']=='closed_absent'and l['sessions_before_drop']==0 for l in leases)};save('original-PG-summary.json',summary);print(json.dumps(summary))
