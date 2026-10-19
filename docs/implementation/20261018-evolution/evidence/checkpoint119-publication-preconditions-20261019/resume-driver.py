"""Resume assembled documentation after its missing causal-summary link was rejected."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys

ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018')
RUN=ROOT/'docs/implementation/20261018-evolution'
EV=RUN/'evidence'
TMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
BASE='145b9d409e0c94cfd2cb813d47fa7f9d011096fd'
git=lambda *args,**kw:subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT,**kw)
assert git('rev-parse','HEAD').decode().strip()==BASE
expected={'CAMBIOS.md','DECISIONES.md','ENTREGA.md','ESTADO.md','RIESGOS.md','TRAZABILIDAD.json','VALIDACION.md'}
assert set(git('diff','--name-only','-z').decode().split('\0')[:-1])=={'docs/implementation/20261018-evolution/'+n for n in expected}
assert not git('diff','--cached','--name-only')
v2=(TMP/'metodobase-checkpoint119-v2.py').read_bytes()
cause=json.loads((TMP/'metodobase-checkpoint119-publication-precondition-20261019/cause.json').read_bytes())
assert hashlib.sha256(v2).hexdigest()==cause['v2_sha256']
tree=ast.parse(v2)
boundary=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='data' for t in n.targets))
prelude=tree.body[:boundary]
# Initial clean-tree gate was satisfied on the first run; the assembled seven docs are now explicitly expected above.
guards=[n for n in prelude if isinstance(n,ast.Assert) and "status" in ast.unparse(n)]
assert len(guards)==1
prelude.remove(guards[0])
namespace={'__file__':str(TMP/'metodobase-checkpoint119-v2.py'),'__name__':'checkpoint119_verify_resume'}
exec(compile(ast.Module(body=prelude,type_ignores=[]),'checkpoint119-exact-authentication','exec'),namespace)

refused=EV/'checkpoint119-publication-preconditions-20261019'
refused.mkdir(exist_ok=False)
(refused/'.gitattributes').write_bytes(b'* -text\n')
for p in (TMP/'metodobase-checkpoint119-publication-precondition-20261019').iterdir():
    if p.is_file() and p.name!='.gitattributes':(refused/p.name).write_bytes(p.read_bytes())
(refused/'second-driver.py').write_bytes(v2)
(refused/'resume-driver.py').write_bytes(Path(__file__).read_bytes())
(refused/'resume-initial-driver.py').write_bytes((TMP/'metodobase-checkpoint119-resume.py').read_bytes())
(refused/'resume-prepare.py').write_bytes((TMP/'metodobase-checkpoint119-resume-v2-prepare.py').read_bytes())
(refused/'second-cause.json').write_bytes((json.dumps({'failure':'Registry rejected an evidence link named receipt.json; the recorded causal artifact is summary.json.',
 'first_seven_documents_assembled':True,'nothing_staged_or_committed':True,'product_unchanged':True,
 'correction':'Only the invalid reference is corrected. The full manifest/blob authentication is replayed before continuing; previous failures and both drivers retained.'},indent=2)+'\n').encode())

data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{r['id']:{key:r[key] for key in fields} for r in value['requisitos']}
before=criteria(json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json')))
assert len(before)==110 and len(criteria(data))==112
assert {k:criteria(data)[k] for k in before}==before
bad='evidence/prepared-wave119-20261019/metodobase-member-vm-causality-20261019/receipt.json'
good=bad.removesuffix('receipt.json')+'summary.json'
assert (RUN/good).is_file()
qa=next(r for r in data['requisitos'] if r['id']=='QA-12')
assert qa['evidencia'].count(bad)==1
qa['evidencia']=[good if r==bad else r for r in qa['evidencia']]
(RUN/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
result=subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,capture_output=True)
(refused/'final-registry.stdout.raw.log').write_bytes(result.stdout)
(refused/'final-registry.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode(errors='replace')
assert {k:criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))[k] for k in before}==before
for p in refused.iterdir():
    if p.is_file():namespace['scan'](p.read_bytes(),p.name);namespace['raw'].add(p)
namespace.update({'data':data,'before':before,'criteria':criteria,'__file__':str(Path(__file__))})
start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='seal' for t in n.targets))
exec(compile(ast.Module(body=tree.body[start:],type_ignores=[]),'checkpoint119-exact-stage-and-seal','exec'),namespace)
