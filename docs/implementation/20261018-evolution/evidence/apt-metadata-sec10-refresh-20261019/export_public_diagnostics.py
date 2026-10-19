from pathlib import Path
import io,json,hashlib,subprocess,sys,tarfile
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-m2-native-validation-20261019')
sys.path.insert(0,str(LAB/'scripts'))
import guest_access
remote="""python3 - <<'PY'
from pathlib import Path
import sys,tarfile
root=Path('/var/tmp/metodobase-expat-m2-native-20261019/apt-failure-v2')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for file in sorted(root.iterdir()):
  if file.is_file() and not file.is_symlink():
   assert file.stat().st_size<500000
   tar.add(file,arcname=file.name,recursive=False)
PY
"""
r=guest_access.run(remote,timeout=45)
(OUT/'public-apt-diagnostics-export.tar').write_bytes(r.stdout)
(OUT/'public-apt-diagnostics-export.stderr').write_bytes(r.stderr)
assert r.returncode==0
target=OUT/'public-apt-diagnostics';target.mkdir()
with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
 assert len(tar.getmembers())==10
 for member in tar:
  assert member.isfile() and member.name==Path(member.name).name and member.size<500000
  (target/member.name).write_bytes(tar.extractfile(member).read())
print(json.dumps({'public_files':len(list(target.iterdir())),'archive_bytes':len(r.stdout),'sha256':hashlib.sha256(r.stdout).hexdigest()}))

