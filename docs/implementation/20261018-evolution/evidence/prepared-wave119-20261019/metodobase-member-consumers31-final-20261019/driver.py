"""Freeze and execute the new fixture, preserving the exact old consumer callbacks."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import time

root = Path(r'F:\mb-mfa31-compose-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-member-consumers31-final-20261019')
base = '2010a6c56187fe0cf3389da7ffc4cdd09e00f968'
name = 'tests/e2e/member_link_consumers31.cjs'
git = lambda *args: subprocess.check_output(['git', *args], cwd=root)
assert git('rev-parse','HEAD').decode().strip() == base and not git('status','--porcelain','--untracked-files=no')
source = (root/name).read_bytes()
assert hashlib.sha256(source).hexdigest() == '4b8db35bfac09bef72b32940dab81245a316385d7a78a05a1c725b67b4167be6'
marker='const tests=[];const test=(n,f)=>tests.push([n,f]);'
old=(root/'tests/e2e/member_link_consumers.cjs').read_text(encoding='utf8')
new=source.decode()
assert new[new.index(marker):] == old[old.index(marker):]
subprocess.run(['git','add','--',name],cwd=root,check=True,capture_output=True)
assert git('diff','--cached','--name-only','-z').decode().split('\0')[:-1] == [name]
subprocess.run(['git','diff','--cached','--check','--',name],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Keep member consumer contracts on the actual daily plan companion modules'],cwd=root,check=True,capture_output=True)
head=git('rev-parse','HEAD').decode().strip()
assert not git('status','--porcelain','--untracked-files=no')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'tested-fixture.raw.cjs').write_bytes(source)
names=git('ls-files','-z','--','web','api','core','config','src','tests').decode().split('\0')[:-1]
node=Path(r'C:\Program Files\nodejs\node.exe')


def photo():
    return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names},
            'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
            'node_sha256':hashlib.sha256(node.read_bytes()).hexdigest()}


before=photo()
(out/'before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
started=time.monotonic()
result=subprocess.run([str(node),name],cwd=root,capture_output=True,timeout=30,check=False)
(out/'stdout.raw.json').write_bytes(result.stdout)
(out/'stderr.raw.log').write_bytes(result.stderr)
data=json.loads(result.stdout)
after=photo()
(out/'after.json').write_bytes((json.dumps(after,indent=2)+'\n').encode())
summary={'head':head,'exit':result.returncode,'seconds':time.monotonic()-started,'passed':data['passed'],'total':data['total'],
         'sources':len(names),'packages':len(before['packages']),'source_packages_node_quiet':before==after,
         'test_callbacks_and_runner_suffix_exact_v1':True,'original_helper_changed':False,'product_changed':False,
         'scope':'Root authored fixture adoption,16existing criteria replayed with real R24 companion modules and include-aware DOM. Fixed API doubles, no HTTP/browser/PG/independent acceptance. Original historical13of16 failures and passive-stub causality remain separate and unchanged.'}
(out/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps(summary))
assert before==after and result.returncode==0 and data['total']==data['passed']==16
