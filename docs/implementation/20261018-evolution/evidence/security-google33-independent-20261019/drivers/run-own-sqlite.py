from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
R=Path(r'F:/mb-security-google33-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-google33-peer-private-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def photo():
    names=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','tests','scripts','requirements*','Dockerfile','db_bootstrap.py','pyproject.toml'],cwd=R).decode().split('\0');names.append('tests/test_security_google33_peer.py')
    return {'source':{n:sha((R/n).read_bytes()) for n in names if n and (R/n).is_file()},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();assert len(before['packages'])==92;save('own-sqlite-before.json',before)
args=[sys.executable,'-B','-X','utf8','tests/run_isolated.py','tests/test_security_google33_peer.py','-q','--tb=short','--basetemp='+str(P/'pytest-own-sqlite'),'--junitxml='+str(P/'own-sqlite.xml')]
run=subprocess.run(args,cwd=R,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=300)
(P/'own-sqlite-stdout.RAW.log').write_bytes(run.stdout);(P/'own-sqlite-stderr.RAW.log').write_bytes(run.stderr)
cases=ET.parse(P/'own-sqlite.xml').findall('.//testcase');rows=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases];save('own-sqlite-cases.STRUCTURAL.json',rows)
after=photo();save('own-sqlite-after.json',after);summary={'exit':run.returncode,'cases':len(rows),'outcomes':{k:sum(r['outcome']==k for r in rows) for k in ['passed','failure','error','skipped']},'source_packages_Python_quiet':before==after};save('own-sqlite-summary.json',summary);print(json.dumps(summary));assert before==after
