"""Normalize only prose in Git; all staged RAW proofs retain exact bytes."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root=Path('F:/MetodoBaseWeb-execution-20261018')
run=root/'docs/implementation/20261018-evolution'
ev=run/'evidence'
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
assert git('rev-parse','HEAD',text=True).strip()=='b59c99f04c5bb164ec54a467c866bcca21a9e328'
docs=[(run/name).relative_to(root).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
folders=['desktop31215-independent-20261019','qa-r12-core29-independent-20261019','security-r12-core29-independent-20261019','security-r12-core29-v2-independent-20261019']
raw=[p for name in folders for p in (ev/name).rglob('*') if p.is_file()]
raw.extend([ev/name for name in ['checkpoint107-driver.py','checkpoint107-recovery.py','checkpoint107-recovery-first.py','checkpoint107-review.json']])
final=ev/'checkpoint107-finalize.py'
receipt=ev/'checkpoint107-packaging.json'
assert not final.exists() and not receipt.exists()
shutil.copyfile(__file__,final)
receipt.write_text(json.dumps({'RAW_scope':'Four new proof directories and coordinator receipts; all staged blobs checked byte for byte','prose_normalization':'Only eight control docs use normal repository autocrlf=true normalization; no RAW file normalized','packaging_errata':'Initial full-relative links corrected; recovery count11 corrected to9 before write; prose staging initially preserved CRLF and diffcheck rejected it. No product/test failure. Original scripts retained.','author_manifests_unchanged':True},indent=2)+'\n',encoding='utf-8')
raw.extend([final,receipt])
subprocess.run(['git','-c','core.autocrlf=true','add','--renormalize','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',final.relative_to(root).as_posix(),receipt.relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
assert not git('diff','--cached','--check','--',*docs,stderr=subprocess.STDOUT)
names=sorted(p.relative_to(root).as_posix() for p in raw)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names).encode())
cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);parts=buffer[cursor:end].split();assert parts[1]==b'blob'
    size=int(parts[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(root/name).read_bytes(),name
    cursor+=size+1
assert cursor==len(buffer)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','commit','-m','Record desktop93 and independent R12 core V1/V2 reviews'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_git_blobs_byte_identical':len(names),'prose_documents':8,'registry':104,'product_changes':False}))
