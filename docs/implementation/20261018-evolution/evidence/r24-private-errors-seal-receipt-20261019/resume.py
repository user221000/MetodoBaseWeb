from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path(r'F:\mb-r24-invalidated-controls-20261019');base=root/'docs/implementation/20261018-evolution/evidence'
ev=base/'r24-private-errors-author-20261019';manifest=json.loads((ev/'manifest.json').read_bytes())
for name,meta in manifest.items():assert hashlib.sha256((ev/name).read_bytes()).hexdigest()==meta['sha256']
source=['web/middleware/security_headers.py','tests/test_diary_private_headers.py']
subprocess.run(['git','diff','--cached','--check','--',*source],cwd=root,check=True)
for path in ev.rglob('*'):
    if path.is_file():assert subprocess.check_output(['git','show',':'+path.relative_to(root).as_posix()],cwd=root)==path.read_bytes(),path
receipt=base/'r24-private-errors-seal-receipt-20261019';receipt.mkdir(exist_ok=False)
(receipt/'.gitattributes').write_bytes(b'* -text\n')
shutil.copyfile(__file__,receipt/'resume.py')
record={'author_manifest_sha256':hashlib.sha256((ev/'manifest.json').read_bytes()).hexdigest(),'files_raw_byte_exact_Git':sum(p.is_file() for p in ev.rglob('*')),'source_diff_check_exit':0,'preserved_sealer_attempt':{'driver_sha256':hashlib.sha256((ev/'metodobase-r24-privacy-seal.py').read_bytes()).hexdigest(),'exit':1,'cause':'git diff --check applied to raw CRLF proof bytes reported line terminators as trailing whitespace; no proof or criterion changed. Resume checks source paths only and independently authenticates every raw staged proof byte.'},'scope':'No test repeated or rewritten; pending independent QA final-source acceptance.'}
(receipt/'receipt.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
subprocess.run(['git','-c','core.autocrlf=false','add','--',str(receipt.relative_to(root))],cwd=root,check=True)
for path in receipt.rglob('*'):
    if path.is_file():assert subprocess.check_output(['git','show',':'+path.relative_to(root).as_posix()],cwd=root)==path.read_bytes()
result=subprocess.run(['git','commit','-m','fix(diary): preserve private headers on every response and failure'],cwd=root,capture_output=True,check=True)
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'freeze_sha256':hashlib.sha256((ev/'source-freeze.json').read_bytes()).hexdigest(),'manifest_sha256':record['author_manifest_sha256'],'files':record['files_raw_byte_exact_Git']}))
