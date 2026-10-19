from pathlib import Path
import hashlib
import json
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

root=Path('F:/mb-hidx-20261019')
target=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-before-null-order-fix-20261019.zip')
assert not target.exists()
paths=subprocess.check_output(['git','ls-files','-m','-o','--exclude-standard','-z'],cwd=root).decode().split('\0')[:-1]
assert len(paths)==11,len(paths)
with ZipFile(target,'x',ZIP_DEFLATED) as archive:
    for name in sorted(paths):archive.writestr(name,(root/name).read_bytes())
print(json.dumps({'archive':str(target),'files':len(paths),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'purpose':'Exact current candidate before changing PostgreSQL nonnullable id ordering; failure tests/logs/plans remain separately preserved.'}))
