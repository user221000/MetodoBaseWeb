from pathlib import Path
import hashlib,json,re,shutil,subprocess
root=Path(r'F:\mb-r24-invalidated-controls-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
ev=root/'docs/implementation/20261018-evolution/evidence/r24-private-errors-author-20261019';ev.mkdir(exist_ok=False)
(ev/'.gitattributes').write_bytes(b'* -text\n')
for mode in ['before','after']:
    shutil.copytree(tmp/('metodobase-r24-privacy-root-'+mode+'-20261019'),ev/mode)
shutil.copytree(tmp/'metodobase-r24-privacy-focal-20261019',ev/'maintained')
for name in ['metodobase-r24-privacy-root.py','metodobase-r24-privacy-focal.py','metodobase-r24-privacy-seal.py']:
    shutil.copyfile(tmp/name,ev/name)
(ev/'README.txt').write_bytes(('Same independent QA driver999: before4/4 failure, after4/4 pass on both factories, revoked-source and superseded-publication-ID404. New maintained diary boundaries/fallback plus old history/recovery/middleware94/94 pass. Source status before/after explicitly captured; after is parent9bfa with working middleware delta, not a tested future commit. No PostgreSQL/browser/network; independent acceptance and fresh final browser still pending.\n').encode())
source=['web/middleware/security_headers.py','tests/test_diary_private_headers.py']
subprocess.run(['git','add','--',*source],cwd=root,check=True)
freeze={'parent':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'sources':{n:{'working_sha256':hashlib.sha256((root/n).read_bytes()).hexdigest(),'Git_blob_sha256':hashlib.sha256(subprocess.check_output(['git','show',':'+n],cwd=root)).hexdigest()} for n in source},'criteria_unchanged_driver_sha256':'999f84c84996de56b2fbbc8aa66a2ed1c585f96cc686ca8cf9724d5ba35b6a22','scope':'Diary root and slash family only, always private Cache-Control and Referrer-Policy, including opaque500 using existing factory body. No DDL or business-state change.'}
(ev/'source-freeze.json').write_bytes((json.dumps(freeze,indent=2)+'\n').encode())
def token(blob):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=match.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|sk_live_[A-Za-z0-9]+|rk_live_[A-Za-z0-9]+',blob))
paths=sorted(p for p in ev.rglob('*') if p.is_file())
for path in paths:assert not token(path.read_bytes()),path
manifest={p.relative_to(ev).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in paths}
(ev/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
subprocess.run(['git','-c','core.autocrlf=false','add','--',str(ev.relative_to(root))],cwd=root,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=root,check=True)
for path in ev.rglob('*'):
    if path.is_file():assert subprocess.check_output(['git','show',':'+path.relative_to(root).as_posix()],cwd=root)==path.read_bytes(),path
subprocess.run(['git','commit','-m','fix(diary): preserve private headers on every response and failure'],cwd=root,check=True)
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'freeze_sha256':hashlib.sha256((ev/'source-freeze.json').read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((ev/'manifest.json').read_bytes()).hexdigest(),'raw_files':len(manifest)+1}))
