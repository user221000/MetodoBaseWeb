"""Reconcile integrated web36, source-bound native acceptance and new QA-28."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint143-20261020')
BASE = '6b1e1590c13849c72245915c1d606bd22798a1d1'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda obj: (json.dumps(obj, ensure_ascii=False, indent=2)+'\n').encode()
git = lambda *args: subprocess.check_output(['git', *args], cwd=R)
assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert not git('status', '--porcelain', '-uno').strip() and not O.exists()
O.mkdir()
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria = lambda value: {row['id']: {key: row[key] for key in ['fuente', 'seccion', 'problema', 'criterio_exacto']} for row in value['requisitos']}
old = criteria(data)
assert len(old) == 144
untracked = {name: sha((R/name).read_bytes()) for name in git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0') if name and (R/name).is_file()}
assert len(untracked) == 537
(O/'untracked-before.json').write_bytes(encode(untracked))
paths, imports = [], []
for ref, prefix in [
    ('a10bd7ba34412a8d85c0e699bb6fff07fde2e7f0', 'qa-r31-native-mfa35-dom-independent-20261020'),
    ('019e985b', 'security-r05-finite-v3-independent-20261020'),
    ('d94fd991af752276f3319d695b5b9a14a39968b0', 'ops-ci37-preparation-20261020'),
    ('ffee085f5e6fa5205d13c0ebd606cf72d9d3a5fb', 'security-account37-ui401-red-independent-20261020'),
    ('08de03f3ecbbc8d8a10bac193f12efadf92312ad', 'security-account37-ui401-aliases-independent-20261020'),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree', '-r', '--name-only', '-z', ref, '--', folder).decode().split('\0')[:-1]
    assert names, prefix
    entry = {'producer': git('rev-parse', ref).decode().strip(), 'prefix': prefix, 'files': len(names), 'hashes': {}, 'product_imported': False}
    for name in names:
        raw = git('show', ref+':'+name)
        assert not (R/name).exists(), name
        (R/name).parent.mkdir(parents=True, exist_ok=True)
        (R/name).write_bytes(raw)
        paths.append(name); entry['hashes'][name] = sha(raw)
    imports.append(entry)
assert not git('diff', '--name-only', '2709d4f54ad779173c90520bcf6e6c627bce4fd2', '474af762b40c3c3321664ce667e7bb1805a3013f', '--', 'web', 'api', 'core', 'config', 'src').strip()
for name in ['web/static/js/gym-branding.js', 'web/static/js/usuario-privacidad.js', 'web/templates/configuracion.html', 'web/templates/usuario_perfil.html']:
    assert git('show', BASE+':'+name) == git('show', 'c822c06d:'+name)
paragraph = ('La rama principal local integra notificaciones36 y su UI27, la coherencia monetaria SEC25 y el aislamiento de tenant en rutas primarias QA-26. Los30 archivos de producto del merge a387 coinciden con la composicion revisada ab1b. El gate actual pasa78/78 casos HTTP reales sobre ambas factories API y SaaS; fuentes1268, Python,92 versiones instaladas y Node permanecen estables. La preparacion inicial selecciono un archivo inexistente: cero casos y exit4; su booleano de intencion no constituye ejecucion HTTP. Se conserva ese RAW separado.\n\n'
    'QA repitio los15 grupos originales de navegador MFA sobre PostgreSQL35 y runtime exacto a MAIN2709:11 profesionales y4 personales, pageErrors=[],12 capturas y cero violaciones axe en el alcance comprobado. Una UUID cerro normalmente y los21 procesos propios cerraron con identidad comprobada; el pool nativo era5/0, sin atribucion pool1. La reparacion DOM QA-27 queda verificada localmente en esa fuente. El intento anterior rechazado y su diagnostico permanecen intactos. Los cambios posteriores36 tienen el gate HTTP separado; no se afirma navegador nativo36 o37. La superposicion movil del boton de menu sigue en UX-09/R13.\n\n'
    'Cuenta37 sigue aislada. Seguridad confirma QA-28: tras un401 real de recurso, la UI conserva acceso en RAM o proyecciones de la cuenta. Se preservan seis HTTP RED y doce canarias VM RED, incluidos aliases de identidad/MFA. ROOT reprodujo los mismos fallos y prepara un cambio acotado al namespace de cuenta, con fence del actor capturado y sin refresh/retry; reautenticacion primaria incorrecta no implica retirar sesion. La revision independiente de esa correccion, PG peer, restore37, CI y navegador37 siguen en curso.\n\n'
    'R05v3 ya esta integrado con125 casos actuales y146 de revision independiente. El nuevo escaneo real del arbol405 es RED:53203 alertas,42187 clasificadas por ubicaciones finitas y11016 pendientes en236 archivos. El resultado historico RED1603 se conserva; no representa el resultado actual. Seguridad preparo una propuesta de11015 puntos y dejo uno sin preimagen historica; ninguna ampliacion v4 esta aceptada o integrada. CI37 tiene solo preparacion estructural4353 NodeIDs,43 modulos480 casos afectados y30 controles; no CI global verde.\n\n'
    'Se conservan los144 criterios anteriores y los92 originales; se agrega QA-28, total145. Los537 archivos untracked permanecen intactos. Free mantiene10 clientes,1 plan por cliente al dia y10 planes totales al dia por gimnasio, mensual20 sin cambio. El trabajo actual es exclusivamente del servicio web. Sin push, PR, despliegue, cobros o envios reales.')
for row in data['requisitos']:
    ident = row['id']
    if ident in {'SEC25', 'QA-26', 'QA-27'}:
        row['estado'] = row['implementacion'] = row['validacion'] = 'verificado'
        row['bloqueo'] = None
        row['observaciones'].append('Checkpoint143: verificado localmente en fuente y alcance expresos; no despliegue ni aceptacion global del requisito padre.')
        if ident == 'QA-27':
            row['commits'].append('a10bd7ba34412a8d85c0e699bb6fff07fde2e7f0')
            row['pruebas'].append('Nuevo gate original15:11profesional+4personal PASS enPG35/runtime exactoMAIN2709; pageErrors[],12capturas,12scopedaxe0/overflow0;21procesos propios cerrados y1UUIDDROPnormal/ausenciafresca. Pool5/0,no36/37nativeclaim; intento anterior rechazado intacto.')
            row['evidencia'].append('evidence/qa-r31-native-mfa35-dom-independent-20261020/review.json')
            row['revisor'] = 'QA independiente a10:15 grupos nativos originales enPG35; cuatro deltasDOM siguen exactos c822 enMAIN36.'
        else:
            row['commits'].extend(['a387c7836ffc922e3d4236911955d625b086eeaf', BASE])
            row['pruebas'].append('MAIN36 actual78/78HTTPPASS incluye canarias y contratos afectados; fuentequieta1268/92dists/Node. Revision independiente y PostgreSQL previos siguen vinculados a sus fuentes exactas, no ejecucion nueva.')
            row['evidencia'].append('evidence/root-main36-current-20261020/summary.json')
    if ident in {'R27', 'R26', 'R31', 'R16', 'B19', 'UX-15'}:
        row['observaciones'].append('Checkpoint143: MAIN36/UI27 integrado78HTTPPASS; cuenta37aislada yQA-28confirmado401local, correccion/peer/restore/CI/nativo37pendientes. No entregabilidad real de notificaciones ni aceptacion completa del requisito padre.')
        row['evidencia'].append('evidence/root-main36-current-20261020/summary.json')
    if ident in {'R05', 'QA-01', 'QA-07', 'OPS07'}:
        row['observaciones'].append('Checkpoint143: R05v3integrado405;125actuales/146peerPASS pero escaneo actual405RED11016(53203raw/42187finite),236archivos. Propuesta11015+1sinpreimagen noaceptada; noR05globalPASS. CI37preparacion4353NodeIDs/43modules480cases/30controls, nobroadCI37aun.')
        row['evidencia'].extend(['evidence/root-main-r05-v3-current-20261020/summary.json', 'evidence/security-r05-finite-v3-independent-20261020/result-projection.json', 'evidence/ops-ci37-preparation-20261020/preparation.json'])
    if ident in {'R13', 'UX-09', 'R19'}:
        row['observaciones'].append('Checkpoint143: nativo original15 pasa en fuente35 exacta2709 sin erroresDOM; observacion movil menu/heading permaneceUX-09/R13, no eliminada por ese gate. Navegador37pendiente.')
qa28 = {'id': 'QA-28', 'identificador_original': 'QA-28', 'fuente': 'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md', 'seccion': 'Checkpoint143 QA-28',
    'problema': 'Un401 de recurso en seguridad de cuenta37 conserva la credencial RAM y/o proyecciones del actor anterior; incluye status, requestEmail, changePassword y aliases context/factorStatus/verify.',
    'criterio_exacto': 'Un401 de recurso debe retirar la autoridad local capturada y limpiar sus proyecciones, sin refresh, replay automatico, adopcion de actor ni afirmacion de revocacion global. Una respuesta tardia de A nunca retira B ni sobrescribe un epoch externo. Preservar403/422 corregibles y401 de reautenticacion primaria incorrecta, captura del cuerpo antes de await, WebLock hasta respuesta y frontera local antes de liberarlo cuando corresponda. Repetir seis HTTP reales originales en ambas factories, doce VM RED y bordes independientes, sin modificar primitives globales MFA/R31.',
    'prioridad': 'P2', 'responsable': 'Coordinacion autor focal; Seguridad revision independiente', 'tareas': ['R16', 'R31', 'UX-15'], 'dependencias': [],
    'estado': 'en_revision', 'implementacion': 'en_revision', 'validacion': 'en_revision', 'despliegue': 'no_desplegado', 'entorno': 'local',
    'cambios': ['Correccion aislada namespace accountSecurity; ninguna integracion37 enMAIN aun.'],
    'commits': ['ffee085f5e6fa5205d13c0ebd606cf72d9d3a5fb', '08de03f3ecbbc8d8a10bac193f12efadf92312ad', 'ff65b1e46e4c9a861491760bd2c65f11511ab2e5'],
    'pruebas': ['Seguridad6HTTPRED+12VMRED y controles; ROOT reproduce6HTTPRED/0E y12VMRED+24PASS controles, fuentes1172/92dists quietas. Correcion final y peer pendientes; bordes con delayJSON requieren companion de reloj porque401 se retira antesJSON.'],
    'evidencia': ['evidence/security-account37-ui401-red-independent-20261020/http-result.json', 'evidence/security-account37-ui401-aliases-independent-20261020/red-aliases-result.json'],
    'documentacion': ['NUEVOS_HALLAZGOS.md', 'VALIDACION.md'], 'revisor': 'Seguridad independiente: reproduccion confirmada sobre c91; correccion aun en revision.',
    'bloqueo': 'Integracion37 condicionada a replay literal y revision independiente de la correccion; no proveedor o nativo37.', 'observaciones': []}
data['requisitos'].append(qa28)
assert {key: value for key, value in criteria(data).items() if key in old} == old and len(criteria(data)) == 145
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
for name in ['VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md']:
    path = D/name
    assert b'## Checkpoint143' not in path.read_bytes()
    text = paragraph if name != 'NUEVOS_HALLAZGOS.md' else 'QA-28: '+qa28['problema']+'\n\nCriterio: '+qa28['criterio_exacto']+'\n\nSeisHTTP ydoceVM RED independientes preservados. Correccion focal yrevision en curso; no defecto de autorizacion backend demostrado.'
    path.write_bytes(path.read_bytes().rstrip()+('\n\n## Checkpoint143\n\n'+text+'\n').encode())
state = (D/'ESTADO.md').read_text(encoding='utf8')
history = state[state.index('## Observaciones historicas'):] if '## Observaciones historicas' in state else state[state.index('## Observaciones hist\u00f3ricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementacion\n\nCheckpoint143 local: esquema36 y145 requisitos.\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validacion](VALIDACION.md).\n\n'+history+'\n## Checkpoint143\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validacion](VALIDACION.md).\n').encode())
proof = D/'evidence/checkpoint143-closure-20261020'
proof.mkdir(); (proof/'.gitattributes').write_bytes(b'* -text\n')
(proof/'imports.json').write_bytes(encode(imports)); (proof/'driver.py').write_bytes(Path(__file__).read_bytes())
checked = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=R, capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout); (O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
git('-c', 'core.autocrlf=false', 'add', '-f', '--', *paths, proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json', 'TRAZABILIDAD.md', 'ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'DECISIONES.md', 'RIESGOS.md', 'NUEVOS_HALLAZGOS.md']
git('-c', 'core.autocrlf=true', 'add', '--renormalize', '--', *[(D/name).relative_to(R).as_posix() for name in controls])
check = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=R, capture_output=True)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cached, cr = {}, set()
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.', line)
    if match:
        name, number = match.group(1), int(match.group(2)); assert name in paths
        if name not in cached: cached[name] = git('show', ':'+name).split(b'\n')
        raw = cached[name][number-1]
        assert raw.endswith(b'\r') and not raw[:-1].endswith((b' ', b'\t'))
        cr.add(name)
attrs = git('show', ':.gitattributes').replace(b'\r\n', b'\n').rstrip()+b'\n'
for name in sorted(cr):
    entry = (name+' whitespace=cr-at-eol\n').encode()
    if entry not in attrs: attrs += entry
(R/'.gitattributes').write_bytes(attrs); git('-c', 'core.autocrlf=false', 'add', '--', '.gitattributes')
git('diff', '--cached', '--check')
assert all(sha((R/name).read_bytes()) == digest for name, digest in untracked.items())
assert all(git('show', ':'+name) == (R/name).read_bytes() for name in paths)
assert all(name.startswith('docs/') or name == '.gitattributes' for name in git('diff', '--cached', '--name-only').decode().splitlines())
receipt = {'base': BASE, 'requirements': 145, 'previous_criteria_exact': 144, 'proof_files_imported': sum(row['files'] for row in imports), 'untracked_preserved': 537, 'product_imported': False, 'MAIN_schema': 36, 'original_native_15_accepted_source35': True, 'current_native36_or37_accepted': False, 'fresh_R05_remaining': 11016, 'global_acceptance': False, 'CRLF_paths_preserved': sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt)); git('-c', 'core.autocrlf=false', 'add', '-f', '--', proof.relative_to(R).as_posix())
git('diff', '--cached', '--check'); git('commit', '-m', 'Reconcile integrated web36 contracts native15 source35 and confirmed account401 finding')
assert not git('status', '--porcelain', '-uno').strip()
(O/'result.json').write_bytes(encode({'head': git('rev-parse', 'HEAD').decode().strip(), **receipt}))
print(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), **receipt}))
