"""Preserve prepared candidate receipts and exact author proofs, without integrating products."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

MAIN=Path(r'F:\MetodoBaseWeb-execution-20261018')
EV=MAIN/'docs/implementation/20261018-evolution/evidence'
TMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
CAND=Path(r'F:\mb-mfa31-compose-20261019')
OUT=EV/'prepared-wave119-20261019'
SHA=lambda b:hashlib.sha256(b).hexdigest()
git=lambda root,*args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git(MAIN,'rev-parse','HEAD').decode().strip()=='145b9d409e0c94cfd2cb813d47fa7f9d011096fd'
assert git(CAND,'rev-parse','HEAD').decode().strip()=='4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae'
assert not git(MAIN,'status','--porcelain','--untracked-files=no')
assert not git(CAND,'status','--porcelain','--untracked-files=no')

def scan(blob,name,depth=0):
    assert depth<5
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=match.start()
        assert not(p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p])),name
    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+|otpauth://totp/[^\s\x22\x27]+\?secret=[A-Z2-7]{16,}',blob),name
    if name.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(blob)) as arc:
            members=[(m.filename,arc.read(m)) for m in arc.infolist() if not m.is_dir()]
    elif name.lower().endswith('.tar'):
        with tarfile.open(fileobj=io.BytesIO(blob)) as arc:
            members=[]
            for m in arc.getmembers():
                if m.isdir():continue
                assert m.isreg(),(name,m.name)
                members.append((m.name,arc.extractfile(m).read()))
    else:return
    seen=set()
    for child,data in members:
        p=PurePosixPath(child)
        assert not p.is_absolute() and '..' not in p.parts and child not in seen and len(data)<50_000_000
        seen.add(child)
        scan(data,name+'/'+child,depth+1)

sources={}
directories=[
 'metodobase-mfa-ui31-browser-copy-wait-20261019',
 'metodobase-mfa31-fixture-compose-v2-20261019',
 'metodobase-member-vm-causality-20261019',
 'metodobase-member-consumers31-prepare-20261019',
 'metodobase-member-consumers31-final-20261019',
 'metodobase-mfa31-summary-fix-20261019',
 'metodobase-expat-m2-native-context-20261019',
 'metodobase-apt-metadata-root-raw-20261019',
]
for name in directories:
    parent=TMP/name
    assert parent.is_dir(),name
    for p in parent.rglob('*'):
        if p.is_file():
            assert not p.is_symlink() and p.suffix not in ('.pyc',)
            sources[name+'/'+p.relative_to(parent).as_posix()]=p.read_bytes()
for name in ['metodobase-mfa31-fixture-compose.py','metodobase-mfa31-fixture-compose-v2-prepare.py',
             'metodobase-mfa31-fixture-assert-count.py','metodobase-mfa31-fixture-compose-count-cause.json',
             'metodobase-apt-metadata-root-raw-continue.py','metodobase-apt-metadata-root-raw-continue-v2-prepare.py']:
    sources['preparation/'+name]=(TMP/name).read_bytes()
sources['driver.py']=Path(__file__).read_bytes()
for name,blob in sources.items():scan(blob,name)
assert not OUT.exists()
OUT.mkdir()
(OUT/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in sources.items():
    target=OUT/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(blob)

# Author test adoption proof is transferred as immutable Git blobs, not EOL-converted checkout bytes.
prefix='docs/implementation/20261018-evolution/evidence/backend-mfa31-fixture-adoption'
freeze_blob=git(CAND,'show','HEAD:'+prefix+'/freeze.json')
assert SHA(freeze_blob)=='ff524d818c9da668f6c059d493f23fc6cce4ecb9bc5e278da8c030031ba34d59'
freeze=json.loads(freeze_blob)
target=EV/'backend-mfa31-fixture-adoption'
assert not target.exists()
target.mkdir()
for name,meta in freeze['proof_files'].items():
    blob=git(CAND,'show','HEAD:'+prefix+'/'+name)
    assert len(blob)==meta['bytes'] and SHA(blob)==meta['sha256']
    scan(blob,name)
    path=target/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(blob)
(target/'freeze.json').write_bytes(freeze_blob)

receipt={'main':'145b9d409e0c94cfd2cb813d47fa7f9d011096fd',
 'isolated_candidate':'4a5475ccd6c7ac7525e2a1e30f7d2801bf19aaae',
 'main_product_changed':False,'author_test_proofs_exact_Git_blobs':len(freeze['proof_files'])+1,
 'scope':[
  'Browser predicate one-literal correction c669, no browser failure invented.',
  'Fixture adoption automatic merge2010; initial guard count failed before merging, corrected counter scope, no altered AST comparison.',
  'Old EEa8 and current consumer fixture13/16; passive companion stubs establish cause only, not acceptance. Current31 fixture loads actual companions and preserves16 callbacks/runner byte exactly;16/16 root author replay, not independent.',
  'UX19 original mounted canary3red -> same3green4a; independent replay3+2 stored separately.',
  'Old7c Docker context exact174080B retained; native metadata failure preimage is separate; D60 metadata acceptance does not prove build/runtime.',
  'Root SSH read-only RAW provenance collector: first incorrect whole-base status equality guard failed after captures; first continuation guessed oldliblzma version and failed beforeSSH; v2 verifies actual native87 invariance, original base only explicitliblzma u1->u2, exact original image RootFS prefix, never-started basecontainer and keyring. No target mutation by those collectors.'
 ]}
(OUT/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
entries={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':SHA(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file()}
(OUT/'manifest.json').write_bytes((json.dumps({'files':entries},indent=2)+'\n').encode())
print(json.dumps({'prepared':len(entries),'manifest':SHA((OUT/'manifest.json').read_bytes()),'backend_proofs':len(freeze['proof_files'])+1}))
