"""Build an exact Git-blob context from local COPY inputs only; no VM actions."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import shlex
import subprocess
import tarfile
import zipfile

root=Path(r'F:\mb-mfa31-runtime-terminal-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
out=tmp/'metodobase-mfa31-runtime-terminal-context-20261019';assert not out.exists()
head='262f3b9687f911c5d6d4a7f88b58f326044f08f8'
git=lambda *args,**kwargs:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root,**kwargs)
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain','--untracked-files=no')
docker=git('show',head+':Dockerfile');sources=[]
for line in docker.decode().splitlines():
    if not line.startswith('COPY '):continue
    words=shlex.split(line)
    if words[1].startswith('--from='):continue
    assert len(words)>=3 and all(not word.startswith('--') for word in words[1:])
    for source in words[1:-1]:
        assert source not in {'.','/'} and not any(c in source for c in '*?[')
        assert not PurePosixPath(source).is_absolute() and '..' not in PurePosixPath(source).parts
        sources.append(source)
entries={}
for row in git('ls-tree','-r','-z',head).split(b'\0'):
    if not row:continue
    meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split();name=name.decode()
    selected=name in {'Dockerfile','.dockerignore'} or any(name==source.rstrip('/') or (source.endswith('/') and name.startswith(source)) or (not source.endswith('/') and name.startswith(source+'/')) for source in sources)
    if not selected:continue
    assert kind=='blob' and mode in {'100644','100755'},name
    path=PurePosixPath(name)
    # Additional exclusions mirror or strengthen existing Dockerignore rules;
    # code, locks, templates, fonts and ordinary public assets remain Git exact.
    if '__pycache__' in path.parts or name.startswith('web/static/uploads/') or path.name.startswith('.env'):
        continue
    if path.suffix.lower() in {'.db','.pyc','.log','.md','.bat','.spec'} or path.name=='conftest.py':
        continue
    entries[name]={'mode':mode,'oid':oid}
for source in sources:
    prefix=source.rstrip('/')
    assert any(name==prefix or name.startswith(prefix+'/') for name in entries),source
assert not any(name.startswith(('docs/','tests/','assets/','ui_desktop/')) for name in entries)
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
ordered=sorted(entries)
batch=git('cat-file','--batch',input=('\n'.join(entries[name]['oid'] for name in ordered)+'\n').encode())
offset=0;blobs={}
for name in ordered:
    end=batch.index(b'\n',offset);oid,kind,size=batch[offset:end].decode().split();size=int(size)
    assert oid==entries[name]['oid'] and kind=='blob'
    blob=batch[end+1:end+1+size];offset=end+1+size
    assert batch[offset:offset+1]==b'\n';offset+=1
    assert len(blob)==size
    scan(blob,name);blobs[name]=blob
    entries[name].update(bytes=size,sha256=hashlib.sha256(blob).hexdigest())
assert offset==len(batch)
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
archive=out/'context.tar'
with tarfile.open(archive,'x',format=tarfile.PAX_FORMAT) as handle:
    for name in ordered:
        member=tarfile.TarInfo(name);member.size=len(blobs[name]);member.mode=int(entries[name]['mode'][-3:],8)
        member.uid=member.gid=0;member.mtime=0;member.uname=member.gname=''
        handle.addfile(member,io.BytesIO(blobs[name]))
digest=hashlib.sha256()
with archive.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
receipt={'source':head,'app_base':'6a75d096ea3d63d9e78c76d33b7e243160b23364',
 'native_source':'72c44a1834d7bd9803b4b8846c6c87e85a53bfd3','local_COPY_inputs':sources,
 'context_bytes':archive.stat().st_size,'context_sha256':digest.hexdigest(),'files':entries,
 'scope':'Git blobs only, explicit Docker COPY inputs and additional existing ignore exclusions; no VM upload/build/runtime acceptance.'}
(out/'manifest.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'context':str(archive),'files':len(entries),'bytes':archive.stat().st_size,'sha256':digest.hexdigest(),'source':head,'VM_mutated':False}))
