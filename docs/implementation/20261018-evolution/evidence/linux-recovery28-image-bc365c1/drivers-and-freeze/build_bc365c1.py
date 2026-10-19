from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,os,shlex,subprocess,sys,tarfile,time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
REPO=Path(r'F:\MetodoBaseWeb-image-security-20261019')
HEAD='bc365c13b9af9e24129a56b4068059a67bb3afa0'
OUT=LAB/'evidence/recovery28-image-bc365c1';OUT.mkdir(exist_ok=False)
TAG='metodobase-lab:recovery28-bc365c1'
REMOTE='/home/lab/metodobase-recovery28-bc365c1'
PATHS=['Dockerfile','.dockerignore','requirements_web.lock','requirements-container-bootstrap.lock',
       'config','core','src','api','web','utils','static','fonts','entrypoint.sh','alembic.ini','db_bootstrap.py']
GITENV={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
GITENV.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_ATTR_NOSYSTEM='1',GIT_NO_REPLACE_OBJECTS='1',GIT_OPTIONAL_LOCKS='0')
GIT=['git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,
     '-c','core.attributesFile='+os.devnull,'-c','core.excludesFile='+os.devnull,'-C',str(REPO)]
def git(*args,input_data=None):return subprocess.check_output(GIT+list(args),env=GITENV,input=input_data)
def sha(b):return hashlib.sha256(b).hexdigest()
def file_info(p):
    with p.open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
    return {'bytes':p.stat().st_size,'sha256':d}
def snapshot():
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert git('status','--porcelain=v1','--untracked-files=all')==b''
    files={}
    for rel in git('ls-files','-z').decode().rstrip('\0').split('\0'):
        p=REPO/rel
        assert p.is_file() and not p.is_symlink() and not(getattr(p.lstat(),'st_file_attributes',0)&0x400)
        files[rel]=file_info(p)
    gitdir=Path(git('rev-parse','--absolute-git-dir').decode().strip())
    common=Path(git('rev-parse','--path-format=absolute','--git-common-dir').decode().strip())
    controls=[gitdir/'index',common/'config',gitdir/'config.worktree',Path.home()/'.gitconfig',Path.home()/'.config/git/config']
    return {'tracked_sources':files,'git_controls':{str(p):file_info(p) if p.is_file() else None for p in controls}}

