from pathlib import Path
import hashlib
import json
import tarfile

archive=Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\sca-native-triage31-20261019\primary\Python-3.12.15.tar.xz')
assert len(archive.read_bytes())==20829824
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a'
with tarfile.open(archive,mode='r:xz') as tar:
    name='Python-3.12.15/Modules/clinic/pyexpat.c.h'
    matches=[m for m in tar.getmembers() if m.name==name]
    assert len(matches)==1 and matches[0].isreg() and not(matches[0].issym() or matches[0].islnk())
    header=tar.extractfile(matches[0]).read()
    source=tar.extractfile('Python-3.12.15/Modules/pyexpat.c').read()
    assert b'#include "clinic/pyexpat.c.h"' in source
    result={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
     'path':'Modules/clinic/pyexpat.c.h','bytes':len(header),'sha256':hashlib.sha256(header).hexdigest(),
     'source_include_present':True,'scope':'Read-only local authenticated archive inspection; no compiler/runtime claim.'}
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-clinic-inspection-20261019')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'header.raw.h').write_bytes(header)
(out/'receipt.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(result))
