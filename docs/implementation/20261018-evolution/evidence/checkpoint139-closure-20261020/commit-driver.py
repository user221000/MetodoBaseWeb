"""Normalize only unsealed attribute metadata and commit the verified registry."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint139-20261020')
P = D/'evidence/checkpoint139-closure-20261020'
BASE = '1bb480e364073d1da85d926f675a88d4a9fe5481'
encode = lambda value:(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def git(*args):
    return subprocess.run(['git',*args],cwd=R,capture_output=True,check=True)


assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
attributes = R/'.gitattributes'
(O/'root-attributes-before-normalization.raw').write_bytes(attributes.read_bytes())
attributes.write_bytes(attributes.read_bytes().replace(b'\r\n',b'\n'))
git('-c','core.autocrlf=false','add','--','.gitattributes')
git('diff','--cached','--check')
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
prior = json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json').stdout)
criteria = lambda value:{row['id']:{key:row[key] for key in ('fuente','seccion','problema','criterio_exacto')} for row in value['requisitos']}
assert len(data['requisitos'])==140
assert all(criteria(data)[key]==value for key,value in criteria(prior).items())
assert next(row for row in data['requisitos'] if row['id']=='SEC19')['estado']=='en_revision'
checked = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--check'],cwd=R,capture_output=True)
(O/'registry-commit.stdout').write_bytes(checked.stdout)
(O/'registry-commit.stderr').write_bytes(checked.stderr)
assert checked.returncode==0
imports = json.loads((P/'imports.json').read_bytes())
paths = [path for value in imports for path in value['hashes']]+['docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_SNAPSHOT.json']
assert len(paths)==59 and all(git('show',':'+path).stdout==(R/path).read_bytes() for path in paths)
untracked = json.loads((O/'untracked-before.json').read_bytes())
assert len(untracked)==537 and all(hashlib.sha256((R/path).read_bytes()).hexdigest()==digest for path,digest in untracked.items())
assert all(path.startswith('docs/') or path=='.gitattributes' for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt = {'base':BASE,'requirements':140,'previous_criteria_exact':139,'proof_files_imported':58,
    'snapshot_doc_imported':True,'untracked_preserved':537,'product_imported':False,'MAIN_schema':35,
    'MAIN_directed_PASS':75,'R31_independent_server_PASS':106,'global_acceptance':False,'SEC19_closed':False,
    'initial_registry_refusal':'SEC19 lacked recorded independent PG review; state corrected to en_revision, criterion unchanged.',
    'attribute_refusal':'Only unsealed root .gitattributes mixed CRLF was normalized; all imported RAW artifacts remain byte exact.'}
(P/'receipt.json').write_bytes(encode(receipt))
(P/'commit-driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',P.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Record actual MAIN35 validation and independently repaired browser admission')
assert not git('status','--porcelain','-uno').stdout.strip()
result = {'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
