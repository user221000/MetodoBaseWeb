from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, shlex, subprocess

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = LAB / 'evidence/runtime28-native-20261019'
OUT = BASE / 'symlink-gate'
prepared = json.loads((OUT / 'preparation.json').read_text())
frame = OUT / 'qa.transport'
assert hashlib.sha256(frame.read_bytes()).hexdigest() == prepared['frame']['sha256']
IMAGE = 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c'
bootstrap = r'''import hashlib,io,json,pathlib,runpy,sys,tarfile
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==FRAME_SHA
header,tar=data.split(b'\n',1);files=json.loads(header)['files'];assert len(files)==498
assert hashlib.sha256(tar).hexdigest()==TAR_SHA
root=pathlib.Path('/qa');assert root.is_dir() and not any(root.iterdir())
with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
 names=[]
 for m in archive.getmembers():
  p=pathlib.PurePosixPath(m.name);names.append(m.name)
  assert m.isfile() and not p.is_absolute() and '..' not in p.parts and '\\' not in m.name and ':' not in m.name
  assert not any(part=='.git' or part.startswith('.env') for part in p.parts)
 assert len(names)==len(set(names))==len({n.casefold() for n in names})==len(files)
 archive.extractall(root,filter='data')
actual={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in root.rglob('*') if p.is_file()}
assert actual==files
sys.path.insert(0,'/qa/tools')
import pytest;assert pytest.__version__=='9.1.1'
runpy.run_path('/qa/runner.py',run_name='__main__')
'''.replace('FRAME_SHA', repr(prepared['frame']['sha256'])).replace('TAR_SHA', repr(prepared['tar']['sha256']))
compile(bootstrap, 'qa-symlink-bootstrap', 'exec')
remote = r'''import json,os,pathlib,subprocess,sys,time
image=IMAGE; payload=sys.stdin.buffer.read()
assert json.loads(subprocess.check_output(['sudo','-n','docker','image','inspect','--format','{{json .Id}}',image]))==image
assert subprocess.check_output(['sudo','-n','docker','ps','-q'])==b''
root=pathlib.Path('/home/lab/metodobase-runtime28-symlink-20261019');root.mkdir(mode=0o700,exist_ok=False)
command=['sudo','-n','docker','create','-i','--name','metodobase-symlink28-99c846bd',
 '--label','metodobase.lab.scope=runtime28-native-20261019','--network','none','--read-only',
 '--user','999:999','--cap-drop','ALL','--security-opt','no-new-privileges','--no-healthcheck',
 '--tmpfs','/tmp:rw,noexec,nosuid,size=64m,uid=999,gid=999','--tmpfs','/qa:rw,noexec,nosuid,size=32m,uid=999,gid=999',
 '--pids-limit','128','--memory','512m','--workdir','/qa','--entrypoint','python',image,'-B','-c',BOOTSTRAP]
cid=subprocess.check_output(command,text=True).strip();record={'driver_pid':os.getpid(),'container_id':cid,'image_id':image,'command':command}
try:
 started=time.monotonic()
 p=subprocess.run(['sudo','-n','docker','start','-a','-i',cid],input=payload,stdout=sys.stdout.buffer,stderr=sys.stderr.buffer)
 record['exit']=p.returncode;record['seconds']=round(time.monotonic()-started,3)
 record['state']=json.loads(subprocess.check_output(['sudo','-n','docker','inspect','--format','{{json .State}}',cid]))
 assert record['state']['ExitCode']==p.returncode
finally:
 assert json.loads(subprocess.check_output(['sudo','-n','docker','inspect','--format','{{json .Id}}',cid]))==cid
 subprocess.run(['sudo','-n','docker','rm',cid],check=True,stdout=subprocess.DEVNULL)
 record['container_removed']=True
 (root/'gate-control.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(record['exit'])
'''.replace('IMAGE', repr(IMAGE)).replace('BOOTSTRAP', repr(bootstrap))
compile(remote, 'owned-symlink-controller', 'exec')
helper = LAB / 'scripts/guest_access.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7'
spec = importlib.util.spec_from_file_location('access', helper)
access = importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
with frame.open('rb') as stdin, (OUT / 'run.log').open('xb') as stdout, (OUT / 'run.stderr.log').open('xb') as stderr:
    result = access.run('/opt/metodobase-lab/python/bin/python3.12 -c ' + shlex.quote(remote),
                        stdin=stdin, stdout=stdout, stderr=stderr, timeout=600)
control = access.run('cat /home/lab/metodobase-runtime28-symlink-20261019/gate-control.json', timeout=30)
assert control.returncode == 0
(OUT / 'controller.json').write_bytes(control.stdout)
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'image_id': IMAGE, 'exit': result.returncode,
           'prepared_frame_sha256': prepared['frame']['sha256'],
           'scope': 'Real Linux local-storage symlink unit gate, independent of PostgreSQL/runtime startup.'}
if result.returncode == 0:
    lines = (OUT / 'run.log').read_text().splitlines()
    records = [json.loads(line.split('SYMLINK28_RESULT ', 1)[1]) for line in lines if line.startswith('SYMLINK28_RESULT ')]
    assert len(records) == 1
    summary['actual'] = records[0]
    (OUT / 'junit.xml').write_text(records[0]['junit_xml'], encoding='utf-8')
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
raise SystemExit(result.returncode)
