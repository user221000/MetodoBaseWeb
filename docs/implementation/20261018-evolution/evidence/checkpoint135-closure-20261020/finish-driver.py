"""Finish checkpoint135 after removing an unsealed control document's EOF blank."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint135-20261020')
P = D/'evidence/checkpoint135-closure-20261020'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()

def git(*args):
    return subprocess.run(['git',*args],cwd=R,capture_output=True,check=True)

BASE = 'a61f9e1a470dff5383be9155b2ac4e15cd6cbd08'
assert git('rev-parse','HEAD').stdout.decode().strip() == BASE
path = D/'NUEVOS_HALLAZGOS.md'
raw = path.read_bytes()
assert raw.endswith(b'\n\n')
(O/'NUEVOS_HALLAZGOS-unsealed-before.md').write_bytes(raw)
path.write_bytes(raw.rstrip()+b'\n')
git('-c','core.autocrlf=true','add','--renormalize','--',path.relative_to(R).as_posix())
checked = git('diff','--cached','--check')
(O/'whitespace-final.stdout').write_bytes(checked.stdout)
(O/'whitespace-final.stderr').write_bytes(checked.stderr)
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
prior = json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json').stdout)
immutable = lambda value: {r['id']:{k:r[k] for k in ('fuente','seccion','problema','criterio_exacto')} for r in value['requisitos']}
before = immutable(prior)
assert len(data['requisitos']) == 133 and all(immutable(data)[key] == value for key,value in before.items())
preserved = json.loads((O/'untracked-before.json').read_bytes())
assert all(sha((R/path).read_bytes()) == digest for path,digest in preserved.items())
imports = json.loads((P/'imports.json').read_bytes())
assert all(sha((R/path).read_bytes()) == digest and git('show',':'+path).stdout == (R/path).read_bytes()
    for item in imports for path,digest in item['hashes'].items())
assert all(path.startswith('docs/') for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt = {'base':BASE,'requirements':133,'prior_immutable_criteria_preserved':128,
    'untracked_files_preserved':len(preserved),'evidence_imports':30,'product_imported':False,
    'CRLF_raw_preserved':True,'whitespace_check_exit':0,
    'initial_control_error':'One unsealed control document ended with an extra blank line; preserved preimage, stripped only its EOF whitespace. Imported proofs unchanged.',
    'scope':'web_only_explicit_user_instruction','desktop_review_executed':False,'global_acceptance':False}
(P/'receipt.json').write_bytes(encode(receipt))
(P/'finish-driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',P.relative_to(R).as_posix())
git('diff','--cached','--check')
proc = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--check'],cwd=R,capture_output=True,check=True)
(O/'registry-final.stdout').write_bytes(proc.stdout)
(O/'registry-final.stderr').write_bytes(proc.stderr)
git('commit','-m','Limit execution to the web service and register confirmed review findings')
assert not git('status','--porcelain','-uno').stdout.strip()
result = {'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
