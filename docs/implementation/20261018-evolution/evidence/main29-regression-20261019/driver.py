"""Run both required broad regression modes against the merged schema29 source."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,time
import xml.etree.ElementTree as ET
root=Path(r'F:\MetodoBaseWeb-execution-20261018');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-main29-regression-first-20261019');out.mkdir(exist_ok=False)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='e250d56a5be5c950167b682d49991d29a8dbaa62'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
def photo():return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'before-pip.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
base=[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests','--ignore=tests/test_login_desktop.py','--ignore=tests/test_desktop_entrypoints.py','-q','--tb=short']
commands={'serial':base+['--cov','--cov-report=xml:'+str(out/'coverage.xml'),'--cov-report=json:'+str(out/'coverage.json'),'--junitxml='+str(out/'serial.xml')],
          'shuffle':base+['--shuffle-seed=20261018','-n','2','--junitxml='+str(out/'shuffle.xml')]}
def run(item):
    name,command=item;environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',COVERAGE_FILE=str(out/('.coverage-'+name)))
    for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL','_METODOBASE_TEST_ROOT']:environment.pop(key,None)
    started=time.monotonic()
    result=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=900)
    (out/(name+'.stdout.private.log')).write_bytes(result.stdout);(out/(name+'.stderr.private.log')).write_bytes(result.stderr)
    cases=ET.parse(out/(name+'.xml')).findall('.//testcase') if (out/(name+'.xml')).exists() else []
    summary={'mode':name,'command':command,'exit':result.returncode,'seconds':time.monotonic()-started,'cases':len(cases),'failures':[],'skips':[]}
    for case in cases:
        for tag in ['failure','error','skipped']:
            node=case.find(tag)
            if node is not None:
                entry={'module':case.get('classname'),'case':case.get('name'),'kind':tag,'message':node.get('message','')}
                summary['skips' if tag=='skipped' else 'failures'].append(entry)
    (out/(name+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'mode':name,'exit':result.returncode,'cases':len(cases),'failures':len(summary['failures']),'skips':len(summary['skips']),'seconds':summary['seconds']}),flush=True)
    return summary
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,commands.items()))
coverage=subprocess.run([sys.executable,'-X','utf8','-B','tests/check_coverage.py',str(out/'coverage.json')],cwd=root,capture_output=True,timeout=30)
(out/'coverage-check.stdout.log').write_bytes(coverage.stdout);(out/'coverage-check.stderr.log').write_bytes(coverage.stderr)
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8')
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'after-pip.log').write_bytes(pip.stdout+pip.stderr)
summary={'head':head,'results':results,'coverage_exit':coverage.returncode,'sources_packages_stable':before==after,'sources':len(names),'packages':len(before['packages']),'pip_exit':pip.returncode,'scope':'Both required broad SaaS modes on merged schema29 with isolated synthetic roots; local Windows known platform skip evaluated separately. No PG/Redis/Linux/Actions/image claim.'}
(out/'summary.private.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(json.dumps({key:summary[key] for key in ['head','coverage_exit','sources_packages_stable','sources','packages','pip_exit']}),flush=True)
assert before==after and pip.returncode==0
