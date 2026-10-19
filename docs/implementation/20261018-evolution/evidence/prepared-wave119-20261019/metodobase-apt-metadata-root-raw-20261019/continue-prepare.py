from pathlib import Path
import hashlib
import json

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
original=tmp/'metodobase-apt-metadata-root-raw-continue.py'
blob=original.read_bytes()
needle=b"assert changes=={'liblzma5:amd64':{'base':'5.8.1-1','failed_native':'5.8.1-1+deb13u2'}},changes"
assert blob.count(needle)==1
replacement=b"assert set(changes)=={'liblzma5:amd64'} and changes['liblzma5:amd64']['failed_native']=='5.8.1-1+deb13u2',changes"
updated=blob.replace(needle,replacement)
updated=updated.replace(b'Original raw/driver retained.',b'Original raw/driver retained. First continuation also assumed base5.8.1-1; raw pinned base has5.8.1-1+deb13u1. Refined guard accepts the actual pinned old version and requires the sole changed package targetu2; native-before versus native-after87comparison remains exact. Both first drivers are preserved.')
target=tmp/'metodobase-apt-metadata-root-raw-continue-v2.py'
with target.open('xb') as output:
    output.write(updated)
out=tmp/'metodobase-apt-metadata-root-raw-20261019'
(out/'continue-first-precondition.py').write_bytes(blob)
(out/'continue-prepare.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'first_sha256':hashlib.sha256(blob).hexdigest(),'refined_sha256':hashlib.sha256(updated).hexdigest(),
                  'correction':'No hard-coded guess of original base package version; exact pinned base raw remains authority. Sole liblzma targetu2 and all87native packages equality remain required.'}))
