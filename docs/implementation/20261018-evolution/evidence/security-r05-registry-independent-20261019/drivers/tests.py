from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
ROOT=Path(r'F:/mb-security-r05-classifier-peer-20261019');TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp');PRIVATE=TEMP/'metodobase-sec-r05-classifier-peer-private-20261019'
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-r05-registry-independent-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest()
save=lambda n,v:(OUT/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
def photo():
    return {'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'sources':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for stem in ['scripts','web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes()),'data_zip':sha((ROOT/'scripts/data/reviewed_scan_locations_v1.zip').read_bytes())}
before=photo();assert len(before['packages'])==89;save('tests17-before.json',before)
a=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert a.returncode==0
(OUT/'pip17-before.raw.log').write_bytes(a.stdout+a.stderr)
names=['tests/test_secret_scan_safety.py','tests/test_secret_scan_fragment_pins.py','tests/test_security_gitleaks_peer.py','tests/test_secret_scan_reviewed_locations.py','tests/test_security_r05_registry_peer.py']
cmd=[sys.executable,'-B','-X','utf8','tests/run_isolated.py',*names,'-q','--tb=short','--basetemp='+str(PRIVATE/'pytest-17'),'--junitxml='+str(PRIVATE/'tests17.xml')]
run=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=240)
(PRIVATE/'tests17-stdout.raw.log').write_bytes(run.stdout);(PRIVATE/'tests17-stderr.raw.log').write_bytes(run.stderr)
cases=ET.parse(PRIVATE/'tests17.xml').findall('.//testcase');projection=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((n for n in ['failure','error','skipped'] if c.find(n)is not None),'passed')} for c in cases]
save('tests17.STRUCTURAL.json',projection)
after=photo();save('tests17-after.json',after);assert before==after
b=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert b.returncode==0
(OUT/'pip17-after.raw.log').write_bytes(b.stdout+b.stderr)
summary={'exit':run.returncode,'cases':len(cases),'passed':sum(c['outcome']=='passed' for c in projection),'failure':sum(c['outcome']=='failure' for c in projection),'error':sum(c['outcome']=='error' for c in projection),'skipped':sum(c['outcome']=='skipped' for c in projection),'Python_packages_sources_exact':before==after,'packages':89,'pip_before':a.returncode,'pip_after':b.returncode}
save('tests17-summary.json',summary);print(json.dumps(summary))
assert run.returncode==0
