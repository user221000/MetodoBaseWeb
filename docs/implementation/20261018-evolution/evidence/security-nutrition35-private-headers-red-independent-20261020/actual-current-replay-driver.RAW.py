from pathlib import Path
import hashlib, importlib.metadata, json, os, shutil, subprocess, sys, xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-conflict-peer-20261019')
P=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-nutrition35-api-peer-private-20261019')
SHA=lambda b:hashlib.sha256(b).hexdigest()
phase=sys.argv[1];assert phase.replace('-','').isalnum()
D=P/phase;D.mkdir(exist_ok=False)
save=lambda n,v:(D/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()=='cdf103a28fe33e32cfeaac825d338d1901a5295e'
def photo():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')
 names+=list(str(p.relative_to(R)).replace('\\','/')for p in (R/'tests').glob('test_security_nutrition35_*peer.py'))+['tests/test_nutrition35_write_error_boundary.py','tests/e2e/security_nutrition35_peer.cjs']
 return {'source':{n:SHA((R/n).read_bytes())for n in sorted(set(names))if n and not n.startswith('docs/')and(R/n).is_file()},'packages':{d.metadata['Name']:{'version':d.version,'METADATA_SHA256':SHA((d.read_text('METADATA')or'').encode())}for d in importlib.metadata.distributions()},'python':SHA(Path(sys.executable).read_bytes()),'base_python':SHA(Path(sys._base_executable).read_bytes()),'node':SHA(Path(shutil.which('node')).read_bytes())}
before=photo();save('before.json',before)
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(D/'pip-before.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*sys.argv[2:],'-q','--tb=short','--basetemp='+str(D/'pytest'),'--junitxml='+str(D/'result.xml')]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
for k in list(env):
 if k.startswith('METODOBASE_TEST_')or k in {'FOLLOWUP34_PRIVATE_LEASES','SEC_FOLLOWUP34_RECEIPTS'}:env.pop(k,None)
save('argv.json',cmd)
r=subprocess.run(cmd,cwd=R,env=env,capture_output=True,timeout=720)
(D/'stdout.RAW.log').write_bytes(r.stdout);(D/'stderr.RAW.log').write_bytes(r.stderr)
cases=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped']if c.find(k)is not None),'passed')}for c in ET.parse(D/'result.xml').findall('.//testcase')]
save('cases.STRUCTURAL.json',cases)
after=photo();save('after.json',after);assert before==after
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(D/'pip-after.RAW.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
summary={'phase':phase,'exit':r.returncode,'cases':len(cases),'outcomes':{k:sum(c['outcome']==k for c in cases)for k in ['passed','failure','error','skipped']},'source_packages92_python_node_quiet':True,'PG_SQL_or_private_profile':False}
save('summary.json',summary);print(json.dumps(summary))
