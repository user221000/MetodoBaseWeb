from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
ROOT=Path(r"F:/mb-mfa31-current-fixtures-20261019")
OUT=Path(__file__).parent
label=sys.argv[1]
selected=sys.argv[2:]
out=OUT/label;out.mkdir(exist_ok=False)
names=subprocess.check_output(['git','ls-files','-z','--','web','api','core','config','src','tests','conftest.py'],cwd=ROOT).decode().split(chr(0))[:-1]
def photo():return {'files':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1'}
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT']:env.pop(key,None)
started=time.monotonic()
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py',*selected,'-q','--tb=short','--junitxml='+str(out/'result.xml')],cwd=ROOT,capture_output=True,env=env,timeout=600)
(out/'stdout.private.raw.log').write_bytes(result.stdout);(out/'stderr.private.raw.log').write_bytes(result.stderr)
xml=ET.fromstring((out/'result.xml').read_bytes());cases=xml.findall('.//testcase')
rows=[{'module':c.get('classname'),'case':c.get('name'),'result':next((t for t in ['failure','error','skipped'] if c.find(t)is not None),'passed')} for c in cases]
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
summary={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'exit':result.returncode,'seconds':time.monotonic()-started,'counts':{k:sum(r['result']==k for r in rows) for k in ['passed','failure','error','skipped']},'rows':rows,'sources':len(names),'packages':len(before['packages']),'quiet':before==after,'scope':'Directed SQLite-only current31 fixture diagnostic; no PostgreSQL, browser, provider, external sockets or product changes.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='rows'}));assert before==after
