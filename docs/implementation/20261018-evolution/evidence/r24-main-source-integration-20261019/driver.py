"""Integrate reviewed source exactly, with a separate safe evidence projection."""
from pathlib import Path
import hashlib,io,json,re,shutil,subprocess,sys,zipfile
root=Path(r'F:\MetodoBaseWeb-execution-20261018');run=root/'docs/implementation/20261018-evolution';ev=run/'evidence';temp=Path(r'C:\Users\Consu\AppData\Local\Temp')
author=Path(r'F:\mb-r24-invalidated-controls-20261019');pre=temp/'metodobase-r24-main-source-preflight-20261019';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
def sensitive(blob):
    for m in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=m.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob))
def safe(blob):
    assert not sensitive(blob)
    if zipfile.is_zipfile(io.BytesIO(blob)):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            assert sum(r.file_size for r in z.infolist())<50*1024*1024
            for row in z.infolist():
                if not row.is_dir():assert not sensitive(z.read(row)),row.filename
assert len(sys.argv)==2,'Supply exact final independent QA summary SHA256 after acceptance'
qa_summary=ev/'qa-r24-after-privacy-independent-20261019/final-summary.json'
assert sha(qa_summary.read_bytes())==sys.argv[1]
assert sha((ev/'security-r24-private-errors-independent-20261019/source.json').read_bytes())=='4a709db44b2bd60340e339bbd0ef46da28de1fef089a324b7d267e3a7bf9414b'
before='5949a2a90341f37469e1a1f5b6e855c2dfe7c2e4';final='4042d77b55b88fb200e7de1cbf41d75adc88d4f3'
assert git('rev-parse','HEAD',text=True).strip()==before and not git('status','--porcelain','--untracked-files=no')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=author,text=True).strip()==final
metadata=json.loads((pre/'receipt.json').read_bytes());assert metadata['main']==before
patch=(pre/'source.patch').read_bytes();assert sha(patch)==metadata['patch_sha256']
old_registry=(run/'TRAZABILIDAD.json').read_bytes()
pins={p.relative_to(root).as_posix():git('show','HEAD:'+p.relative_to(root).as_posix()) for p in sorted((root/'web/database/alembic/schema_targets').glob('*.json'))}
c4='web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py';pins[c4]=git('show','HEAD:'+c4)
projection=ev/'r24-author-private-projection-20261019';assert sha((projection/'manifest.json').read_bytes())=='94b74adc4aa80f136d71b89e4ae966f5447e19f94edb20269cca391205a4fbe7'
raw=set()
for name,meta in json.loads((projection/'manifest.json').read_bytes())['files'].items():
    path=projection/name;assert sha(path.read_bytes())==meta['sha256'] and path.stat().st_size==meta['bytes'];safe(path.read_bytes());raw.add(path)
raw.add(projection/'manifest.json')
for prefix in ['r24-invalidated-controls-author-20261019','r24-private-errors-author-20261019','r24-private-errors-seal-receipt-20261019']:
    source=author/'docs/implementation/20261018-evolution/evidence'/prefix;target=ev/prefix;assert not target.exists()
    for path in source.rglob('*'):
        if path.is_file():safe(path.read_bytes())
    shutil.copytree(source,target)
    for path in target.rglob('*'):
        if path.is_file():assert path.read_bytes()==(source/path.relative_to(target)).read_bytes();raw.add(path)
dest=ev/'r24-main-source-integration-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
for path in pre.iterdir():
    if path.is_file():safe(path.read_bytes());shutil.copyfile(path,dest/path.name)
shutil.copyfile(__file__,dest/'driver.py')
result=subprocess.run(['git','apply','--index','-'],cwd=root,input=patch,capture_output=True)
(dest/'apply.stdout.log').write_bytes(result.stdout);(dest/'apply.stderr.log').write_bytes(result.stderr);assert result.returncode==0
for name,meta in metadata['source_paths'].items():assert sha(git('show',':'+name))==meta['candidate_Git_sha256'],name
doc='docs/implementation/20261018-evolution/R24_PLAN_DIARIO_CONTRATO.md';body=git('show',final+':'+doc).decode()
old='`evidence/r24` conserva rojo/verde, fuentes RAW, SSR, cantidades puras, consumidores montados en memoria, HTTP SQLite y PostgreSQL restringido con migración30 real.'
new='La [proyección pública del autor](evidence/r24-author-private-projection-20261019/manifest.json) conserva rojo/verde, fuentes, SSR, cantidades puras, consumidores en memoria y HTTP SQLite/PostgreSQL con migración30 real. Cuatro valores CSRF de SSR sintético se sustituyeron únicamente en esta proyección; los RAW originales permanecen privados y sus hashes se vinculan en projection.json. Los dos ZIP de código se inspeccionaron por entrada y se conservan byte a byte.'
assert body.count(old)==1;(root/doc).write_bytes(body.replace(old,new).encode())
subprocess.run(['git','add','--',doc],cwd=root,check=True,capture_output=True)
receipt={'before':before,'author':'adc80c7edb6314a7851b9447bccb092a62c142d5','controls_fix':'9bfa76dee0dcda846d9d29ac79d0192289ebd2f2','final_candidate':final,'source_paths':metadata['source_paths'],'QA_final_summary_sha256':sys.argv[1],'security_backend_review':'fc3928d2cb8b0f5ba376d204084aea259f379a9edb800a07f99eb0dbde9fdcb1','security_delta_review':'4a709db44b2bd60340e339bbd0ef46da28de1fef089a324b7d267e3a7bf9414b','author_projection_manifest':'94b74adc4aa80f136d71b89e4ae966f5447e19f94edb20269cca391205a4fbe7','method':'25source paths byte-exact Git delta, no author ancestry with private SSR. One contract paragraph updates evidence provenance only. Original local private commits and criteria unchanged. No DDL/business quota change. Broad composed regression pending.'}
(dest/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());raw.update(p for p in dest.rglob('*') if p.is_file())
names=sorted(p.relative_to(root).as_posix() for p in raw)
for i in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','--',*names[i:i+25]],cwd=root,check=True,capture_output=True)
buf=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buf.index(b'\n',cursor);head=buf[cursor:end].split();assert head[1]==b'blob';size=int(head[2]);cursor=end+1;assert buf[cursor:cursor+size]==(root/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buf)
source=list(metadata['source_paths']);changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert changed==set(names+source+[doc])
subprocess.run(['git','diff','--cached','--check','--',*source,doc],cwd=root,check=True,capture_output=True)
assert (run/'TRAZABILIDAD.json').read_bytes()==old_registry
for name,blob in pins.items():assert git('show','HEAD:'+name)==blob
subprocess.run(['git','commit','-m','Integrate independently reviewed daily plan consumption with private failure headers'],cwd=root,check=True,capture_output=True)
for name,meta in metadata['source_paths'].items():assert sha(git('show','HEAD:'+name))==meta['candidate_Git_sha256']
assert subprocess.run(['git','merge-base','--is-ancestor','adc80c7edb6314a7851b9447bccb092a62c142d5','HEAD'],cwd=root).returncode==1
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'source_paths_exact':len(source),'raw_files_exact':len(names),'schema_pins_exact':len(pins),'registry_unchanged':True,'unsafe_author_ancestry_excluded':True,'broad_composed':'pending'}))
