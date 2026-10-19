from pathlib import Path
import sys,tarfile
roots=[Path('/home/lab/metodobase-runtime28-network-20261019'),Path('/home/lab/metodobase-runtime28-product-a781deb39fd74441baa6a37c1a0cab40')]
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for root in roots:
  for p in sorted(root.rglob('*')):
   rel=p.relative_to(root)
   if 'private' in rel.parts:continue
   assert not p.is_symlink()
   if p.is_file():t.add(p,arcname=root.name+'/'+rel.as_posix(),recursive=False)
