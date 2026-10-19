from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, shlex, subprocess, time

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = LAB / 'evidence/runtime28-native-20261019'
OUT = BASE / 'native'
OUT.mkdir(exist_ok=False)
REPO = Path(r'F:\MetodoBaseWeb-image-security-20261019')
HEAD = 'bc365c13b9af9e24129a56b4068059a67bb3afa0'
IMAGE = 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c'
def info(p):
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': p.stat().st_size, 'sha256': digest}
baseline = json.loads((LAB / 'evidence/recovery28-image-bc365c1/before.json').read_text())
def snapshot():
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
    cmd = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull,
           '-c', 'core.attributesFile=' + os.devnull, '-C', str(REPO)]
    assert subprocess.check_output(cmd + ['rev-parse', 'HEAD'], env=env).decode().strip() == HEAD
    assert subprocess.check_output(cmd + ['status', '--porcelain=v1', '--untracked-files=all'], env=env) == b''
    sources = {}
    for rel in baseline['tracked_sources']:
        p = REPO / rel
        assert p.is_file() and not p.is_symlink() and not (getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)
        sources[rel] = info(p)
    return {'tracked_sources': sources, 'git_controls': {p: info(Path(p)) if Path(p).is_file() else None for p in baseline['git_controls']}}
before = snapshot()
assert before == baseline
(OUT / 'before.json').write_text(json.dumps(before, indent=2) + '\n', encoding='utf-8')
probe = (BASE / 'scripts/native_probe.py').read_bytes()
probe_sha = hashlib.sha256(probe).hexdigest()
helper = LAB / 'scripts/guest_access.py'
assert info(helper)['sha256'] == '616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7'
spec = importlib.util.spec_from_file_location('owned_access', helper)
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)
remote = r'''import hashlib,json,os,pathlib,subprocess,sys,time
payload=sys.stdin.buffer.read()
assert hashlib.sha256(payload).hexdigest()==PAYLOAD_SHA
image=IMAGE
assert json.loads(subprocess.check_output(['sudo','-n','docker','image','inspect','--format','{{json .Id}}',image]))==image
assert subprocess.check_output(['sudo','-n','docker','ps','-q'])==b''
root=pathlib.Path('/home/lab/metodobase-runtime28-native-20261019');root.mkdir(mode=0o700,exist_ok=False)
args=['sudo','-n','docker','create','-i','--name','metodobase-native28-99c846bd',
 '--label','metodobase.lab.scope=runtime28-native-20261019','--network','none','--read-only',
 '--user','999:999','--cap-drop','ALL','--security-opt','no-new-privileges','--no-healthcheck',
 '--tmpfs','/tmp:rw,noexec,nosuid,size=32m','--pids-limit','256','--memory','768m',
 '--workdir','/','--entrypoint','python',image,'-B','-']
cid=subprocess.check_output(args,text=True).strip()
print('OWNED_NATIVE_CONTAINER '+cid,file=sys.stderr,flush=True)
record={'driver_pid':os.getpid(),'container_id':cid,'image_id':image,'command':args,'payload_sha256':PAYLOAD_SHA}
try:
 host=json.loads(subprocess.check_output(['sudo','-n','docker','inspect','--format','{{json .HostConfig}}',cid]))
 record['lab_flags']={k:host[k] for k in ['NetworkMode','ReadonlyRootfs','CapDrop','SecurityOpt','Memory','PidsLimit','Binds']}
 assert record['lab_flags']['NetworkMode']=='none' and record['lab_flags']['ReadonlyRootfs'] is True
 started=time.monotonic()
 p=subprocess.run(['sudo','-n','docker','start','-a','-i',cid],input=payload,stdout=sys.stdout.buffer,stderr=sys.stderr.buffer)
 record['exit']=p.returncode;record['seconds']=round(time.monotonic()-started,3)
 record['state']=json.loads(subprocess.check_output(['sudo','-n','docker','inspect','--format','{{json .State}}',cid]))
 assert record['state']['ExitCode']==p.returncode
finally:
 assert json.loads(subprocess.check_output(['sudo','-n','docker','inspect','--format','{{json .Id}}',cid]))==cid
 subprocess.run(['sudo','-n','docker','rm',cid],check=True,stdout=subprocess.DEVNULL)
 record['container_removed']=True
 (root/'native-control.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(record['exit'])
'''.replace('PAYLOAD_SHA', repr(probe_sha)).replace('IMAGE', repr(IMAGE))
compile(remote, 'owned-native-controller', 'exec')
with (OUT / 'native.json').open('xb') as stdout, (OUT / 'native.log').open('xb') as stderr, (BASE / 'scripts/native_probe.py').open('rb') as stdin:
    result = access.run('/opt/metodobase-lab/python/bin/python3.12 -c ' + shlex.quote(remote),
                        stdin=stdin, stdout=stdout, stderr=stderr, timeout=1200)
control = access.run('cat /home/lab/metodobase-runtime28-native-20261019/native-control.json', timeout=30)
(OUT / 'controller.json').write_bytes(control.stdout)
assert control.returncode == 0
after = snapshot()
(OUT / 'after.json').write_text(json.dumps(after, indent=2) + '\n', encoding='utf-8')
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'source_head': HEAD, 'image_id': IMAGE,
           'probe_sha256': probe_sha, 'exit': result.returncode, 'source_and_git_controls_stable': before == after,
           'tracked_sources': len(before['tracked_sources']), 'artifacts': {p.name: info(p) for p in OUT.iterdir() if p.is_file()}}
if result.returncode == 0:
    report = json.loads((OUT / 'native.json').read_text())
    summary.update(elf_count=report['elf_count'], versions=report['versions'], native_errors=report['errors'])
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
assert before == after
raise SystemExit(result.returncode)
