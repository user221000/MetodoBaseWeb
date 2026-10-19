"""Read-only quality gates on the frozen R24 source; no provider or service."""
from pathlib import Path
import concurrent.futures,hashlib,importlib.metadata,json,os,subprocess,sys,time
ROOT=Path(r'F:\mb-r24-plan-20261019');OUT=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r24-root-quality-20261019');OUT.mkdir(exist_ok=False)
QUALITY=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-20261018\Scripts\python.exe')
HEAD='adc80c7edb6314a7851b9447bccb092a62c142d5';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=ROOT,**k)
assert git('rev-parse','HEAD',text=True).strip()==HEAD and not git('status','--porcelain')
manifest=ROOT/'docs/implementation/20261018-evolution/evidence/r24/final-source.json'
assert sha(manifest.read_bytes())=='749261abb9a10ad8ae818bee4fbbd39ce93bb6bf76ced549393049ed90a4cbda'
for name,details in json.loads(manifest.read_bytes())['sources'].items():
    blob=(ROOT/name).read_bytes();assert sha(blob)==details['raw_sha256'] and sha(blob.replace(b'\r\n',b'\n'))==details['git_lf_sha256']
names=git('ls-files','-z').decode().split('\0')[:-1]
def photo():return {'files':{n:sha((ROOT/n).read_bytes()) for n in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
def write(name,data):(OUT/name).write_bytes((json.dumps(data,indent=2)+'\n').encode())
before=photo();write('before.json',before)
def run(mode):
    start=time.monotonic();result=subprocess.run([str(QUALITY),'-X','utf8','-B','tests/check_quality.py',mode],cwd=ROOT,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'},timeout=120,check=False)
    (OUT/(mode+'.stdout.log')).write_bytes(result.stdout);(OUT/(mode+'.stderr.log')).write_bytes(result.stderr)
    return {'mode':mode,'exit':result.returncode,'seconds':time.monotonic()-start}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,['lint','syntax','security']))
after=photo();write('after.json',after)
report={'head':HEAD,'source_files':len(names),'packages':len(before['packages']),'quiet':before==after,'results':rows,'scope':'Root read-only quality on author frozen R24; no HTTP/PG/Chrome/Actions or clinical/privacy acceptance.'};write('summary.json',report);print(json.dumps(report))
assert before==after and all(row['exit']==0 for row in rows)
