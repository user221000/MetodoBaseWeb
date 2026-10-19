"""Execute the actual maintained23 Node gates and their real CLI parsers."""
from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,time
import yaml
root=Path(r'F:\mb-r23-history30-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r23-ci-node-first-20261019');out.mkdir(exist_ok=False)
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')[:-1]
def photo():return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(set(names))},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
workflow=yaml.safe_load((root/'.github/workflows/ci.yml').read_bytes());blocks=[step['run'] for step in workflow['jobs']['frontend-contracts']['steps'] if 'node tests/e2e/' in step.get('run','')]
assert len(blocks)==3
prefix=r'''set -euo pipefail
node() {
 local script="$1"; shift
 local args=()
 for arg in "$@"; do
  if [[ "$arg" == web/* ]]; then args+=("$CI_ROOT/$arg"); else args+=("$arg"); fi
 done
 "$CI_NODE" "$CI_ROOT/$script" "${args[@]}"
}
python() { local script="$1"; shift; "$CI_PYTHON" "$CI_ROOT/$script" "$@"; }
'''
environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',CI_ROOT=root.as_posix(),CI_NODE='C:/Program Files/nodejs/node.exe',CI_PYTHON=Path(sys.executable).as_posix())
rows=[]
for number,block in enumerate(blocks):
    script=out/('block'+str(number)+'.sh');script.write_bytes((prefix+block).encode())
    started=time.monotonic();result=subprocess.run(['C:/Program Files/Git/bin/bash.exe',script.as_posix()],cwd=out,env=environment,capture_output=True,timeout=120,check=False)
    (out/('block'+str(number)+'.stdout.log')).write_bytes(result.stdout);(out/('block'+str(number)+'.stderr.log')).write_bytes(result.stderr)
    rows.append({'block':number,'exit':result.returncode,'Node_invocations':sum(line.startswith('node tests/e2e/') for line in block.splitlines()),'seconds':time.monotonic()-started})
    print(json.dumps(rows[-1]),flush=True)
    if result.returncode:break
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8')
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,check=False);(out/'pip.log').write_bytes(pip.stdout+pip.stderr)
summary={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'uncommitted_CI_sources_identified_by_hash':True,'results':rows,'sources_packages_stable':before==after,'source_files':len(set(names)),'packages':len(before['packages']),'pip_exit':pip.returncode,'scope':'Actual23 local Node VM/controlled-DOM commands from workflow and exact real parser/normalizer invocations. No Chrome/layout/HTTP/PG/Actions.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(json.dumps(summary))
assert len(rows)==3 and all(row['exit']==0 for row in rows) and sum(row['Node_invocations'] for row in rows)==23 and before==after and pip.returncode==0
