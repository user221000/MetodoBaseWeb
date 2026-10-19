from pathlib import Path
import ast,hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
ROOT=Path(sys.argv[1]);PHASE=sys.argv[2];ARGS=sys.argv[3:]
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-retirement-peer-private-20261019')
OUT=Path(r'F:/mb-security-retirement-peer-20261019/docs/implementation/20261018-evolution/evidence/security-progress-retirement-independent-20261019')
raw=PRIVATE/PHASE;raw.mkdir();public=OUT/PHASE;public.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(name,data):(public/name).write_bytes((json.dumps(data,indent=2)+'\n').encode())
def photo():
    names=sorted(p for stem in ['web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts)
    return {'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        'sources':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in names},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
        'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes())}
before=photo();dump('before.json',before);assert len(before['packages'])==89
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(public/'pip-before.raw.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',SEC_RETIREMENT_LINEAGE_RECEIPT=str(raw/'lineage.json'))
cmd=[sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('metodobase-sec-retirement-peer-child-20261019.py')),str(ROOT),str(raw),*ARGS]
run=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=1200)
(raw/'stdout.raw.log').write_bytes(run.stdout);(raw/'stderr.raw.log').write_bytes(run.stderr)
cases=ET.parse(raw/'results.xml').findall('.//testcase') if (raw/'results.xml').exists() else []
projection=[{'case':c.get('classname')+'::'+c.get('name'),'outcome':next((kind for kind in ['failure','error','skipped'] if c.find(kind) is not None),'passed')} for c in cases]
dump('cases.STRUCTURAL.json',projection)
if (raw/'lineage.json').exists():dump('lineage.json',json.loads((raw/'lineage.json').read_bytes()))
after=photo();dump('after.json',after)
pip2=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(public/'pip-after.raw.log').write_bytes(pip2.stdout+pip2.stderr)
summary={'exit':run.returncode,'cases':len(cases),'outcomes':{k:sum(c['outcome']==k for c in projection) for k in ['passed','failure','error','skipped']},'source_count':len(before['sources']),'packages':len(before['packages']),'sources_packages_python_exact':before==after,'pip_before':pip.returncode,'pip_after':pip2.returncode}
dump('summary.json',summary)
dump('private-originals.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw.iterdir()) if p.is_file()})
print(json.dumps(summary),flush=True)
assert before==after and pip2.returncode==0
