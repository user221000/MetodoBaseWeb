"""Read-only package/dependency photo plus unchanged historical51 criteria."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-desktop31215-independent-20261019')
ROOT=Path(r'F:/mb-d31215-20261019')
HEAD='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def packages(label):
    inventory=sorted([d.metadata['Name'],d.version] for d in importlib.metadata.distributions())
    assert len(inventory)==83
    result=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,timeout=30)
    with (OUT/(label+'-pip.log')).open('xb') as stream:stream.write(result.stdout+result.stderr)
    assert result.returncode==0
    locks={p.name:sha(p.read_bytes()) for p in ROOT.glob('requirements*.lock')}
    value={'packages':inventory,'count':83,'pip_check_exit':result.returncode,'locks':locks}
    save(label+'-packages.json',value)
    return value

if __name__=='__main__':
    before=packages('bundle-before')
    environment=os.environ.copy();environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHON_DOTENV_DISABLED='1')
    clock=time.monotonic()
    with (OUT/'bundle51-original.log').open('xb') as stream:
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(OUT/'bundle51-adapted.py')],
                              cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
    after=packages('bundle-after')
    raw=TEMP/'desktop-artifact27-independent-source.json'
    (OUT/'bundle51-source.json').write_bytes(raw.read_bytes())
    proof=json.loads(raw.read_text(encoding='utf8'))
    save('bundle51-result.json',{'exit':result.returncode,'seconds':time.monotonic()-clock,'checks':len(proof['checks']),
         'failed_checks':proof['failed_checks'],'packages_and_locks_stable':before==after})
    print(json.dumps({'exit':result.returncode,'checks':len(proof['checks']),'failed':proof['failed_checks'],'packages_stable':before==after}))
    assert result.returncode==0 and len(proof['checks'])==51 and not proof['failed_checks'] and before==after