assert json.loads((LAB/'evidence/python31215-base-preload-abd559a/summary.json').read_text())['runtime_python']=='3.12.15'
before=snapshot();(OUT/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
tree={}
for item in git('ls-tree','-r','-z','--full-tree',HEAD,'--',*PATHS).split(b'\0'):
    if not item:continue
    metadata,name=item.split(b'\t',1);mode,kind,oid=metadata.decode().split();rel=name.decode('utf-8')
    assert kind=='blob' and mode in ('100644','100755')
    tree[rel]={'mode':mode,'oid':oid}
assert len(tree)==299,len(tree)
batch=git('cat-file','--batch',input_data=''.join(x['oid']+'\n' for x in tree.values()).encode())
offset=0;expected={}
for rel,entry in tree.items():
    end=batch.index(b'\n',offset);oid,kind,size=batch[offset:end].decode().split();size=int(size)
    assert oid==entry['oid'] and kind=='blob'
    blob=batch[end+1:end+1+size];assert batch[end+1+size:end+2+size]==b'\n';offset=end+2+size
    expected[rel]={'bytes':size,'sha256':sha(blob)}
archive=OUT/'build-context.tar'
with archive.open('xb') as stream:subprocess.run(GIT+['archive','--format=tar',HEAD,*PATHS],env=GITENV,stdout=stream,check=True)
archive_info=file_info(archive);actual={}
with tarfile.open(archive) as source:
    assert source.pax_headers.get('comment')==HEAD
    seen=[]
    for member in source.getmembers():
        rel=member.name;p=PurePosixPath(rel);seen.append(rel)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in rel and ':' not in rel
        assert member.isdir() or member.isfile(),'No links or special files'
        assert not any(part=='.git' or part.startswith('.env') or part.casefold() in ('backups','datos','licencias','instance') for part in p.parts)
        assert not rel.casefold().endswith(('.key','.pem','.pfx','.p12','.db','.sqlite','.sqlite3','.lic','.log'))
        if member.isfile():
            data=source.extractfile(member).read();actual[rel]={'bytes':len(data),'sha256':sha(data)}
    assert len(seen)==len(set(seen))==len({p.casefold() for p in seen})
assert actual==expected
(OUT/'context-files.json').write_text(json.dumps(actual,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('guest_access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
transport=OUT/'build-context.transport'
header=json.dumps({'inventory':actual},sort_keys=True,separators=(',',':')).encode('utf-8')+b'\n'
with transport.open('xb') as stream:
    stream.write(header)
    with archive.open('rb') as tarstream:
        while chunk:=tarstream.read(1024*1024):stream.write(chunk)
transport_info=file_info(transport)
(OUT/'transport.json').write_text(json.dumps({'transport':transport_info,'archive':archive_info,'framing':'Canonical JSON header plus LF plus exact Git tar; SHA256 binds header and archive.'},indent=2)+'\n',encoding='utf-8')
extract='''import hashlib,io,json,pathlib,sys,tarfile
frame=sys.stdin.buffer.read();assert hashlib.sha256(frame).hexdigest()==TRANSPORT_HASH
header,data=frame.split(b'\\n',1);inventory=json.loads(header)['inventory']
assert hashlib.sha256(data).hexdigest()==ARCHIVE_HASH
assert len(inventory)==299
root=pathlib.Path(DESTINATION)
assert str(root).startswith('/home/lab/metodobase-recovery28-') and not root.exists()
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
 names=[]
 for m in archive.getmembers():
  p=pathlib.PurePosixPath(m.name);names.append(m.name)
  assert not p.is_absolute() and '..' not in p.parts and '\\\\' not in m.name and ':' not in m.name
  assert m.isdir() or m.isfile()
  assert not any(x=='.git' or x.startswith('.env') for x in p.parts)
 assert len(names)==len(set(names))==len({x.casefold() for x in names})
 root.mkdir(exist_ok=False)
 archive.extractall(root,filter='data')
actual={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in root.rglob('*') if p.is_file()}
assert actual==inventory
print(json.dumps({'context_files':len(actual),'archive_sha256':hashlib.sha256(data).hexdigest(),'guest_context_exact':True}))
'''.replace('TRANSPORT_HASH',repr(transport_info['sha256'])).replace('ARCHIVE_HASH',repr(archive_info['sha256'])).replace('DESTINATION',repr(REMOTE))
compile(extract,'guest-extract','exec')
with transport.open('rb') as stream:transfer=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(extract),stdin=stream,timeout=300)
(OUT/'transfer.log').write_bytes(transfer.stdout+transfer.stderr);assert transfer.returncode==0
launch='''import json,os,subprocess,sys
active=subprocess.check_output(['sudo','-n','docker','ps','--format','{{.ID}} {{.Names}}'],text=True)
assert not active.strip(),'Another running container detected'
command=['sudo','-n','env','DOCKER_HOST=unix:///var/run/docker.sock','docker','build','--platform=linux/amd64','--pull=false','--force-rm',
 '--label','org.opencontainers.image.revision=HEAD','--tag','TAG','DESTINATION']
p=subprocess.Popen(command)
print('METODOBASE_BUILD_PROCESS '+json.dumps({'driver_pid':os.getpid(),'docker_client_pid':p.pid,'tag':'TAG','source':'HEAD'}),flush=True)
exit_code=p.wait();print('METODOBASE_BUILD_EXIT '+str(exit_code),flush=True)
raise SystemExit(exit_code)
'''.replace('HEAD',HEAD).replace('TAG',TAG).replace('DESTINATION',REMOTE)
started=time.monotonic()
print(json.dumps({'stage':'build','source':HEAD,'tag':TAG,'context_files':len(actual),'context_bytes':archive_info['bytes']}),flush=True)
with (OUT/'build.log').open('xb') as log:
    result=access.run('/opt/metodobase-lab/python/bin/python3.12 -c '+shlex.quote(launch),stdout=log,stderr=subprocess.STDOUT,timeout=3000)
after=snapshot();(OUT/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
summary={'finished_utc':datetime.now(timezone.utc).isoformat(),'source_commit':HEAD,'image_tag':TAG,'context_scope':PATHS,
         'archive':archive_info,'file_count':len(actual),'source_inventory_sha256':sha(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()),
         'build_exit':result.returncode,'build_seconds':round(time.monotonic()-started,3),
         'source_and_git_controls_stable':before==after,'archive_stable':file_info(archive)==archive_info,
         'scope':'Exact Git source build on owned Linux TCG guest. No application startup, PostgreSQL test, release or performance claim.'}
(OUT/'build-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2),flush=True)
assert before==after and file_info(archive)==archive_info
raise SystemExit(result.returncode)
