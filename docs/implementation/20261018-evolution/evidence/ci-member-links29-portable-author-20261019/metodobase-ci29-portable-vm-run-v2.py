"""Execute the actual eighteen frontend workflow modules and their report guards."""
from concurrent.futures import ThreadPoolExecutor
import hashlib,importlib.metadata,json,os
from pathlib import Path
import shlex,subprocess,sys
import yaml
root=Path(r'F:\mb-r12-ci29-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-portable-vm18-after-20261019');out.mkdir(exist_ok=False)
sources=sorted(set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]+subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')[:-1]))
def photo():return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources if (root/name).is_file()},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
workflow=yaml.safe_load((root/'.github/workflows/ci.yml').read_text(encoding='utf-8-sig'))
commands=[];guards=[]
for step in workflow['jobs']['frontend-contracts']['steps']:
    for line in step.get('run','').splitlines():
        if line.startswith('node tests/e2e/'):
            driver,report=line.split(' > ');commands.append((shlex.split(driver),report))
        elif line.startswith('python scripts/check_frontend_report.py '):guards.append(shlex.split(line))
        elif line.startswith('node -e '):guards.append(shlex.split(line))
assert len(commands)==18
def execute(item):
    command,report=item
    result=subprocess.run(command,cwd=root,capture_output=True,timeout=60)
    (out/report).write_bytes(result.stdout);(out/(report+'.stderr.log')).write_bytes(result.stderr)
    value=json.loads(result.stdout)
    cases=value.get('results',value.get('report'))
    assert result.returncode==0 and cases and all(case['passed'] is True for case in cases)
    return {'command':command,'report':report,'exit_code':result.returncode,'cases':len(cases)}
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(execute,commands))
guard_rows=[]
for index,command in enumerate(guards):
    if command[0]=='python':command=[sys.executable,str(root/command[1]),str(out/command[2]),*command[3:]]
    result=subprocess.run(command,cwd=out,capture_output=True,timeout=20)
    (out/('guard-'+str(index)+'.log')).write_bytes(result.stdout+result.stderr)
    guard_rows.append({'command':command,'exit_code':result.returncode})
    assert result.returncode==0
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8');assert before==after
summary={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'modules':rows,'guards':guard_rows,'module_count':len(rows),'assertion_executions':sum(row['cases'] for row in rows),'sources_packages_stable':True,'sources':len(before['files']),'packages':len(before['packages']),'scope':'Actual eighteen VM workflow modules and actual report guards. No browser, HTTP, PostgreSQL, Actions or runtime30 claim; source has uncommitted CI2 only.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps({key:summary[key] for key in ['module_count','assertion_executions','sources_packages_stable','sources','packages']}))
assert summary['assertion_executions']==300
