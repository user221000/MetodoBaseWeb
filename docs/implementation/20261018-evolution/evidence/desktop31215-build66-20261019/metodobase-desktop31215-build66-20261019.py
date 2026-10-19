from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

source=Path('F:/mb-d31215-20261019')
temp=Path('C:/Users/Consu/AppData/Local/Temp')
out=temp/'metodobase-desktop31215-build66-20261019'
out.mkdir(exist_ok=False)
python=temp/'metodobase-desktop31215-package-20261019/Scripts/python.exe'
commit='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==commit
assert not subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=source).strip()
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0')[:-1]
photo=lambda:{n:sha((source/n).read_bytes()) for n in tracked}
before=photo()
before_packages=subprocess.check_output([str(python),'-m','pip','list','--format=json','--disable-pip-version-check'])
assert len(json.loads(before_packages))==83
runtime=json.loads(subprocess.check_output([str(python),'-I','-c','import json,platform,ssl;print(json.dumps({"version":platform.python_version(),"openssl":ssl.OPENSSL_VERSION}))']))
assert runtime['version']=='3.12.15'
command=[str(python),'-X','utf8','build.py','--source-commit',commit,'--test','--zip','--prepare-installer']
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL','NUMBER_OF_PROCESSORS'}}
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',QT_QPA_PLATFORM='offscreen')
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with (out/'build.log').open('xb') as stream:
    result=subprocess.run(command,cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1500)
elapsed=round(time.monotonic()-clock,3)
after=photo()
after_packages=subprocess.check_output([str(python),'-m','pip','list','--format=json','--disable-pip-version-check'])
check=subprocess.run([str(python),'-m','pip','check'],capture_output=True)
(out/'pip-check.log').write_bytes(check.stdout+check.stderr)
(out/'source-photos-private.json').write_text(json.dumps({'before':before,'after':after},indent=2)+'\n',encoding='utf-8')
(out/'package-inventory.json').write_bytes(after_packages)
proof={'source_commit':commit,'worktree':str(source),'interpreter':str(python),'runtime':runtime,'started_utc':started,'seconds':elapsed,'command':command,'exit':result.returncode,'tracked_sources':len(before),'sources_stable':before==after,'source_aggregate_sha256':sha(json.dumps(before,sort_keys=True,separators=(',',':')).encode()),'target_packages':len(json.loads(after_packages)),'packages_stable':before_packages==after_packages,'pip_check_exit':check.returncode,'scope':'Actual clean-worktree Windows desktop build underCPython3.12.15: maintained source tests, PyInstaller onedir, offscreen diagnostic, ZIP and prepared installer as reached. No Inno compilation, payload review, installation/upgrade/uninstall, signing, real contacts or OS egress isolation claim.'}
(out/'summary.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(json.dumps(proof),flush=True)
assert result.returncode==check.returncode==0 and before==after and before_packages==after_packages
