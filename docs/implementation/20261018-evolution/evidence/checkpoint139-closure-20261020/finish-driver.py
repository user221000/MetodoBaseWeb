"""Complete the checkpoint after validating the actual independent review scope."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
T = Path('C:/Users/Consu/AppData/Local/Temp')
O = T/'metodobase-checkpoint139-20261020'
P = D/'evidence/checkpoint139-closure-20261020'
BASE = '1bb480e364073d1da85d926f675a88d4a9fe5481'
encode = lambda value: (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def git(*args,check=True):
    return subprocess.run(['git',*args],cwd=R,capture_output=True,check=check)


assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
for row in data['requisitos']:
    if row['id']=='SEC19':
        row['estado']=row['implementacion']=row['validacion']='en_revision'
        row['revisor']='ROOT repite la proyección original en72/72SQLite; revisión independiente de PostgreSQL restringido aún pendiente.'
        row['bloqueo']='Completar la misma canaria de proyección/ORM en PostgreSQL restringido por otro agente. Lease actual exclusivoBackend36; conservar criterio abierto.'
        row['observaciones'][-1]='Checkpoint139: proyección con revisiónSQLite focal, sin cierre del criterio hasta PostgreSQL restringido independiente. El registro rechazó correctamente el cierre sin revisor; se corrigió el estado, sin cambiar criterios.'
    elif row['id'] in {'SEC20','QA-21'}:
        row['revisor']='ROOT independiente: cuatro originales cf32 enPG35 restringido sobrehint final1afa, más72/72SQLite ysource binding del merge MAIN35. Sin despliegue.'
        row['bloqueo']=None
    elif row['id']=='QA-22':
        row['revisor']='ROOT independiente: ocho canarias mantenidas de corrupción/restricciones enPG35 y75/75contratosMAIN. Autor conserva las mismas dos originales antes/después y su inversa completa.'
        row['bloqueo']=None
    elif row['id'] in {'QA-20','QA-23','SEC21','SEC22'}:
        row['revisor']=row['revisor'].replace('pendiente integración MAIN','integrado MAIN35 c4f9;75/75contratosPASS').replace('Pendiente integración MAIN.','Integrado MAIN35 c4f9;75/75contratosPASS.').replace('Integración MAIN pendiente.','Integrado MAIN35 c4f9;75/75contratosPASS.').replace('integración MAIN pendiente','integrado MAIN35 c4f9;75/75contratosPASS')
        row['bloqueo']=None
prior = json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json').stdout)
criteria = lambda value:{row['id']:{key:row[key] for key in ('fuente','seccion','problema','criterio_exacto')} for row in value['requisitos']}
assert len(data['requisitos'])==140
assert all(criteria(data)[key]==value for key,value in criteria(prior).items())
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
old = 'y SEC19/20/21/22 quedan verificados localmente con peer;'
new = ('y SEC20/21/22 quedan verificados localmente con peer; SEC19 conserva pendiente la revisión '
       'independiente de PostgreSQL;')
for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md']:
    path = D/name
    text = path.read_text(encoding='utf-8')
    assert old in text,name
    path.write_bytes(text.replace(old,new).encode())
result = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True)
(O/'registry-final.stdout').write_bytes(result.stdout)
(O/'registry-final.stderr').write_bytes(result.stderr)
assert result.returncode==0
imports = json.loads((P/'imports.json').read_bytes())
paths = [path for item in imports for path in item['hashes']]
snapshot = 'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_SNAPSHOT.json'
paths.append(snapshot)
assert len(paths)==59
(P/'finish-driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',*paths,P.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','NUEVOS_HALLAZGOS.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
check = git('diff','--cached','--check',check=False)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cr = set()
cache = {}
if check.returncode:
    assert check.returncode==2
    for line in check.stdout.decode().splitlines():
        match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
        if not match:
            continue
        path,num = match.group(1),int(match.group(2))
        assert path in paths
        if path not in cache:
            cache[path]=git('show',':'+path).stdout
        value=cache[path].split(b'\n')[num-1]
        assert value.endswith(b'\r') and not value[:-1].endswith((b' ',b'\t'))
        cr.add(path)
    attrs = R/'.gitattributes'
    raw = attrs.read_bytes().rstrip()+b'\n'
    for path in sorted(cr):
        entry=(path+' whitespace=cr-at-eol\n').encode()
        if entry not in raw:
            raw+=entry
    attrs.write_bytes(raw)
    git('-c','core.autocrlf=false','add','--','.gitattributes')
git('diff','--cached','--check')
untracked = json.loads((O/'untracked-before.json').read_bytes())
assert len(untracked)==537 and all(sha((R/path).read_bytes())==digest for path,digest in untracked.items())
assert all(git('show',':'+path).stdout==(R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') or path=='.gitattributes' for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt = {'base':BASE,'requirements':140,'previous_criteria_exact':139,'proof_files_imported':58,'snapshot_doc_imported':True,
    'untracked_preserved':537,'product_imported':False,'MAIN_schema':35,'MAIN_directed_PASS':75,
    'R31_independent_server_PASS':106,'global_acceptance':False,'CRLF_paths_preserved':sorted(cr),
    'SEC19_closed':False,'initial_registry_refusal_preserved':'SEC19: cierre sin revisión/evidencia. State corrected to en_revision pending independent PG projection.'}
(P/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',P.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Record actual MAIN35 validation and independently repaired browser admission')
assert not git('status','--porcelain','-uno').stdout.strip()
result = {'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
