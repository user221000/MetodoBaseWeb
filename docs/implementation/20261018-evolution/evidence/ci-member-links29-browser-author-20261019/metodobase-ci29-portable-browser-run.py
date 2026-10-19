"""Exercise the frozen public/private orchestrator against actual owned Chrome/PG."""
import hashlib,importlib.metadata,json,os
from pathlib import Path
import subprocess,sys,tempfile,time
root=Path(r'F:\mb-r12-ci29-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-portable-browser-first-20261019');out.mkdir(exist_ok=False)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='6c9347d226f57b967f4bb881ab005920f6c9b238'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
modules=Path(r'F:\MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
configuration_path=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq/env.json')
configuration=json.loads(configuration_path.read_text(encoding='utf-8-sig'))
sha=lambda value:hashlib.sha256(value).hexdigest()
def photo():return {'sources':{name:sha((root/name).read_bytes()) for name in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'node_dependency_files':{path.relative_to(modules).as_posix():sha(path.read_bytes()) for path in sorted(modules.rglob('*')) if path.is_file()},'Node':sha(Path(r'C:\Program Files\nodejs\node.exe').read_bytes()),'Chrome':sha(Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe').read_bytes()),'private_config_sha256':sha(configuration_path.read_bytes())}
def write(name,value):(out/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
def process_photo(name):
    command="Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('chrome.exe','chrome_crashpad_handler.exe') -or $_.ProcessId -in @(8776) } | Select-Object ProcessId,ParentProcessId,CreationDate,ExecutablePath | ConvertTo-Json -Depth 3"
    result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,timeout=20)
    assert result.returncode==0;(out/name).write_bytes(result.stdout)
    return json.loads(result.stdout.decode('utf-8-sig'))
before=photo();write('before.json',before);old_processes=process_photo('foreign-chrome-before.json')
old_phases=set(Path(tempfile.gettempdir()).glob('metodobase-member-browser-*'))
environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',QA_NODE_MODULES=str(modules),QA_CHROME=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:environment.pop(key,None)
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:environment[key]=configuration[key]
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'before-pip.log').write_bytes(pip.stdout+pip.stderr);assert pip.returncode==0
started=time.monotonic()
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/e2e/run_member_link_browser.py','--output',str(out/'public'),'--port','8794'],cwd=root,env=environment,capture_output=True,timeout=420)
(out/'orchestrator.stdout.log').write_bytes(result.stdout);(out/'orchestrator.stderr.log').write_bytes(result.stderr)
after=photo();write('after.json',after);new_processes=process_photo('foreign-chrome-after.json')
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'after-pip.log').write_bytes(pip.stdout+pip.stderr)
new_phases=set(Path(tempfile.gettempdir()).glob('metodobase-member-browser-*'))-old_phases
write('private-phase-locations.private.json',[str(path) for path in sorted(new_phases)])
receipt=json.loads((out/'public/receipt.json').read_bytes()) if (out/'public/receipt.json').exists() else None
old_by_id={row['ProcessId']:row for row in old_processes};new_by_id={row['ProcessId']:row for row in new_processes}
preserved=all(new_by_id.get(key)==value for key,value in old_by_id.items())
summary={'head':head,'exit_code':result.returncode,'seconds':time.monotonic()-started,'sources_packages_tools_config_stable':before==after,'source_files':len(names),'packages':len(before['packages']),'node_dependency_files':len(before['node_dependency_files']),'pip_after_zero':pip.returncode==0,'foreign_chrome_preserved':preserved,'new_Chrome_process_IDs':sorted(set(new_by_id)-set(old_by_id)),'owned_private_phase_count':len(new_phases),'public_receipt':receipt,'scope':'Actual Windows Chrome/HTTP/restricted migratedPG29 through frozen CI2 orchestrator; no Linux/Actions/candidate-image or worker/provider generation claim.'}
write('summary.json',summary);print(json.dumps(summary))
assert result.returncode==0 and before==after and pip.returncode==0 and preserved and len(new_phases)==1
assert summary['new_Chrome_process_IDs']==[] and receipt['completed'] is True
