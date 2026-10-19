"""Verify actual historical29 source, guard and unchanged populated restore."""
from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,time
import xml.etree.ElementTree as ET
root=Path(r'F:\mb-r12-history30-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci30-archive29-first-20261019');out.mkdir(exist_ok=False)
names=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]);names.add('tests/run_reviewed_ci29.py')
def photo():return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(names)},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
configuration=json.loads(Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
for name in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:environment.pop(name,None)
for name in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:environment[name]=configuration[name]
(out/'private-restore-evidence').mkdir();environment['METODOBASE_TEST_EVIDENCE_DIR']=str(out/'private-restore-evidence')
rows=[]
for mode in ['guard','restore']:
    command=[sys.executable,'-X','utf8','-B','tests/run_reviewed_ci29.py','--output',str(out/mode)]
    if mode=='restore':command+=['--junitxml='+str(out/'restore.xml')]
    started=time.monotonic();result=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=300)
    (out/(mode+'.stdout.private.log')).write_bytes(result.stdout);(out/(mode+'.stderr.private.log')).write_bytes(result.stderr)
    rows.append({'mode':mode,'exit':result.returncode,'seconds':time.monotonic()-started})
    if result.returncode:break
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8')
cases=ET.parse(out/'restore.xml').findall('.//testcase') if (out/'restore.xml').exists() else []
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'pip.log').write_bytes(pip.stdout+pip.stderr)
summary={'current_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'historical29_pin':'fd636202045efa30b1430f4a9dd8ab287ec76357','results':rows,'sources_packages_stable':before==after,'source_files':len(names),'packages':len(before['packages']),'restore_cases':len(cases),'restore_failures_errors_skips':sum(case.find(tag) is not None for case in cases for tag in ['failure','error','skipped']),'pip_exit':pip.returncode,'scope':'Actual exact Git historical29 guard+one unchanged populated29 restore from pinned source while host model30 remains unchanged. No fake29 metadata/current30 acceptance.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(json.dumps(summary))
assert len(rows)==2 and all(row['exit']==0 for row in rows) and before==after and pip.returncode==0 and len(cases)==1 and summary['restore_failures_errors_skips']==0
