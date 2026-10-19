from pathlib import Path
import hashlib
import json
import subprocess

root=Path(r'F:\mb-mfa31-terminal-sv-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
out=tmp/'metodobase-mfa31-terminal-sv-freeze-20261019';assert not out.exists()
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()=='809eab28c40c112cb6e3c9d8caceebae28683abd'
before=json.loads((tmp/'metodobase-mfa31-terminal-sv-before-20261019/summary.json').read_bytes())
after=json.loads((tmp/'metodobase-mfa31-terminal-sv-after-20261019/summary.json').read_bytes())
assert before['cases']==after['cases']==14 and before['passed']==4 and before['failed']==10 and after['passed']==14
assert before['test_source_sha256']==after['test_source_sha256']
assert before['sources_packages_python_exact'] and after['sources_packages_python_exact']
names=['web/services/mfa_service.py','web/static/js/mfa-ui.js','tests/test_mfa31_terminal_session_version.py']
assert set(git('diff','--name-only','-z').decode().split('\0')[:-1])==set(names[:2])
sha=lambda data:hashlib.sha256(data).hexdigest()
binary=Path(r'C:\Program Files\nodejs\node.exe');binary_before=sha(binary.read_bytes())
sources={name:sha((root/name).read_bytes()) for name in names}
assert sources[names[2]]==after['test_source_sha256']
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
results=[]
for name in ['mfa_state.cjs','mfa_prompt.cjs','mfa_api.cjs']:
    result=subprocess.run([str(binary),'tests/e2e/'+name],cwd=root,capture_output=True,timeout=60)
    (out/(name+'.stdout.raw.log')).write_bytes(result.stdout);(out/(name+'.stderr.raw.log')).write_bytes(result.stderr)
    results.append({'driver':name,'exit':result.returncode,'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr)})
assert all(row['exit']==0 for row in results)
assert binary_before==sha(binary.read_bytes()) and sources=={name:sha((root/name).read_bytes()) for name in names}
subprocess.run(['git','diff','--check'],cwd=root,capture_output=True,check=True)
subprocess.run(['git','-c','core.autocrlf=false','add','--',*names],cwd=root,capture_output=True,check=True)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names)
subprocess.run(['git','commit','-m','Preserve terminal session login while refusing factor version overflow'],cwd=root,capture_output=True,check=True)
head=git('rev-parse','HEAD').decode().strip();assert not git('status','--porcelain','--untracked-files=no')
receipt={'source':head,'base':'809eab28c40c112cb6e3c9d8caceebae28683abd','same_HTTP_cases':14,'before_failed':10,'before_controls':4,'after_passed':14,
 'new_unique_HTTP_cases':8,'legacy_boundary_replays':2,'existing_control_replays':4,'old_assertions_changed':0,
 'node_drivers':results,'node_binary_sha256':binary_before,'sources_before_after_node_exact':True,
 'scope':'Author scoped HTTP+SQLite and maintained VM replays. Independent security and full serial/n2 composed regression pending.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
