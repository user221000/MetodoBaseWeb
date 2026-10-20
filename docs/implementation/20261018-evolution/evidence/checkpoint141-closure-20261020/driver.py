"""Record actual integrated R31, rejected native evidence and isolated 36/37 work."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint141-20261020')
BASE = 'b17c08efe9c7debff3d98321b59e164ee42803e5'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda obj: (json.dumps(obj, ensure_ascii=False, indent=2)+'\n').encode()


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=R, capture_output=True, check=check)


assert git('rev-parse', 'HEAD').stdout.decode().strip() == BASE
assert not git('status', '--porcelain', '-uno').stdout.strip()
assert not O.exists()
O.mkdir()
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria = lambda obj: {row['id']: {key: row[key] for key in ('fuente', 'seccion', 'problema', 'criterio_exacto')} for row in obj['requisitos']}
old = criteria(data)
assert len(old) == 140
untracked = {path: sha((R/path).read_bytes()) for path in git('ls-files', '--others', '--exclude-standard', '-z').stdout.decode().split('\0') if path and (R/path).is_file()}
assert len(untracked) == 537
(O/'untracked-before.json').write_bytes(encode(untracked))
paths, imports = [], []
for ref, prefix in [
    ('827144aeab4e52162fcf37badf4c1e61156f9828', 'root-sec25-money36-author-20261020'),
    ('5ffc04b0d963cd3f685bdad69f2cd0f87eede8f5', 'root-notifications36-postgresql-peer-20261020'),
    ('e42a9063', 'security-notifications36-money-red-independent-20261020'),
    ('683babef', 'security-notifications36-boundaries-before-independent-20261020'),
    ('e19187ba9fa6ede9c97b623389376e683e4da5d9', 'security-notifications36-fixed-independent-20261020'),
    ('2c3d70cc8e12dfe3200ce4f9a7ecf7f7ea93eb16', 'qa-r31-native-mfa35-preparation-independent-20261020'),
    ('d8151e4eb2d78690c40340488de29ca95dc99c2a', 'qa-r31-native-mfa35-rejected-independent-20261020'),
    ('be778fecfcea65f9dd8f50a45e847177b0a01ac1', 'qa-r31-typeerror-diagnostic-independent-20261020'),
    ('ee7b1f31c72b25654fb8f91788b4da03cdf90b4b', 'ui27-registration-bearer-candidate-20261020'),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree', '-r', '--name-only', '-z', ref, '--', folder).stdout.decode().split('\0')[:-1]
    assert names, prefix
    entry = {'producer': git('rev-parse', ref).stdout.decode().strip(), 'prefix': prefix, 'files': len(names), 'hashes': {}, 'product_imported': False}
    for path in names:
        raw = git('show', ref+':'+path).stdout
        if (R/path).exists():
            assert (R/path).read_bytes() == raw, path
        else:
            (R/path).parent.mkdir(parents=True, exist_ok=True)
            (R/path).write_bytes(raw)
            paths.append(path)
        entry['hashes'][path] = sha(raw)
    imports.append(entry)

paragraph = ('MAIN integra localmente el servidor y la interfaz R31 sobre esquema35. El gate del producto integrado8144 pasa110/110 contratos HTTP en ambas factories, sin errores o skips; no representa CI completo, PostgreSQL o Chrome. Se conservan140 criterios anteriores y se registran SEC25, QA-25, QA-26 y QA-27, total144 (92 originales y52 añadidos). El navegador nativo sigue rechazado:11 grupos profesionales alcanzados,2TypeError finales y9 capturas; los4 grupos personales no se ejecutaron. Diagnóstico SQLite35 separado reproduce4TypeError de acceso a DOM invalidado, sin atribuirlos uno a uno a los2 anteriores; reparación focal en curso. QA-25 se verifica localmente: normalizar EOL sólo en memoria repara2 compilaciones; el gate integrado incluye4 puentes MFA conHTTP real. Notificaciones36 permanece aislado: autor120/120SQLite tras reparar SEC25; seguridad independiente31/31 y ROOT60/60PostgreSQL restringido, pool1 y FORCE32, dosBD cerradas normal sin sesiones y ausencia fresca. ROOT es autor del delta monetario y su replay PG no sustituye la revisión independiente de ese delta. Registro con Bearer ajeno QA-26 confirmado1RED/1control en ambas factories: API500 con una identidad persistida; SaaS200. Cuenta37 aislada pasa61 contratos iniciales y69 de compatibilidad/bordes;20HTTP repetidos tras estilo, revisión independiente en curso yPG37 pendiente. R05 global sigue RED1603 en4f4, sin nuevo escaneo. Sólo servicio web; desktop fuera del trabajo y entrega. Sin despliegue, cargos o envíos reales.')

def append_unique(row, field, value):
    if value not in row[field]:
        row[field].append(value)


for row in data['requisitos']:
    if row['id'] == 'SEC24':
        row['estado'] = row['implementacion'] = row['validacion'] = 'verificado'
        row['bloqueo'] = None
        row['revisor'] = 'Seguridad independiente106/106 y ROOT sobre MAIN integrado110/110; alcance de admisión HTTP finita, sin cierre globalR31.'
        append_unique(row, 'commits', BASE)
        append_unique(row, 'pruebas', 'Checkpoint141: MAIN8144 conserva la guardia finita; gate110/110 incluye canaria original y contadores SQL/verificador antes de admisión, ambosfactories.')
        append_unique(row, 'evidencia', 'evidence/root-main-r31-current-http-20261020/summary.json')
    if row['id'] in {'R31', 'SEC02', 'R10', 'R19', 'R32'}:
        append_unique(row, 'observaciones', 'Checkpoint141: R31 integradoMain35/8144 y110HTTPPASS; nativo d815 rechazado por2TypeError finales,4grupos personales no ejecutados. Diagnóstico be778 identifica4accesosDOM separados/QA-27; no nativoPASS ni cierre global. Nuevo cookie/RAM no autoriza recursos ni cambia actor porStorage.')
        row['evidencia'].extend(['evidence/root-main-r31-current-http-20261020/summary.json', 'evidence/qa-r31-native-mfa35-rejected-independent-20261020/phase-summary.json', 'evidence/qa-r31-typeerror-diagnostic-independent-20261020/phase-summary.json'])
    if row['id'] in {'R27', 'SEC23', 'QA-24'}:
        append_unique(row, 'observaciones', 'Checkpoint141: candidato36 aislado con fixSEC25; autor120SQLite, seguridad independiente31SQLite y ROOT60PG(replay29funcionales+31security),1253fuentes/92dists quietas,32FORCE/42physical/pool1. ROOT no es revisor independiente de su propio delta monetario. UI27 y composición37 pendientes; puertos de envío deshabilitados. No integración36 enMAIN.')
        row['evidencia'].extend(['evidence/root-notifications36-postgresql-peer-20261020/summary.json', 'evidence/security-notifications36-fixed-independent-20261020/joint-fixed-own-31-result.json'])
    if row['id'] == 'R16':
        append_unique(row, 'observaciones', 'Checkpoint141: cuenta37 freeze25ec aislado,61iniciales+69compatibilidad/bordes en fuentes separadas y20HTTP repetidos tras estilo; revisión independiente en curso, PG37/UI autenticada/integración pendientes. No correo real ni cambio de dirección implementado.')

sys.path.insert(0, str(R))
from scripts.implementation_registry import record
new = [
    ('SEC25', 'Snapshot de factura contradictorio (paid mayor que due con remaining positivo, o paidTrue/open) podía calificar como deuda y programar recordatorio en candidato36.', 'Aceptar deuda sólo con importe entero acotado y coherencia due=paid+remaining, estado y paid compatibles; contradicción o ausencia produce unknown y no nuevo envío. Aplicar la misma validación a snapshots nuevos y hechos persistidos. Preservar canaria original RED, contratos coherentes, fuentes Stripe/MP, RLS y ausencia de cargos/envío real; repetir ambosfactories y revisión independiente, sin atribuir aceptación del proveedor como entrega.', ['R27', 'R26', 'R31'], 'en_revision'),
    ('QA-25', 'Dos companions R31 asumían finales LF y fallaban al compilar fuentes RAW CRLF antes de invocar HTTP o Chrome; no eran regresión del runtime MFA.', 'Conservar los originales RAW y sus hashes; normalizar EOL exclusivamente en la copia en memoria usada por el companion. Mantener aserciones de negocio y de ciclo de sesión, informar hash RAW y de compilación por separado, repetir controles LF/CRLF y puentes MFA contra HTTP real en ambasfactories. No presentar compilación como navegador nativo.', ['R19', 'R05', 'R32'], 'verificado'),
    ('QA-26', 'Registro público legacy con Bearer válido ajeno devuelve500 en API después de persistir una identidad nueva; el mismo caso SaaS devuelve200. La cuenta manager original conserva su autoridad.', 'La ruta pública de registro debe derivar la identidad sólo del registro actual y no heredar contexto tenant de un Bearer ajeno. Completar una cuenta independiente con200 sin adopción de autoridad ajena o dejar cero identidad parcial cuando se rechace por ese contexto. Preservar la admisión browser antes de cualquier consulta, vecinos protegidos y reset finally; usar rutas y métodos finitos, sin exención global de prefijo. Repetir canaria original y controles en ambasfactories con revisión independiente.', ['R16', 'R10', 'R19'], 'en_curso'),
    ('QA-27', 'La invalidación de sesión elimina el DOM privado mientras callbacks de configuración/branding/perfil/privacidad conservan búsquedas de nodos o continúan una inicialización; diagnóstico nativo separado observa cuatro TypeError.', 'Tras invalidación local o externa, los consumidores privados deben detenerse, limpiar su RAM y tolerar la eliminación del DOM sin TypeError, lectura tardía, envío o readopción de actor. Capturar referencias propias y verificar vigencia antes de usar nodos o continuar await; cubrir las cuatro ubicaciones observadas, personalización y pagehide. Preservar pageErrors==[] y todas las aserciones de negocio del navegador original; verificar reparación focal y después repetir navegador con fuente actual y revisión independiente.', ['R31', 'R19', 'R13'], 'en_curso'),
]
for ident, problem, criterion, tasks, state in new:
    assert ident not in old
    row = record(ident, D/'NUEVOS_HALLAZGOS.md', 'Checkpoint141 '+ident, problem, criterion, 'P2')
    row['tareas'] = tasks
    row['responsable'] = 'Coordinación y autor focal; QA/seguridad independiente'
    row['estado'] = row['implementacion'] = row['validacion'] = state
    row['documentacion'] = ['VALIDACION.md', 'NUEVOS_HALLAZGOS.md']
    if ident == 'SEC25':
        row['commits'] = ['206a3ba55d5a29b9f5a805700d3afef647fbebb4', 'e19187ba9fa6ede9c97b623389376e683e4da5d9', '5ffc04b0d963cd3f685bdad69f2cd0f87eede8f5']
        row['evidencia'] = ['evidence/security-notifications36-money-red-independent-20261020/result-projection.json', 'evidence/security-notifications36-fixed-independent-20261020/joint-fixed-own-31-result.json', 'evidence/root-sec25-money36-author-20261020/summary.json', 'evidence/root-notifications36-postgresql-peer-20261020/summary.json']
        row['pruebas'] = ['2RED originales;8 controles monetarios antes=2PASS6RED; después31/31 propios seguridad; autor120SQLite yROOT60PG incluyen replays, no sumar como casos distintos.']
        row['revisor'] = 'Seguridad independiente e191,31/31; replayPGROOT no es revisión independiente del delta monetario deROOT.'
        row['bloqueo'] = 'Integración local36 yUI27 pendientes; no envío/proveedor real.'
    elif ident == 'QA-25':
        row['commits'] = ['c9f5d35798c1c528ccf9082c50af28354ea9ab04', BASE]
        row['pruebas'] = ['2RED decompilación→2PASS,10casos/20compilaciones LF/CRLF;4/4 puentes MFAHTTP incluidos en110/110MAIN.']
        row['evidencia'] = ['SESION_NAVEGADOR_R31_QA25_EOL.json', 'evidence/root-main-r31-current-http-20261020/summary.json']
        row['revisor'] = 'ROOT repite puentes reales sobre producto integrado y conserva diagnóstico previo de framing.'
    elif ident == 'QA-26':
        row['commits'] = ['ee7b1f31c72b25654fb8f91788b4da03cdf90b4b', 'eae23be92b5981e0b9688d2234cb373859afac78']
        row['pruebas'] = ['FE1RED/1PASS;ROOT repite la canaria literal:2casos=1FAIL/1PASS,0E/skip,19.75s,1247fuentes/92dists quietas; RAW privado, sinPG o proveedorred.']
        row['evidencia'] = ['evidence/ui27-registration-bearer-candidate-20261020/candidate.json']
        row['observaciones'] = ['Canaria RAW inmutable438b0105; reparación backend aún no integrada.']
    else:
        row['commits'] = ['d8151e4eb2d78690c40340488de29ca95dc99c2a', 'be778fecfcea65f9dd8f50a45e847177b0a01ac1']
        row['pruebas'] = ['Original11grupos/2TypeError con9capturas rechazado,4personales noejecutados; diagnóstico2escenarios/4TypeError separado conmapping SSR. No equivalencia1:1 ni productoPASS.']
        row['evidencia'] = ['evidence/qa-r31-native-mfa35-rejected-independent-20261020/phase-summary.json', 'evidence/qa-r31-typeerror-diagnostic-independent-20261020/SSR-line-mapping.json']
        row['observaciones'] = ['El diagnóstico se anunció provisionalmente como QA-26; ROOT asigna QA-27 para preservar el ID de registro ya reservado. RAW históricos no se reescriben.']
    data['requisitos'].append(row)
assert all(criteria(data)[key] == value for key, value in old.items())
assert len(data['requisitos']) == 144
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
for name, content in {'VALIDACION.md': paragraph, 'CAMBIOS.md': paragraph, 'DECISIONES.md': 'La aceptación R31 actual se limita al gate HTTP integrado; el rechazo nativo se conserva y obliga reparar QA-27 antes de repetir. QA-26 identifica registro y QA-27 invalidación DOM; sus RAW nominales anteriores permanecen intactos. Notificaciones36 y cuenta37 siguen aislados. No se amplía la exclusión tenant por prefijo ni se reduce pageErrors. Sólo web.', 'RIESGOS.md': 'Nativo actual rechazado por accesos DOM tras invalidación. Registro público API puede persistir una identidad antes de responder500 con Bearer ajeno. R05 global RED1603 y CI/broad/imagen/restore actuales pendientes; PG37 y consumo UI pendiente. Retención, países, SLO y piloto conservan decisiones externas pendientes.'}.items():
    p = D/name
    assert b'## Checkpoint141' not in p.read_bytes()
    p.write_bytes(p.read_bytes().rstrip()+('\n\n## Checkpoint141\n\n'+content+'\n').encode())
findings = D/'NUEVOS_HALLAZGOS.md'
findings.write_bytes(findings.read_bytes().rstrip()+('\n\n'+''.join('## Checkpoint141 '+ident+'\n\n'+problem+'\n\nCriterio: '+criterion+'\n\n' for ident, problem, criterion, _, _ in new)).encode())
state = (D/'ESTADO.md').read_text(encoding='utf8')
history = state[state.index('## Observaciones históricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint141 local: esquema35 y144 requisitos.\n\n'+paragraph+'\n\nFree: 10 clientes activos, 1 plan por cliente al día y 10 planes totales por gimnasio al día. Copia de referencia y537 untracked preservados; sin push, PR, despliegue, cargos o envíos.\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint141\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
proof = D/'evidence/checkpoint141-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
(proof/'imports.json').write_bytes(encode(imports))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=R, capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout)
(O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
git('-c', 'core.autocrlf=false', 'add', '-f', '--', *paths, proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json', 'TRAZABILIDAD.md', 'ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md']
git('-c', 'core.autocrlf=true', 'add', '--renormalize', '--', *[(D/name).relative_to(R).as_posix() for name in controls])
check = git('diff', '--cached', '--check', check=False)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cached = {}
cr = set()
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.', line)
    if match:
        path, num = match.group(1), int(match.group(2))
        assert path in paths, path
        if path not in cached:
            cached[path] = git('show', ':'+path).stdout.split(b'\n')
        value = cached[path][num-1]
        assert value.endswith(b'\r') and not value[:-1].endswith((b' ', b'\t'))
        cr.add(path)
attrs = git('show', ':.gitattributes').stdout.replace(b'\r\n', b'\n').rstrip(b'\n')+b'\n'
for path in sorted(cr):
    entry = (path+' whitespace=cr-at-eol\n').encode()
    if entry not in attrs:
        attrs += entry
(R/'.gitattributes').write_bytes(attrs)
git('-c', 'core.autocrlf=false', 'add', '--', '.gitattributes')
git('diff', '--cached', '--check')
assert all(sha((R/path).read_bytes()) == digest for path, digest in untracked.items())
assert all(git('show', ':'+path).stdout == (R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') or path == '.gitattributes' for path in git('diff', '--cached', '--name-only').stdout.decode().splitlines())
receipt = {'base': BASE, 'requirements': 144, 'previous_criteria_exact': 140, 'new_ids': [item[0] for item in new], 'proof_files_imported': len(paths), 'untracked_preserved': 537, 'product_imported': False, 'MAIN_schema': 35, 'R31_product_integrated': True, 'MAIN_HTTP': {'passed':110, 'failed':0}, 'native_browser_accepted': False, 'global_acceptance': False, 'CRLF_paths_preserved': sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c', 'core.autocrlf=false', 'add', '-f', '--', proof.relative_to(R).as_posix())
git('diff', '--cached', '--check')
git('commit', '-m', 'Record integrated web session and preserve rejected native and isolated account notification evidence')
assert not git('status', '--porcelain', '-uno').stdout.strip()
result = {'head': git('rev-parse', 'HEAD').stdout.decode().strip(), **receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
