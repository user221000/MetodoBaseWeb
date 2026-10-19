"""Verify final CI29 helper/browser wiring composition without new services."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,importlib.metadata,json,shutil,subprocess,sys
root=Path(r'F:\mb-r12-ci29-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-final-composition-20261019');out.mkdir(exist_ok=False)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='4e875f99d5af4bb2a1ec4468de08e0fde948dfb7'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
def photo():return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'Git_executable_sha256':hashlib.sha256(Path(shutil.which('git')).read_bytes()).hexdigest(),'Bash_executable_sha256':hashlib.sha256(Path(r'C:\Program Files\Git\bin\bash.exe').read_bytes()).hexdigest()}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
commands={'full-guard':[sys.executable,'-X','utf8','-B','tests/verify_member_links_ci.py','--output',str(out/'guard')],
          'unit':[sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests/test_member_browser_gate.py','tests/test_member_ci_trust.py','tests/test_reviewed_ci28_archive.py','-q','--tb=short','--junitxml='+str(out/'unit.xml')]}
def run(item):
    name,command=item;result=subprocess.run(command,cwd=root,capture_output=True,timeout=240)
    (out/(name+'.stdout.log')).write_bytes(result.stdout);(out/(name+'.stderr.log')).write_bytes(result.stderr)
    return {'name':name,'command':command,'exit':result.returncode}
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,commands.items()))
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8')
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'pip.log').write_bytes(pip.stdout+pip.stderr)
summary={'head':head,'results':results,'files':len(names),'packages':len(before['packages']),'sources_packages_Git_Bash_stable':before==after,'pip_exit':pip.returncode,'scope':'Actual final CI29 verification, real parsers/owned inert Bash/Git archives and unit gates. No new Chrome/PG/Linux/Actions or index30 execution.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(json.dumps(summary))
assert before==after and pip.returncode==0 and all(item['exit']==0 for item in results)
