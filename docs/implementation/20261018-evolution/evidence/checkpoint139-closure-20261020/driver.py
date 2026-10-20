"""Record real MAIN validation and the independently repaired browser boundary."""
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
BASE = '1bb480e364073d1da85d926f675a88d4a9fe5481'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def git(*args,check=True):
    return subprocess.run(['git',*args],cwd=R,capture_output=True,check=check)


def criteria(value):
    return {row['id']:{key:row[key] for key in ('fuente','seccion','problema','criterio_exacto')} for row in value['requisitos']}


assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
O.mkdir()
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
old = criteria(data)
assert len(old)==139
untracked = {path:sha((R/path).read_bytes()) for path in git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')
             if path and (R/path).is_file()}
assert len(untracked)==537
(O/'untracked-before.json').write_bytes(encode(untracked))
paths,imports = [],[]
for ref,prefix,count in [
    ('984c9433d157886ee824458281e0878c359898e9','security-r31-browser-admission-red-independent-20261020',14),
    ('fb44f8f27474f1960f0c6052629d7788122d5646','security-r31-browser-server-independent-20261020',44),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree','-r','--name-only','-z',ref,'--',folder).stdout.decode().split('\0')[:-1]
    assert len(names)==count,(prefix,len(names))
    entry = {'producer':ref,'prefix':prefix,'files':count,'hashes':{},'product_imported':False}
    for path in names:
        assert not (R/path).exists()
        raw = git('show',ref+':'+path).stdout
        (R/path).parent.mkdir(parents=True,exist_ok=True)
        (R/path).write_bytes(raw)
        paths.append(path)
        entry['hashes'][path] = sha(raw)
    imports.append(entry)
snapshot = 'docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_SNAPSHOT.json'
assert not (R/snapshot).exists()
(R/snapshot).write_bytes(git('show','bee520a8a0c9654239dd04fa54696bd098c51faf:'+snapshot).stdout)
paths.append(snapshot)
proof = D/'evidence/checkpoint139-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
problem = ('El candidato de transporte browser rechazaba Origin inválido con403 pero, en la API, '
           'TenantMiddleware podía consultar primero un bearer auténtico. SaaS ya excluía /api/auth/. '
           'No se observó bypass de autenticación ni consumo o cambio de prueba/cookie.')
criterion = ('La admisión estricta de las operaciones finitas del transporte browser debe ocurrir antes de cualquier '
    'consulta de bearer, SQL, verificación de proveedor o efecto de autenticación, incluso si la solicitud lleva '
    'un bearer válido. Rechazar Origin, header browser, contenido, query, método o alias no admitidos con error '
    'público privado y sin modificar refresh cookie, prueba o estado de sesión. Mantener rutas finitas y el '
    'comportamiento de APIlegacy sin header, vecinos y contexto tenant/finally, sin excluir un prefijo global '
    'ni convertir cookie en autoridad general. Repetir la misma canaria independiente689a, controles de '
    'SQL/verificador cero y límites antes/después en ambas factories, con revisión independiente. No presentar '
    'esta consulta previa como auth bypass o como un contador SQL observado si la aserción anterior lo impidió.')
data['requisitos'].append({'id':'SEC24','identificador_original':'SEC24',
    'fuente':'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md','seccion':'Checkpoint139 SEC24',
    'problema':problem,'criterio_exacto':criterion,'prioridad':'P2','responsable':'Coordinación; revisión independiente de seguridad',
    'tareas':['R31','R10','R19'],'dependencias':[],'estado':'en_revision','implementacion':'en_revision','validacion':'en_revision',
    'despliegue':'no_desplegado','entorno':'local','cambios':[],'commits':['8a427c310ec9b5ff37983ac9bdff354343be1708','fb44f8f27474f1960f0c6052629d7788122d5646'],
    'pruebas':['Original52=50autorPASS+SaaSownPASS+APIownRED; antes16boundaries=10PASS6RED; final independiente106/106PASS,0E/skip.'],
    'evidencia':['evidence/security-r31-browser-admission-red-independent-20261020/source.json',
                'evidence/security-r31-browser-server-independent-20261020/source.json'],
    'documentacion':['VALIDACION.md'],'revisor':'Seguridad independiente106/106SQLite/HTTP; sinPG niChrome',
    'bloqueo':'Integración R31 en MAIN y pruebas de navegador/CI actuales pendientes.',
    'observaciones':['Guardia finita antes de _extract_tenant; sólo dispatch guard e imports nuevos, métodos y finally anteriores AST exactos. CookieA/BearerB, ACKdurable perdido, migraciónreplay yHTTPloopback probados. No cierre globalR31.']})
verified = {'QA-20','QA-21','QA-22','QA-23','SEC19','SEC20','SEC21','SEC22'}
for row in data['requisitos']:
    if row['id'] in verified:
        row['estado']=row['implementacion']=row['validacion']='verificado'
        row['evidencia'].append('evidence/root-main35-integrated-contracts-20261020/summary.json')
        row['observaciones'].append('Checkpoint139: verificación focal local del criterio, con peer y source binding del merge MAIN35 más75/75 contratos integrados. No despliegue ni cierre global de R19/R33/R31/CI.')
    if row['id'] in {'R06','R13','R19','R23','R28','R33','R34'}:
        row['observaciones'].append('Checkpoint139: MAINc4f9 con esquema35 pasa75/75 en nueve módulos dirigidos, fuente/Python/92 distribuciones quietos.108 blobs exactos a fdaa; sin errores o skips. CI/broad/Chrome/imagen/PGMAIN actual pendientes.')
        row['evidencia'].append('evidence/root-main35-integrated-contracts-20261020/summary.json')
    if row['id'] in {'R31','SEC02'}:
        row['observaciones'].append('Checkpoint139: servidor R31 candidato8a427 aceptado focalmente por SEC106/106, sinPG/Chrome; SEC24 registrado. Frontend bee520 snapshot aislado: core55/shell6/recovery6/transport42;47comandos offline ymapaCI en curso. ROOT nuevoexportcompanion7011d:108ejecuciones/49casos,17+21+32+38PASS con assertnegocio preservados yunaexpectativa persistencia reexpresada aepoch. QA independiente y nativos en preparación; no R31 enMAIN.')
    if row['id']=='R27':
        row['observaciones'].append('Checkpoint139: candidato36 aislado valida5migracionesPG+19runtimePG en fuente previa. Restore detectó deparse deCHECK36 y se ajusta sólo esa expresión/target36; desconocidos de proveedor superseden hechos anteriores deforma durable, canarios deautor pendientes de últimoPG/restore ypeer. LeasePG sigueBackend exclusivo, sin aceptación global36.')
assert len(data['requisitos'])==140 and all(criteria(data)[key]==value for key,value in old.items())
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
paragraph = ('MAIN conserva esquema35 y140 requisitos (92 originales y48 añadidos), con139 criterios anteriores '
    'exactos. Tras integrar seguimiento34 y perfil nutricional35, el árbol c4f9 pasa75/75 contratos dirigidos, '
    'sin errores o skips y con fuentes/Python/92 distribuciones estables. Los hallazgos focales QA-20/21/22/23 '
    'y SEC19/20/21/22 quedan verificados localmente con peer; esto no cierra R19, R31 o R33 completos. '
    'Servidor R31 aún aislado: SEC24 reparado y106/106 pruebas independientes pasan. Frontend bee520 y '
    'sus companions siguen aislados; la exportación actual pasa108 ejecuciones con49 casos distintos, '
    'sin afirmar navegador nativo. QA prepara revisión y E2E; frontend migra fixtures nativos. '
    'Backend mantiene leasePG exclusivo para36: restore y últimos bordes aún pendientes. R05 global '
    'sigue RED1603 en4f4, sin nuevo escaneo global. CI, broad, Chrome, imagen y despliegue actuales pendientes. '
    'Sólo servicio web; desktop fuera del trabajo y entrega por instrucción expresa.')
new_finding = '\n\n## Checkpoint139\n\n### SEC24\n\n'+problem+'\n\nCriterio: '+criterion+'\n'
for name,content in {
    'NUEVOS_HALLAZGOS.md':new_finding,
    'VALIDACION.md':'\n\n## Checkpoint139\n\n'+paragraph,
    'CAMBIOS.md':'\n\n## Checkpoint139\n\n'+paragraph,
    'DECISIONES.md':'\n\n## Checkpoint139\n\nLa verificación focal local se separa de despliegue y cierre de tareas mayores. R31 conserva APIlegacy y se prueba con cookie/RAM; los tests que exigíanJWTStorage se mantienen históricos y se mapean a criterios actuales, sin simular credenciales enStorage. No basta cambiar comandosCI: preparar fixtures nativos y verificar el navegador real. LeasePG36 exclusivoBackend; Chrome todavía no concedido aQA.',
    'RIESGOS.md':'\n\n## Checkpoint139\n\nSEC24 tenía consultaBearer previa al rechazoOrigin enAPI; reparación y106 controles independientes cierran focalmente el candidato, pendiente integración. Los nativos antiguos inyectanJWTStorage y requieren nueva composición, sin etiquetarlosPASS. Restore36 reveló deriva deCHECK antes/despuésdump y no se acepta todavía. Retención, países, SLO acordado, piloto y revisión profesional requieren evidencia o participación externa.'
}.items():
    p = D/name
    assert b'## Checkpoint139' not in p.read_bytes()
    p.write_bytes(p.read_bytes().rstrip()+content.rstrip().encode()+b'\n')
state = (D/'ESTADO.md').read_text(encoding='utf-8')
history = state[state.index('## Observaciones históricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint139 local: esquema35 y140 requisitos (92 originales y48 añadidos).\n\n'+paragraph+
    '\n\nFree:10 clientes activos,1 plan por cliente al día y10 planes totales por gimnasio al día. '
    'La copia de referencia y537 archivos untracked previos se preservan; sin push, PR, despliegue, cargos o envíos.\n\n'
    '[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint139\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
(proof/'imports.json').write_bytes(encode(imports))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
checked = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(O/'registry.stdout').write_bytes(checked.stdout)
git('-c','core.autocrlf=false','add','-f','--',*paths,proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','NUEVOS_HALLAZGOS.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
whitespace = git('diff','--cached','--check',check=False)
(O/'whitespace-before.stdout').write_bytes(whitespace.stdout)
cr = set()
if whitespace.returncode:
    assert whitespace.returncode==2
    cache = {}
    for line in whitespace.stdout.decode().splitlines():
        match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
        if not match:
            continue
        path,num = match.group(1),int(match.group(2))
        assert path in paths
        if path not in cache:
            cache[path] = git('show',':'+path).stdout
        value = cache[path].split(b'\n')[num-1]
        assert value.endswith(b'\r') and not value[:-1].endswith((b' ',b'\t'))
        cr.add(path)
    attrs = R/'.gitattributes'
    attrs.write_bytes(attrs.read_bytes().rstrip()+b'\n'+''.join(path+' whitespace=cr-at-eol\n' for path in sorted(cr)).encode())
    git('-c','core.autocrlf=false','add','--','.gitattributes')
git('diff','--cached','--check')
assert all(sha((R/path).read_bytes())==digest for path,digest in untracked.items())
assert all(git('show',':'+path).stdout==(R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') or path=='.gitattributes' for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt = {'base':BASE,'requirements':140,'previous_criteria_exact':139,'proof_files_imported':58,'snapshot_doc_imported':True,
    'untracked_preserved':537,'product_imported':False,'MAIN_schema':35,'MAIN_directed_PASS':75,
    'R31_independent_server_PASS':106,'global_acceptance':False,'CRLF_paths_preserved':sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Record actual MAIN35 validation and independently repaired browser admission')
assert not git('status','--porcelain','-uno').stdout.strip()
result = {'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
