"""Resume the uncommitted proof packaging after Git's stat cache kept an old blob."""
import hashlib
from pathlib import Path
import shutil
import subprocess

root=Path('F:/MetodoBaseWeb-execution-20261018')
ev=root/'docs/implementation/20261018-evolution/evidence'
folders=['history-landing-ci-independent-20261019','history-landing-main-ci-review-20261019','linux-recovery28-image-bc365c1','linux-owned-shutdown-20261019']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip().startswith('52af400')
for name in folders:
    assert (ev/name/'.gitattributes').read_bytes()==b'# Preserve original bytes in this new evidence directory only.\n* -text\n'
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',(ev/name).relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
shutil.copyfile(__file__,ev/'ci-image105-restage-driver.py')
prior=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci-image105-evidence-commit-v2-20261019.py')
source=prior.read_text(encoding='utf-8')
# Execute the unchanged verification/commit tail, with this correction driver also
# included in its exact owned path set and its explicit packaging erratum.
tail=source[source.index('raw=[ev/') :]
tail=tail.replace("raw=[ev/'ci-image105-evidence-commit-driver.py',bundle]", "raw=[ev/'ci-image105-evidence-commit-driver.py',bundle,ev/'ci-image105-restage-driver.py']", 1)
tail=tail.replace('Original helper retained. Added scoped -text attributes only to these four new proof folders and restaged;', 'Original helpers retained. Scoped -text attributes added only to these four new proof folders. Normal add retained a stale cached blob in the second attempt, so v3 used explicit renormalize under the scoped attributes before verification;')
assert tail.count('assert blob==(root/name).read_bytes(),name')==1
namespace={}
exec(compile(source[:source.index('assert subprocess.check_output')],str(prior),'exec'),namespace)
namespace.update(bundle=ev/'ci-image105-commit-runners-raw.zip', folders=folders,
                 docs=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','VALIDACION.md','CAMBIOS.md','ENTREGA.md'])
exec(compile(tail,str(prior)+'::verified-tail','exec'),namespace)
