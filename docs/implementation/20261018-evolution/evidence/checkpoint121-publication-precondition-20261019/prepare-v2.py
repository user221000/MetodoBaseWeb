from pathlib import Path
import hashlib
import json

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
old=tmp/'metodobase-checkpoint121.py'
new=tmp/'metodobase-checkpoint121-v2.py'
source=old.read_text(encoding='utf8')
needle="('security-expat-clinic-independent-20261019','source.json','66f909964f8fa7cc49c4ad26ef55244a6b8399f4b5496d493a82ab5f10a79aa3')"
replacement="('security-expat-clinic-independent-20261019','manifest.json','7e0d481601b2f28622506c85437323b625776c7406abf84e3eb3b50dc8da0804')"
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="""assert not target.exists()
target.mkdir();(target/'.gitattributes').write_bytes(b'* -text\\n')
for name,blob in originals.items():
    path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
(target/'manifest.json').write_bytes(manifest)"""
replacement="""existing=target.exists()
if not existing:
    target.mkdir();(target/'.gitattributes').write_bytes(b'* -text\\n')
else:
    assert (target/'.gitattributes').read_bytes()==b'* -text\\n'
    assert (target/'manifest.json').read_bytes()==manifest
for name,blob in originals.items():
    path=target/name
    if existing:assert path.read_bytes()==blob
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
if not existing:(target/'manifest.json').write_bytes(manifest)"""
assert source.count(needle)==1
source=source.replace(needle,replacement)
needle="data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())"
replacement="""attestation=EV/'security-expat-clinic-independent-20261019/source.json'
assert SHA(attestation.read_bytes())=='66f909964f8fa7cc49c4ad26ef55244a6b8399f4b5496d493a82ab5f10a79aa3'
assert json.loads(attestation.read_bytes())['proof_manifest_sha256']=='7e0d481601b2f28622506c85437323b625776c7406abf84e3eb3b50dc8da0804'
scan(attestation.read_bytes(),attestation.name);raw.add(attestation)
refusal=EV/'checkpoint121-publication-precondition-20261019'
refusal.mkdir(exist_ok=False);(refusal/'.gitattributes').write_bytes(b'* -text\\n')
for p in (TMP/'metodobase-checkpoint121-publication-precondition-20261019').iterdir():
    if p.is_file():(refusal/p.name).write_bytes(p.read_bytes());raw.add(refusal/p.name)
raw.add(refusal/'.gitattributes')
"""+needle
assert source.count(needle)==1
source=source.replace(needle,replacement)
assert not new.exists()
new.write_bytes(source.encode())
out=tmp/'metodobase-checkpoint121-publication-precondition-20261019'
out.mkdir(exist_ok=False)
(out/'driver-before.py').write_bytes(old.read_bytes())
(out/'prepare-v2.py').write_bytes(Path(__file__).read_bytes())
(out/'cause.json').write_bytes((json.dumps({'failure':'TypeError while treating independent attestation fields as a file manifest. This producer has a separate manifest, unlike previous source-file-list formats.',
 'state':'No registry/docs/staging/commit changes. Native failure files had already been copied and remain exact.',
 'correction':'Authenticate the actual manifest7e0d and separately bind attestation66f9 to its proof_manifest_sha256. Reuse original native copy only after exact byte verification.',
 'original_driver_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'v2_sha256':hashlib.sha256(new.read_bytes()).hexdigest()},indent=2)+'\n').encode())
print(json.dumps({'prepared':str(new),'source_evidence_unchanged':True}))
