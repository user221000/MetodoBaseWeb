"""Seal only historical test targeting and exact before/after witnesses."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
root=Path(r'F:\mb-r12-history30-20261019');temporary=Path(r'C:\Users\Consu\AppData\Local\Temp')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='ea66afbfe323cd5ac86e24705e2534b54c7bbe13'
ev=root/'docs/implementation/20261018-evolution/evidence/history30-historical29-author-20261019';ev.mkdir(exist_ok=False);(ev/'.gitattributes').write_bytes(b'* -text\n')
for label,name in [('before','metodobase-history30-historical29-before-20261019'),('after','metodobase-history30-historical29-after-20261019')]:
    (ev/label).mkdir()
    for path in sorted((temporary/name).iterdir()):
        if path.is_file():shutil.copyfile(path,ev/label/path.name)
for name in ['metodobase-history30-historical29-before.py','metodobase-history30-historical29-after.py','metodobase-history30-historical29-prepare.py','metodobase-history30-historical29-target-proof-20261019.json','metodobase-history30-historical29-seal.py']:shutil.copyfile(temporary/name,ev/name)
summary=json.loads((ev/'after/summary.json').read_bytes());assert summary['cases']==10 and summary['exit']==0 and summary['sources_packages_plugin_stable']
closure=json.loads((ev/'after/database-closure.json').read_bytes());assert len(closure['created_exact'])==len(closure['closed_and_independently_absent'])==5 and closure['same_exact_names'] and not closure['pending']
proof=json.loads((ev/'metodobase-history30-historical29-target-proof-20261019.json').read_bytes());assert proof['AST_inverse_exact'] and proof['default28_rejection_byte_exact']
source=['tests/integration_client_link_migrations.py','docs/implementation/20261018-evolution/HISTORICO29_EN30.md'];sha=lambda value:hashlib.sha256(value).hexdigest()
manifest={'base':'ea66afbfe323cd5ac86e24705e2534b54c7bbe13','scope':'Three explicit expected_revision29 keywords in historical tests only; product and old default rejection unchanged.','before_SQLite':{'failed':3,'passed':2},'after_actual_SQLite_PG':10,'owned_PG_exact_closed':5,'AST_inverse_exact':True,'sources_packages_plugin_stable':True,'source_files':summary['sources'],'packages':summary['packages'],'source':{name:{'RAW_sha256':sha((root/name).read_bytes()),'GitLF_sha256':sha((root/name).read_bytes().replace(b'\r\n',b'\n'))} for name in source},'files':{path.relative_to(ev).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(ev.rglob('*')) if path.is_file()}}
(ev/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
token=re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])')
for path in ev.rglob('*'):
    if path.is_file() and path.suffix in {'.json','.xml','.log'}:assert not token.search(path.read_bytes()),path
raw=sorted(path.relative_to(root).as_posix() for path in ev.rglob('*') if path.is_file())
for index in range(0,len(raw),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*source],cwd=root,check=True,capture_output=True)
subprocess.run(['git','diff','--cached','--check','--',*source],cwd=root,check=True,capture_output=True)
for name in raw:assert subprocess.check_output(['git','show',':'+name],cwd=root)==(root/name).read_bytes(),name
assert set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1])==set(raw+source)
subprocess.run(['git','commit','-m','Keep explicit historical revision29 checks after model30'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'manifest_sha256':sha((ev/'manifest.json').read_bytes()),'RAW_blobs':len(raw),'cases':10}))
