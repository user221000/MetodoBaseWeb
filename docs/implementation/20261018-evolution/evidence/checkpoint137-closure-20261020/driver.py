"""Web-only continuity with immutable criteria and separately scoped reviews."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
T = Path('C:/Users/Consu/AppData/Local/Temp')
O = T/'metodobase-checkpoint137-20261020'
BASE = 'bdc6881901e17db547e2f83f4dc9f2dd23a7c957'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def git(*args,check=True):
    return subprocess.run(['git',*args],cwd=R,capture_output=True,check=check)


def immutable(data):
    return {row['id']:{key:row[key] for key in ('fuente','seccion','problema','criterio_exacto')} for row in data['requisitos']}


assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
O.mkdir(exist_ok=False)
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
original = immutable(data)
assert len(original)==136
preserved = {path:sha((R/path).read_bytes()) for path in git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')
             if path and (R/path).is_file()}
(O/'untracked-before.json').write_bytes(encode(preserved))
paths = []
imports = []
for ref,prefix,count in [
    ('fe020d6b3928a8e0d0e0b40cbd2b987a7b5dc26d','security-nutrition35-private-headers-red-independent-20261020',23),
    ('dae93f9447e8071334066945c1c3b0fce7088b6d','security-nutrition35-api-privacy-author-20261020',73),
    ('a21e0034e057accde7fb8508f8d11269c9284344','security-qa23-handoff-independent-20261020',22),
    ('fdaa73ce65dfd89306cb0ae776a91876bea9fd49','root-nutrition35-pg-and-web-peer-20261020',6),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree','-r','--name-only','-z',ref,'--',folder).stdout.decode().split('\0')[:-1]
    assert len(names)==count
    item = {'producer':ref,'prefix':prefix,'files':count,'product_imported':False,'hashes':{}}
    for path in names:
        raw = git('show',ref+':'+path).stdout
        target = R/path
        assert not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        item['hashes'][path] = sha(raw)
        paths.append(path)
    imports.append(item)
wire = 'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_WIRE.json'
assert not (R/wire).exists()
(R/wire).write_bytes(git('show','b297df83e855197fd20e6c5b650136d5b19f3f6c:'+wire).stdout)
paths.append(wire)
proof = D/'evidence/checkpoint137-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
new = [
    ('SEC22',['R31','R06','R19'],'Seguridad de aplicación y privacidad',
     'Una excepción inesperada al leer el perfil autenticado devuelve500 genérico sin Cache-Control en ambas factories. Fronteras de405, slash y422 también necesitan la política privada finita.',
     'Conservar un500 opaco ante fallos inesperados de perfil o generación, con no-store/no-referrer y sin texto de excepción, declaración, traceback o valores privados en respuesta o logs. Aplicar cabeceras privadas también en405,422 y alias de una barra de las rutas reales de clientes, perfil personal y generación, manteniendo códigos, contrato de lectura/paginación, CSP existente y vecinos fuera del matcher. Repetir las dos canarias independientes originales y controles de logs y límites; otro agente debe revisar el parche. No afirmar filtración a terceros o bypass por la ausencia observada de cabeceras.',
     'evidence/security-nutrition35-private-headers-red-independent-20261020/source.json',
     'Autor d474 conserva500/headers y sanea logs; ROOTpeer12HTTP originales y17PGprivacidadPASS en scopes separados, con seis originalesSEC21 y controles propios. MAIN sigue33; integración pendiente.'),
    ('SEC23',['R27','R31','R19'],'Backend y datos; revisión de seguridad independiente',
     'En el candidato36, cambiar Usuario.email de A a B y de vuelta a A sin nuevo consentimiento permite que una capacidad antigua de exclusión vuelva a coincidir con el hash de contacto y desactive una preferencia. Reproducción SQL, sin ruta HTTP vigente de cambio de email.',
     'Un cambio real de contacto debe invalidar de forma monotónica las capacidades, el consentimiento aplicable y el handoff pendientes ligados al contacto anterior, incluso ante A→B→A. Conservar los eventos append-only y exigir nueva autorización explícita para el contacto actual; no reactivar por coincidencia de hash. Verificar la época actual bajo lock antes de exclusión o envío, y capturarla en preferencias/outbox/fuente. Impedir decremento, reset, fracción, NULL, saltos y overflow; un incremento manual conservador sólo puede invalidar. Probar incrementos automáticos y el mismo A→B→A original en SQLite y PostgreSQL restringido, con migración, aislamiento, rollback y revisión independiente. No presentar este SQL como explotación HTTP.',
     'evidence/checkpoint137-closure-20261020/backend-observation.json',
     'Autor informa2RED→2PASS con0→1→2 automático, más17/17SQLite de exclusión/época/migraciones; canariaac49732d recuperada por inversa completa SHAigual a foto original. PG36 ypeer pendientes; columna metadata nueva36, targets22–35 intactos.'),
    ('QA-24',['R27','R16','R19'],'Backend y QA independiente',
     'El POST público de exclusión por capacidad funciona en la API pero recibe403 CSRF previo al router en SaaS; la página pública usa credentials:omit y no puede completar la operación anónima.',
     'Permitir que la exclusión pública anónima por capacidad de propósito único complete en ambas factories sin sesión o cookies, con JSON estricto, límite de frecuencia, hash/expiración/versión de capacidad y autoridad disable-only intactos. Una exención CSRF, si es necesaria, debe ser exacta para POST /api/notificaciones/excluir y su alias de una barra, configurable con default vacío; no ampliar prefixes o vecinos. GET/prefetch no muta, bearer ajeno no cambia el sujeto y capacidad vieja no afecta preferencias nuevas. Probar el mismo caso anónimo original y vecinos403, errores privados y ausencia de otros efectos, con revisión independiente.',
     'evidence/checkpoint137-closure-20261020/backend-observation.json',
     'Autor informa reparación exactaCSRF y17/17SQLite con controles de época/migración; actualizador de factory/config predeterminado acotado. No aceptación PG36, peer, entrega de correo o despliegue.'),
]
findings = '\n\n## Checkpoint137\n\n'
for ident,tasks,owner,problem,criterion,evidence,observation in new:
    assert ident not in original
    data['requisitos'].append({'id':ident,'identificador_original':ident,
        'fuente':'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md','seccion':'Checkpoint137 '+ident,
        'problema':problem,'criterio_exacto':criterion,'prioridad':'P2','responsable':owner,
        'tareas':tasks,'dependencias':[],'estado':'en_revision','implementacion':'en_revision','validacion':'en_revision',
        'despliegue':'no_desplegado','entorno':'local','cambios':[],'commits':[],
        'pruebas':[observation],'evidencia':[evidence],'documentacion':['VALIDACION.md'],
        'revisor':'ROOT peer focal; integración MAIN pendiente' if ident=='SEC22' else None,
        'bloqueo':None,'observaciones':[observation]})
    findings += '### '+ident+'\n\n'+problem+'\n\nCriterio: '+criterion+'\n\n'+observation+'\n\n'
for row in data['requisitos']:
    if row['id']=='QA-23':
        row['estado']=row['implementacion']=row['validacion']='en_revision'
        row['commits'] += ['48ba43d8551a1b7bb19aedca583e07b293e9ba67','a21e0034e057accde7fb8508f8d11269c9284344']
        row['evidencia'] += ['evidence/security-qa23-handoff-independent-20261020/review.md','evidence/root-nutrition35-pg-and-web-peer-20261020/summary.json']
        row['revisor']='SEC independiente33/33SQLite,8propios; ROOTPG8/8 tras2RED causales. Pendiente integración MAIN.'
    if row['id']=='SEC21':
        row['estado']=row['implementacion']=row['validacion']='en_revision'
        row['commits'].append('cdf103a28fe33e32cfeaac825d338d1901a5295e')
        row['evidencia'] += ['evidence/security-nutrition35-api-privacy-author-20261020/source.json','evidence/root-nutrition35-pg-and-web-peer-20261020/summary.json']
        row['revisor']='ROOT independiente repite seis originales y cinco boundary; todosPASS SQLite/PG35. Integración MAIN pendiente.'
    if row['id'] in {'R06','R19','R23','R33','QA-22','SEC19','SEC20','QA-21'}:
        row['observaciones'].append('Checkpoint137: ROOT35 aisladoPG inicial34=29P5F preservado; seedPG1/1 yQA23originales4+causales4=8/8 trasfix. SEC21/22privacidad17/17PG;12UUIDnormalescerradas/0sesiones/ausenciafresca. Fixturesactuales72/72SQLite conasercionesintactas. Revisionesfocales, no aceptación global35/MAIN/CI/Chrome/imagen.')
    if row['id'] in {'R31','SEC02'}:
        row['observaciones'].append('Checkpoint137: backendR31producto180839 ytests b297 aislados;32HTTPrealesPASS, cookieHttpOnly/accessRAM, legacyJSONintacto, MFAreal yACKincierto veraz. RevisiónSEC independiente en curso, sinPG; UI55canariosnuevos yrecovery6 deautor en curso decompatibilidadCI. DOMresiduallegacy confirmado mínimo bajoSEC02; no evidenciaChrome ni cierre deStorageMAIN. Wire60ef5966 conservaCSRFcookieindependiente.')
    if row['id']=='R27':
        row['observaciones'].append('Checkpoint137: candidato36 aún aislado; SEC23/QA-24 registrados. EpocacontactoUser metadata aditiva36, no consentimientoinferido. PGlease entregadoBackend trasROOT12DBcerradas; doscapturas propias36cerradas, cinco migraciones PG en curso. No envíos, cargos oproviderlive.')
assert len(data['requisitos'])==139
assert all(immutable(data)[key]==value for key,value in original.items())
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
paragraph = ('Sólo servicio web.139requisitos (92originales+47añadidos),136criterios anteriores exactos. '
    'MAIN continúa esquema33; candidatos34/35/R31/36 aislados. ROOT35 targetPG5bae sobre34d1:1columna+CHECK,seguridad igual. '
    'Faseinicial34=29PASS5FAIL conservada; seedPGcorregido1/1, QA23trasfix8/8PG y28/28SQLite másunit4/4. '
    'QA23peerindependiente33/33SQLite; SEC21/22ROOTpeer42+12SQLite y17PG en scopes separados, sin sumar replays. '
    'Fixturesactuales35:72/72SQLite, helpershistóricos/asercionesintactos; selección inicial errónea0casosexit4 conservada. '
    'ROOT12UUIDnormalescerradas,0sesiones/ausenciafresca; leasePG ahoraBackend36. '
    'BackendR31producto180839 ytests b297:32HTTPrealesPASS, revisiónindependiente en curso; GoogleSignedProvidercompañero conserva14criteriosprevios ycuatroactualestrasframingdocumentado. '
    'UIR31ycompatibilidadCI siguen en curso. SEC23contactoA→B→A yQA-24CSRFexclusión añadidos: autor17/17SQLite, PG36/peer pendientes. '
    'R05global sigueRED1603 en su fuente4f4; broad,Chrome,CI,imagen actuales ydespliegue pendientes. Desktop fuera del trabajo actual por decisión expresa.')
for name,content in {
    'NUEVOS_HALLAZGOS.md':findings,
    'VALIDACION.md':'\n\n## Checkpoint137\n\n'+paragraph,
    'CAMBIOS.md':'\n\n## Checkpoint137\n\nSólo evidencias ycontrol enMAIN, sin integrar producto. '+paragraph,
    'DECISIONES.md':'\n\n## Checkpoint137\n\nLa cookie refresh es autoridad sólo para renovar/cerrar, nunca recurso privado. El headerbrowser opt-in conserva APIlegacy; invalidOrigin no muta refreshcookie, CSRFcookie existente es independiente. Locks del navegador deben conservar intención capturada antes del primerawait y mantenerse duranteSetCookie/JSON. Añadidos36 decontacto yexenciónCSRF exacta requierenpeer/PG antes de aceptar. Continúa alcance sóloSaaS; no cambios desktop.',
    'RIESGOS.md':'\n\n## Checkpoint137\n\nSEC21/22 yQA23 tienen reparación ypeerfocal; no integradosMAIN. R31 requiere cierre extremo aextremo ycompatibilidadCI, sin reponerJWTStorage para obtenerPASS. SEC23ABAcontacto yQA-24optoutanónimo son candidatos36 todavía sinpeer/PG. Retención/países,SLO,piloto,proveedorcorreo yvalidaciónprofesional permanecen sin resolución externa. No aceptación global ni despliegue.'
}.items():
    p = D/name
    assert b'## Checkpoint137' not in p.read_bytes()
    p.write_bytes(p.read_bytes().rstrip()+content.rstrip().encode()+b'\n')
state = (D/'ESTADO.md').read_text(encoding='utf-8')
history = state[state.index('## Checkpoint135'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint137 local: esquema33 y139 requisitos (92 originales y47 añadidos).\n\n'+paragraph+
    '\n\nFree:10 clientes activos,1 plan por cliente al día y10 planes totales por gimnasio al día. '
    'Workspace de referencia intacto y537 archivos untracked previos preservados; sin push,PR,despliegue,cargos oenvíos.\n\n'
    '[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).\n\n## Observaciones históricas (no estado actual)\n\n'+history+
    '\n## Checkpoint137\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).\n').encode())
(proof/'imports.json').write_bytes(encode(imports))
(proof/'backend-observation.json').write_bytes(encode({'scope':'Author observation only; uncommitted isolated36 before independent PG/runtime review.',
    'canary_sha256':'ac49732d85cacbd1cc3a11dee40eb3e7fcc1e849c82a1390afa61c827782144d',
    'canary_provenance':'Recovered by complete inverse of later additions, equal to original source-before SHA; no separate RAW source file at first execution. Original RAW/XML and preimages retained by author; future seal pending.',
    'SQL_ABA':{'before':2,'red':2,'after':2,'pass':2,'HTTP_exploitation_claim':False},
    'focal_SQLite_epoch_exclusion_and_migrations':17,'pass':17,
    'PG36_capture_sha256':'9805f3524648591f5caa2c763ac521c91378b27598f83043a2ebd2fb55ed9199',
    'PG36_runtime_accepted':False,'peer_accepted':False,'live_operations':False}))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
proc = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(O/'registry.stdout').write_bytes(proc.stdout)
(O/'registry.stderr').write_bytes(proc.stderr)
git('-c','core.autocrlf=false','add','-f','--',*paths,proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','NUEVOS_HALLAZGOS.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
checked = git('diff','--cached','--check',check=False)
(O/'whitespace-before.stdout').write_bytes(checked.stdout)
cr_files = {}
if checked.returncode:
    assert checked.returncode==2
    for line in checked.stdout.decode().splitlines():
        match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
        if not match:
            continue
        path,num = match.group(1),int(match.group(2))
        assert path in paths
        raw = cr_files.setdefault(path,git('show',':'+path).stdout)
        physical = raw.split(b'\n')[num-1]
        assert physical.endswith(b'\r') and not physical[:-1].endswith((b' ',b'\t'))
    assert cr_files
    attrs = D/'evidence/.gitattributes'
    prefix = 'docs/implementation/20261018-evolution/evidence/'
    attrs.write_bytes(attrs.read_bytes().rstrip()+b'\n'+''.join(path.removeprefix(prefix)+' whitespace=cr-at-eol\n' for path in sorted(cr_files)).encode())
    git('-c','core.autocrlf=false','add','--',attrs.relative_to(R).as_posix())
git('diff','--cached','--check')
assert all(sha((R/path).read_bytes())==digest for path,digest in preserved.items())
assert all(git('show',':'+path).stdout==(R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt = {'base':BASE,'requirements':139,'immutable_previous_criteria':136,'proof_files_imported':124,
    'wire_imported':True,'preexisting_untracked_preserved':len(preserved),'CRLF_proofs_preserved':sorted(cr_files),
    'product_imported':False,'MAIN_schema':33,'web_only':True,'global_current_acceptance':False}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Preserve web-only privacy and handoff reviews and record notification boundaries')
assert not git('status','--porcelain','-uno').stdout.strip()
result = {'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
