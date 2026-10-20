"""Preserve web review evidence, all prior criteria and unresolved current failures."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
T = Path('C:/Users/Consu/AppData/Local/Temp')
O = T/'metodobase-checkpoint136-20261020'
BASE = '0ee4b220c8927aba6334c7dd0f5c445b42461ecf'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()

def git(*args,check=True):
    return subprocess.run(['git',*args],cwd=R,capture_output=True,check=check)

def immutable(data):
    return {row['id']:{key:row[key] for key in ('fuente','seccion','problema','criterio_exacto')} for row in data['requisitos']}

assert git('rev-parse','HEAD').stdout.decode().strip() == BASE
assert not git('status','--porcelain','-uno').stdout.strip()
O.mkdir(exist_ok=False)
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
original = immutable(data)
assert len(original) == 133
preserved = {path:sha((R/path).read_bytes()) for path in git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')
    if path and (R/path).is_file()}
(O/'untracked-before.json').write_bytes(encode(preserved))
imports = []
paths = []
for ref,prefix,count in [
    ('816805915ccebf4208bd8eeaeaf1d397ad967c19','nutrition-ui35-author-20261020',10),
    ('1ebfb98f205d6be25a088b9fd70c2fa2633d87ba','followup-ui34-author-20261020',10),
    ('244be35d62450a2018c8ee4859a3ffa11a32479e','root-web-qa20-author-20261020',6),
    ('d4df0ed43505eb8584e0ad5495d1328370dbc76b','qa-nutrition35-saas-independent-20261020',19),
    ('f7ef2f68f1bec82d7db941250f762a440cb22d50','qa20-partial-profile-peer-20261020',14),
    ('e60153a2e4c1274b7d1e37cb92ecec3e5e3f9ed5','qa22-corrupt-nutrition-read-author-20261020',14),
    ('f6f4c1bff58d6a25aa3c59498ebed5840fef0a11','security-followup34-pg-independent-20261019',22),
    ('bb9046fb8397b814ba0d010fe3c96f41436cc78a','security-followup34-pg-fix-author-20261019',55),
    ('f7adf67faabd13113961c7f219d507061018e69c','security-nutrition35-api-error-red-independent-20261020',14),
    ('a1a1e16065b33ddedc31695d24f7ca252b6c2b5d','ci35-current-fixtures-author-20261020',14),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree','-r','--name-only','-z',ref,'--',folder).stdout.decode().split('\0')[:-1]
    assert len(names) == count, (prefix,len(names),count)
    item = {'source':ref,'prefix':prefix,'files':count,'product_imported':False,'hashes':{}}
    for path in names:
        raw = git('show',ref+':'+path).stdout
        target = R/path
        assert not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        item['hashes'][path] = sha(raw)
        paths.append(path)
    imports.append(item)
proof = D/'evidence/checkpoint136-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
root_pg = json.loads((T/'metodobase-followup34-author-nutrition35-pg-20261020/gate-result.json').read_bytes())
assert root_pg['cases'] == 34 and root_pg['failures'] == 5 and root_pg['errors'] == root_pg['skips'] == 0
assert root_pg['source_environment_quiet'] and root_pg['all_closed_normal_fresh']
capture = json.loads((T/'metodobase-followup34-author-nutrition35-pg-20261020/capture-structure-check.json').read_bytes())
(proof/'postgres35-observation.json').write_bytes(encode({'source':root_pg['head'],'pass':29,'fail':5,'errors':0,'skip':0,
    'sources':root_pg['sources'],'packages':root_pg['packages'],'installed_python_metadata_files':root_pg['installed_files'],
    'environment_quiet':True,'owned_databases_including_capture':8,'closed_normal_fresh_zero_sessions':True,
    'capture':capture,'failures':'One SQLite-specific boolean seed reused on PostgreSQL; four generation HTTP responses500/TimeoutError with pool1 and expire_on_commit=True. Causality review pending, production factory uses False.',
    'global_acceptance':False}))
new = [
    ('QA-22','P2',['R06','R31','R19'],
     'La lectura de exclusiones alimentarias persistidas con JSON malformado devuelve500 en ambas factories porque _cliente_to_dict ejecuta json.loads antes de la validación nutricional cerrada.',
     'Validar la declaración y las exclusiones persistidas antes de serializar el perfil. Ante JSON truncado, forma incorrecta o valores inválidos, GET detalle/listado y generación deben devolver el error nutricional público422, con no-store/no-referrer y sin reflejar los hechos rechazados. No reinterpretar corrupción como lista vacía ni información desconocida, no modificar la persistencia y no reservar cuota, generar Plan u objeto. Conservar listas legítimas y su orden, DTO y permisos; repetir las mismas dos canarias independientes y los controles añadidos, con peer posterior al parche.',
     'evidence/qa-nutrition35-saas-independent-20261020/phase-summary.json',
     'QA independiente:83 mantenidos PASS;18 propios con16PASS y2RED. Autor e0ca valida antes de json.loads: mismos2 pasan y8mantenidos pasan,10ejecuciones finales. ROOT repite8enPG35 y todos pasan dentro de su fase global29/34; sello del peer pendiente.'),
    ('SEC21','P2',['R31','R06','R19'],
     'NutritionRoute sanea errores sólo cuando el body es dict con restricciones_nutricionales; POST/PUT de clientes con una lista que contiene esa declaración refleja los valores rechazados en422.',
     'Las escrituras de perfil nutricional deben rechazar cuerpos de forma inválida sin reflejar declaraciones o datos de salud en la respuesta, incluidos arrays, objetos anidados, escalares y cadenas. Seleccionar el error público acotado por la superficie de escritura autorizada y conservar validación estricta, códigos y cabeceras privadas; no aceptar arrays ni degradar validación. Mantener contratos de lectura/paginación y rutas vecinas. Repetir las seis canarias independientes originales en ambas factories, controles propios y revisión independiente del parche. No afirmar fuga a terceros o bypass por la reflexión autenticada observada.',
     'evidence/security-nutrition35-api-error-red-independent-20261020/source.json',
     'SEC independiente sobref7c:4RED+2controlesPASS,0errores/skips; canaria21b224 byte exacta, sinPG. Corrección focal en ramaSEC en curso; no integrada ni aceptada.'),
    ('QA-23','P2',['R28','R34','R19','R06'],
     'Cuatro casos HTTP de generación PostgreSQL con pool1 y expire_on_commit=True devuelven500/TimeoutError antes de la guarda worker o publicación, mientras el contrato esperaba422/409. La fábrica productiva usa expire_on_commit=False; no se atribuye allí el mismo fallo.',
     'Confirmar y resolver la retención de checkout entre la reserva durable confirmada y el worker de generación, preservando el contrato con pool1 y ambas configuraciones de expiración admitidas. La lectura del resultado de reserva no debe abrir una transacción innecesaria que bloquee al worker. Mantener atomicidad, idempotencia, cuota, tenant y clasificación veraz de commit o compensación inciertos; no aumentar el pool, poner expire=False en la prueba ni cambiar expectativas para ocultar el fallo. Repetir los mismos cuatro casos PG y controles de handoff y replay, distinguiendo explícitamente defectos del harness de cambios de producto y revisando independientemente la corrección.',
     'evidence/checkpoint136-closure-20261020/postgres35-observation.json',
     'ROOT fasef7c:34casos,29PASS5FAIL0E/skip. Un fallo adicional de seed booleano es harness y se conserva separado. Causa probable lectura ORM expirada tras commit; confirmación con telemetría propia y corrección pendientes.'),
]
text = '\n\n## Checkpoint136\n\n'
for ident,priority,tasks,problem,criterion,evidence,observation in new:
    assert ident not in original
    data['requisitos'].append({'id':ident,'identificador_original':ident,
        'fuente':'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md','seccion':'Checkpoint136 '+ident,
        'problema':problem,'criterio_exacto':criterion,'prioridad':priority,'responsable':'Coordinación y arquitectura',
        'tareas':tasks,'dependencias':[],'estado':'en_revision' if ident=='QA-22' else 'en_curso',
        'implementacion':'en_revision' if ident=='QA-22' else 'en_curso','validacion':'en_revision' if ident=='QA-22' else 'en_curso',
        'despliegue':'no_desplegado','entorno':'local','cambios':[],'commits':[],'pruebas':[observation],
        'evidencia':[evidence],'documentacion':['VALIDACION.md'],'revisor':None,'bloqueo':None,'observaciones':[observation]})
    text += '### '+ident+'\n\n'+problem+'\n\nCriterio: '+criterion+'\n\n'+observation+'\n\n'
for row in data['requisitos']:
    if row['id']=='QA-20':
        row['estado']=row['implementacion']=row['validacion']='en_revision'
        row['commits'] += ['dfabec48547c8a26bffcc599a2f9c2ef153832b1','f7ef2f68f1bec82d7db941250f762a440cb22d50']
        row['evidencia'] += ['evidence/qa20-partial-profile-peer-20261020/phase-summary.json','evidence/root-web-qa20-author-20261020/review.md']
        row['revisor']='QA independiente:22mantenidos+2propiosPASS, tres blobs dfab exactos; pendiente integración MAIN'
    if row['id'] in {'SEC19','SEC20','QA-21','R23'}:
        row['observaciones'].append('Checkpoint136: autor7be tiene38PGfuncionales+5migraciones+1restore+86SQLitePASS; finala4f95 estrecha managerhint con5SQLite2controles/3RED→5PASS. ROOTpeerf7c conserva4originales PG y8QA22 PASS dentro de global29/34; no aceptación global35 y sello pendiente.')
    if row['id'] in {'R06','R33','R31','R19'}:
        row['observaciones'].append('Checkpoint136: UI35autor59VM/DOM+13SSR/HTTP+337regresionesPASS, sinChrome; QA83PASS yQA22/SEC21 añadidos. PG35realcapturado, sólo1col+1check frente34d1,28FORCE/38físicas. ROOT34casosPG=29PASS5FAIL,fuente92dists/4540archivosinstaladosquieta/8UUIDcerradas. No cierre global ni MAIN35.')
    if row['id']=='R27':
        row['estado']=row['implementacion']='en_curso'
        row['observaciones'].append('Checkpoint136: contrato local36 aprobado para preferencias, outbox, intentos y hechos de cobro verificados, cuatro tablas. AutorSQLite/HTTP aislado en curso; ningún envío, cargo, providerlive oPG36. Distinguir accepted de entrega y uncertain sin retry.')
    if row['id']=='R31':
        row['observaciones'].append('Checkpoint136: nueva rama de sesión web en curso: accessRAM/refreshHttpOnly, CSRF y serialización entrepestañas; Storagelegacy aún enMAIN y no se afirma corregido. Sin nuevaDDL para ese transporte.')
    if row['id']=='R16':
        row['observaciones'].append('Checkpoint136: inspección actual confirma que no hay endpoint/campo de verificación de email. Registro hoy emite par; el nuevo transporteR31 no simula verification_required. Flujo de verificación/gestión de cuenta sigue pendiente dentro deR16.')
assert len(data['requisitos']) == 136
assert all(immutable(data)[key] == value for key,value in original.items())
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
paragraph = ('Sólo servicio web. Se conservan133criterios previos yse añadenQA-22,SEC21,QA-23. '
    'QA-20 tienepeer24PASS; UI34/35 están congeladas con pruebas deautor sinChrome. '
    'SEC20/QA-21 reparados en rama aislada; finalhint1afa validado5SQLite yROOTpeer4PGPASS. '
    'PG35target5bae capturado contra34d1:únicocolumnacheck yseguridad exacta; faseROOTf7c34casos=29PASS5FAIL,0errores/skips, '
    '1109fuentes/92dists/4540Python-METADATA quietos,pip0/0,8UUID normalescerradas y ausencia fresca. '
    'Los fallos son seedbooleanoPG ycuatrohandsoffTimeoutError con expiraciónORM de la fixture; no atribuir el fallo al runtimeFalse sin reproducir. '
    'QA-22fixe0ca tieneautor10PASS y8replaysPGROOT; SEC21 sigue4RED/2controles yreparación pendiente. '
    'La nueva composición explícita defixtures35 conserva54NodeIDs y54PASS, sin tocar loshelpershistóricos; UIyhintconsumidores adicionales pendientes. '
    'R27 inicia36aislado;R31sesiónbrowser en implementación;R16emailverify siguependiente. MAIN todavía33,R05globalRED1603;no despliegue ni desktop.')
for name,content in {'NUEVOS_HALLAZGOS.md':text,'VALIDACION.md':'\n\n## Checkpoint136\n\n'+paragraph,
    'CAMBIOS.md':'\n\n## Checkpoint136\n\nSólo importación de evidencias/control, sin producto34/35/36. '+paragraph,
    'DECISIONES.md':'\n\n## Checkpoint136\n\nMantener verificaciones antiguas en su fuente auténtica yusar composición35 explícita sin cambiar aserciones oNodeIDs. Preservar errores deharness yRAW, no ampliar pool ni cambiar expiración para ocultar la retención. El target34d1 sustituyea33 sólo porNOWAIT del trigger; a33 y22–33 permanecen históricos exactos. No verificación de email simulada enR31.',
    'RIESGOS.md':'\n\n## Checkpoint136\n\nSEC21 refleja declaración rechazada en422 para bodylista; requiere erroracotado porruta antes de integrar35. QA-23 investiga retenciónpool con ORMexpirable; no se declara impacto enFalse. QA-22ya tieneparche,peerPGfocal pendiente desello. Responsables seguridad/coordinación. Riesgos legales/retención/proveedor/piloto permanecen externos; transporteStorage no resuelto aún.'}.items():
    path = D/name
    assert b'## Checkpoint136' not in path.read_bytes()
    path.write_bytes(path.read_bytes().rstrip()+content.rstrip().encode()+b'\n')
state = (D/'ESTADO.md').read_text(encoding='utf-8').replace('Checkpoint135 local: esquema33 y133 requisitos (92 originales y41 añadidos).',
    'Checkpoint136 local: esquema33 y136 requisitos (92 originales y44 añadidos).',1)
state += '\n## Checkpoint136\n\n'+paragraph+'\n'
(D/'ESTADO.md').write_bytes(state.encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\nCheckpoint136 conserva136requisitos y133criterios anteriores exactos.\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).\n').encode())
(proof/'imports.json').write_bytes(encode(imports))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
proc = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(O/'registry.stdout').write_bytes(proc.stdout)
(O/'registry.stderr').write_bytes(proc.stderr)
git('-c','core.autocrlf=false','add','-f','--',*paths,proof.relative_to(R).as_posix())
controls=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','NUEVOS_HALLAZGOS.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
checked=git('diff','--cached','--check',check=False)
(O/'whitespace-before.stdout').write_bytes(checked.stdout)
(O/'whitespace-before.stderr').write_bytes(checked.stderr)
cr_files={}
if checked.returncode:
    assert checked.returncode==2
    for line in checked.stdout.decode().splitlines():
        match=re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
        if not match:continue
        path,num=match.group(1),int(match.group(2))
        assert path in paths
        raw=cr_files.setdefault(path,git('show',':'+path).stdout)
        physical=raw.split(b'\n')[num-1]
        assert physical.endswith(b'\r') and not physical[:-1].endswith((b' ',b'\t'))
    assert cr_files
    attrs=D/'evidence/.gitattributes';prefix='docs/implementation/20261018-evolution/evidence/'
    attrs.write_bytes(attrs.read_bytes().rstrip()+b'\n'+''.join(path.removeprefix(prefix)+' whitespace=cr-at-eol\n' for path in sorted(cr_files)).encode())
    git('-c','core.autocrlf=false','add','--',attrs.relative_to(R).as_posix())
git('diff','--cached','--check')
assert all(sha((R/path).read_bytes())==digest for path,digest in preserved.items())
assert all(git('show',':'+path).stdout==(R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt={'base':BASE,'requirements':136,'immutable_previous_criteria':133,'proof_files_imported':len(paths),
    'preexisting_untracked_preserved':len(preserved),'CRLF_immutable_proofs_preserved':sorted(cr_files),
    'product_imported':False,'MAIN_schema':33,'web_only':True,'global35_acceptance':False}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Preserve independent web reviews and record current nutrition35 failures')
assert not git('status','--porcelain','-uno').stdout.strip()
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
