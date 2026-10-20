from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
ROOT=Path(r'F:/mb-security-gitleaks-triage-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019/tests-final'
OUT.mkdir()
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-gitleaks-peer-private-20261019')
sha=lambda b:hashlib.sha256(b).hexdigest()
def snapshot():
    sources={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for stem in ['web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts}
    return {'sources':sources,'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=snapshot();assert len(before['packages'])==89
(OUT/'tests-before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
a=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert a.returncode==0
(OUT/'pip-before.raw.log').write_bytes(a.stdout+a.stderr)
cmd=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests/test_secret_scan_safety.py','tests/test_secret_scan_fragment_pins.py','tests/test_security_gitleaks_peer.py','-q','--tb=short','--basetemp='+str(PRIVATE/'pytest-final'),'--junitxml='+str(PRIVATE/'tests-final.xml')]
run=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=240)
(PRIVATE/'tests-final-stdout.raw.log').write_bytes(run.stdout);(PRIVATE/'tests-final-stderr.raw.log').write_bytes(run.stderr)
cases=ET.parse(PRIVATE/'tests-final.xml').findall('.//testcase')
projection=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((x for x in ['failure','error','skipped'] if c.find(x)is not None),'passed')} for c in cases]
(OUT/'tests.STRUCTURAL.json').write_text(json.dumps(projection,indent=2)+'\n',encoding='utf8')
after=snapshot();(OUT/'tests-after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8')
b=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);assert b.returncode==0
(OUT/'pip-after.raw.log').write_bytes(b.stdout+b.stderr)
summary={'exit':run.returncode,'cases':len(cases),'outcomes':{kind:sum(row['outcome']==kind for row in projection) for kind in ['passed','failure','error','skipped']},'sources_packages_python_exact':before==after,'source_count':len(before['sources']),'packages':len(before['packages']),'pip_before':a.returncode,'pip_after':b.returncode}
(OUT/'tests-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(json.dumps(summary))
assert before==after
