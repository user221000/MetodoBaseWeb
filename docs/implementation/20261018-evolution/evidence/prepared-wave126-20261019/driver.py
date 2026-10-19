from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

root=Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
ev=Path('docs/implementation/20261018-evolution/evidence')
base='cac63688a2e677374518d0e0537f2a1ae617ee5c'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
sha=lambda blob:hashlib.sha256(blob).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
sources=[
 (Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\runtime31-f74a-logging-partial-public-20261019'),
  'b757fe2f19dde492daadc98dc596775f16199ab6a425bec4a17c80fef2c8faa8','ebc63a1d0cc6b21ccbd98a1a286703ee24c7848b2df95c669e8f8c722e403c9e'),
 (Path(r'F:\mb-qa-progress32-restore-20261019')/ev/'qa-progress32-populated-restore-independent-20261019',
  'bda114cd5ae664534c80cc53cf7a6e820f21f76aa96ce2daec05eb1b46893043','1837a6ecc95551ee20a389983428abaa271d2778dd754c9b19b7fdc398fddec4'),
 (root/ev/'root-google-subject-contract-review-20261019',
  '47f479889f5ff5693894909767df971f930116c897e1a1342c4f39ebc6c5d330',None),
]
contents={}
ledger=[]
for folder,manifest_sha,source_sha in sources:
    manifest_blob=(folder/'manifest.json').read_bytes();assert sha(manifest_blob)==manifest_sha
    if source_sha:assert sha((folder/'source.json').read_bytes())==source_sha
    manifest=json.loads(manifest_blob)
    for name,row in manifest.items():
        assert set(row)=={'bytes','sha256'}
        path=folder/name;assert path.resolve().is_relative_to(folder.resolve())
        blob=path.read_bytes();assert len(blob)==row['bytes'] and sha(blob)==row['sha256']
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            name=(ev/folder.name/path.relative_to(folder)).as_posix();blob=path.read_bytes()
            scan(blob,name);assert name not in contents;contents[name]=blob
            ledger.append({'path':name,'bytes':len(blob),'sha256':sha(blob),'source_manifest_sha256':manifest_sha})
prepared=ev/'prepared-wave126-20261019'
blobs={'driver.py':Path(__file__).read_bytes(),'.gitattributes':b'* -text\n',
       'import-ledger.json':(json.dumps({'base':base,'sources':[(str(p),m,s) for p,m,s in sources],'imports':ledger},indent=2)+'\n').encode()}
for name,blob in blobs.items():scan(blob,name);contents[(prepared/name).as_posix()]=blob
blobs['manifest.json']=(json.dumps({name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in blobs.items()},indent=2)+'\n').encode()
contents[(prepared/'manifest.json').as_posix()]=blobs['manifest.json']
for name,blob in sorted(contents.items(),key=lambda item:(Path(item[0]).name!='.gitattributes',item[0])):
    path=root/name
    if path.exists():assert path.read_bytes()==blob,name
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as handle:handle.write(blob)
receipt={'base':base,'files':{name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in contents.items()}}
out=tmp/'metodobase-checkpoint126-import-result.json';assert not out.exists()
out.write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'files':len(contents),'bytes':sum(map(len,contents.values())),'receipt':str(out)}))
