"""Extract and compare payload with authenticated retained tool; never execute Setup."""
import time
from run_bundle51 import *

prior=json.loads((OUT/'bundle51-result.json').read_text(encoding='utf8'))
assert prior['exit']==0 and prior['checks']==51 and not prior['failed_checks']
before=packages('installer-before')
environment=os.environ.copy();environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHON_DOTENV_DISABLED='1')
clock=time.monotonic()
with (OUT/'installer27-original.log').open('xb') as stream:
    result=subprocess.run([sys.executable,'-X','utf8','-B',str(OUT/'installer27-adapted.py')],
                          cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
after=packages('installer-after')
raw=TEMP/'desktop-artifact27-independent-installer-source.json'
(OUT/'installer27-source.json').write_bytes(raw.read_bytes())
proof=json.loads(raw.read_text(encoding='utf8'))
for label in ['list','integrity-test','extract']:
    original=TEMP/('desktop-artifact27-independent-installer-'+label+'.log')
    if original.exists():(OUT/('installer27-'+label+'.log')).write_bytes(original.read_bytes())
save('installer27-result.json',{'exit':result.returncode,'seconds':time.monotonic()-clock,'checks':len(proof['checks']),
     'failed_checks':proof['failed_checks'],'packages_and_locks_stable':before==after})
print(json.dumps({'exit':result.returncode,'checks':len(proof['checks']),'failed':proof['failed_checks'],'packages_stable':before==after}))
assert result.returncode==0 and len(proof['checks'])==27 and not proof['failed_checks'] and before==after
