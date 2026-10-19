from pathlib import Path
import hashlib,json,shutil,subprocess,sys
root=Path(r'F:\MetodoBaseWeb-execution-20261018');run=root/'docs/implementation/20261018-evolution';ev=run/'evidence';base='eea8f773fba9b7f92241958139fcefa23b9ee1d4'
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
assert git('rev-parse','HEAD',text=True).strip()==base
receipt=ev/'checkpoint117-review.json';record=json.loads(receipt.read_bytes());assert record['base']==base and record['registry']==110
raw=set()
for name,meta in record['raw_files'].items():
    p=root/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256'] and p.stat().st_size==meta['bytes'];raw.add(p)
raw.add(receipt)
old=json.loads(git('show',base+':docs/implementation/20261018-evolution/TRAZABILIDAD.json'));current=json.loads((run/'TRAZABILIDAD.json').read_bytes());keys=['fuente','seccion','problema','criterio_exacto']
criteria=lambda data:{r['id']:{k:r[k] for k in keys} for r in data['requisitos']}
before=criteria(old);after=criteria(current);assert len(before)==109 and len(after)==110 and {k:after[k] for k in before}==before
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
proof=ev/'checkpoint117-seal-receipt-20261019';proof.mkdir(exist_ok=False);(proof/'.gitattributes').write_bytes(b'* -text\n');shutil.copyfile(__file__,proof/'resume.py')
ignored=['docs/implementation/20261018-evolution/evidence/main-r23-r24-regression-20261019/coverage.json','docs/implementation/20261018-evolution/evidence/main-r23-r24-regression-20261019/coverage.xml']
check=subprocess.run(['git','check-ignore','--no-index','--verbose','--',*ignored],cwd=root,capture_output=True);assert check.returncode==0
(proof/'ignore-cause.stdout.log').write_bytes(check.stdout);(proof/'ignore-cause.stderr.log').write_bytes(check.stderr)
note={'original_driver_sha256':hashlib.sha256((ev/'checkpoint117-driver.py').read_bytes()).hexdigest(),'original_review_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'cause':'Initial exact add batch returned1 for coverage JSON/XML excluded by existing .gitignore; it staged the other allowed files. Resume force-adds only the exact authenticated raw paths. No proof, test, criterion, filter or .gitignore changed.','previous_criteria_exact':109,'registry':110,'product_changed':False}
(proof/'receipt.json').write_bytes((json.dumps(note,indent=2)+'\n').encode());raw.update(p for p in proof.rglob('*') if p.is_file())
names=sorted(p.relative_to(root).as_posix() for p in raw);docs=[(run/n).relative_to(root).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md','NUEVOS_HALLAZGOS.md']]
for i in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[i:i+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
buf=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buf.index(b'\n',cursor);head=buf[cursor:end].split();assert head[1]==b'blob';size=int(head[2]);cursor=end+1;assert buf[cursor:cursor+size]==(root/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buf) and set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record composed broad regression and MFA parent eligibility finding'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no');print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_authenticated':len(names),'registry':110,'previous_criteria_exact':109}))
