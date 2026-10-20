"""Record the user's web-only scope and confirmed findings without product import."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint135-20261020')
BASE = 'a61f9e1a470dff5383be9155b2ac4e15cd6cbd08'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()

def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=R, capture_output=True, check=check)

def immutable(data):
    return {row['id']: {key: row[key] for key in ('fuente','seccion','problema','criterio_exacto')} for row in data['requisitos']}

assert git('rev-parse','HEAD').stdout.decode().strip() == BASE
assert not git('status','--porcelain','-uno').stdout.strip()
O.mkdir(exist_ok=False)
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
original = immutable(data)
assert len(original) == 128
untracked = git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')[:-1]
preserved = {path: sha((R/path).read_bytes()) for path in untracked if (R/path).is_file()}
(O/'untracked-before.json').write_bytes(encode(preserved))
paths = []
imports = []
for commit, prefix, count in [
    ('f848256ceac6a8c6a7c2cc8e3a8159d8b61e0759','backend-followup34-pg-author-20261019',23),
    ('cf0b06fdcbc3b4fc540105d2877fa33bd19d1c36','desktop35-author-20261020',7),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree','-r','--name-only','-z',commit,'--',folder).stdout.decode().split('\0')[:-1]
    assert len(names) == count
    hashes = {}
    for path in names:
        raw = git('show',commit+':'+path).stdout
        target = R/path
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        paths.append(path)
        hashes[path] = sha(raw)
    imports.append({'source_commit':commit,'prefix':prefix,'files':count,'RAW_equal_Git':True,'hashes':hashes,'product_imported':False})

scope = ('Decisión expresa del usuario al reanudar: «continua con todos estos cambios pero ya no trabajes en la version desktop, '
    'trabaja unicamente en la version de el servicio web». Desde este checkpoint el trabajo y la entrega se limitan al SaaS. '
    'Se detienen desarrollo, QA, empaquetado e instalador desktop. Código y evidencias previos se conservan; no se eliminan funciones existentes '
    'ni se integra el candidato Desktop35. QA confirmó que todavía no había ejecutado pruebas ni creado ramas o artefactos de esa revisión. '
    'Las validaciones Windows del servicio web y el núcleo compartido siguen dentro del alcance. Esta decisión sustituye la instrucción anterior '
    'de continuar el desarrollo desktop; no declara resueltos sus defectos.')

findings = [
    ('SEC19','P1',['R23','R31','R04'],
     'La consulta de locks de autoridad de seguimiento carga nombre, email y password_hash de un responsable histórico que ahora pertenece a otro contexto, aunque el DTO omite su nombre.',
     'Consultar para autoridad únicamente los campos de elegibilidad necesarios bajo los locks originales; no hidratar contacto ni credenciales del responsable ajeno. Los atributos diferidos deben fallar de forma cerrada. Conservar permiso, aislamiento, orden de locks, clasificación de errores, respuestas y DTO. Repetir los mismos canarios HTTP/SQL y de carga ORM en ambas factories; validar el cambio con revisión independiente y PostgreSQL restringido. No atribuir una fuga HTTP al sobreacceso interno observado.',
     'en_revision','Backend y datos','evidence/backend-followup34-pg-author-20261019/projection-canary-results.json',
     'Dos RED reales SQLite/ORM pasan tras proyección de ocho campos; seis aserciones conservadas. Fuente producto81f190/service13a9. Peer PostgreSQL pendiente. El nombre informal Sec18projection de comunicaciones previas corresponde a SEC19; SEC18 existente conserva su identidad.'),
    ('SEC20','P2',['R23','R04','R31'],
     'Con NutriB no asignado, bloquear sólo UsuarioC responsable de una tarea ajena cambia la respuesta a409 mientras un ID inexistente conserva404; el hint incorpora C al lockset antes del filtro de asignación.',
     'En ambas factories, una tarea fuera de la asignación autorizada debe conservar la misma denegación opaca que un ID inexistente, incluso al mantener bloqueada únicamente la cuenta del responsable ajeno. Aplicar el predicado de asignación antes de incorporar identidades sensibles al hint o lockset, revalidando autoridad y estados persistidos sin ampliar permisos. Mantener CAS, locks necesarios, historial e idempotencia y repetir las cuatro canarias originales junto con QA-21 en PostgreSQL con rol restringido. No inferir exposición de DTO o modificación autorizada por este oracle de contención.',
     'en_curso','Seguridad y privacidad','evidence/checkpoint135-closure-20261020/confirmed-web-findings.json',
     'Revisión independiente sobre f848/producto81f190: dos RED por oracle, auth y MFA reales. No hay parche integrado ni aceptación global.'),
    ('QA-19','P2',['R21'],
     'El diálogo Qt de edición llama a GestorBDClientes.actualizar_cliente, método inexistente en la preimagen55a3, por lo que no confirma ni guarda la edición.',
     'La edición real del diálogo Qt debe persistir los cambios de perfil mediante un método existente y aceptar sólo el guardado confirmado, sin incrementar el contador de planes. La misma canaria con diálogo y gestor de la preimagen exacta debe fallar antes y pasar después de la corrección. Conservar formulario y datos ante un fallo de escritura.',
     'pendiente','Coordinación y arquitectura','evidence/desktop35-author-20261020/summary.json',
     'Hallazgo confirmado antes del recorte de alcance. Candidato0d20 aislado y evidencia cf0b conservados; no se integra ni continúa su revisión. Resolución de alcance no_aplicable a la entrega SaaS por decisión expresa del usuario, sin afirmar cierre técnico.'),
    ('QA-20','P2',['R06','R15','R19'],
     'PUT /api/clientes/{id_cliente} con sólo peso sobre un perfil inicialmente vacío devuelve400 client_update_failed en api.app por AttributeError.lower de objetivoNULL, mientras web.main_web guarda200.',
     'El contrato de perfil progresivo debe aceptar una actualización parcial válida en ambas factories sin exigir, rellenar o calcular con datos no declarados. Persistir únicamente los campos enviados y conservar la declaración nutricional y los campos omitidos. Rechazar entradas inválidas sin aplicar parcialmente los otros campos. Conservar pertenencia, permisos, cabeceras privadas y validación completa antes de generar; repetir las mismas canarias antes/después y obtener revisión independiente.',
     'en_curso','Coordinación y arquitectura','evidence/checkpoint135-closure-20261020/confirmed-web-findings.json',
     'Frontend confirmó1RED api/1controlSaaS en55a3. ROOT reprodujo en54e511 dos RED y seis controles con el framing de declaración desconocida corregido explícitamente. Reparación aislada en curso, sin integración MAIN.'),
    ('QA-21','P2',['R23','R17','R19'],
     'El SELECT FOR SHARE del cliente y el trigger34 esperan ante FOR UPDATE externo; la canaria PostgreSQL acaba503 tras statement_timeout700ms en lugar del409 inmediato de contención conocido.',
     'Usar adquisición NOWAIT de los locks compartidos del cliente tanto en servicio como en el guard PostgreSQL, conservando el orden y las invariantes de causa/cliente. Con la misma fila retenida por otra conexión propia, ambas factories deben devolver409 followup_busy dentro del umbral original, sin esperar al statement_timeout, sin ACK ni Task/Event parcial y sin retry automático. SQLSTATE57014 y los fallos desconocidos siguen503. Preservar targets22–33, conservar el target34 anterior y recapturar únicamente la firma34 afectada si cambia el trigger. Repetir los mismos cuatro canarios originales compartidos con SEC20 y las regresiones afectadas.',
     'en_curso','Seguridad y privacidad','evidence/checkpoint135-closure-20261020/confirmed-web-findings.json',
     'Dos RED reales PG sobre81f190; app4flagsfalse/noowner/FORCE28/pool1. Primera UUID propia cerrada por DROP normal,0sesiones y ausencia fresca. Parche y nuevo target34 pendientes, target35 todavía no capturado.'),
]
notes = '\n\n## Checkpoint135\n\n'+scope+'\n'
for ident, priority, tasks, problem, criterion, state, owner, evidence, observation in findings:
    assert ident not in original
    row = {'id':ident,'identificador_original':ident,'fuente':'docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md',
        'seccion':'Checkpoint135 '+ident,'problema':problem,'criterio_exacto':criterion,'prioridad':priority,
        'responsable':owner,'tareas':tasks,'dependencias':[],'estado':state,'implementacion':state,
        'validacion':'pendiente','despliegue':'no_desplegado','entorno':'local','cambios':[], 'commits':[],
        'pruebas':[observation],'evidencia':[evidence],'documentacion':['DECISIONES.md'],'revisor':None,
        'bloqueo':None,'observaciones':[observation]}
    if ident == 'QA-19':
        row['resolucion_alcance'] = 'no_aplicable_a_entrega_SaaS_por_decision_expresa_usuario'
        row['decision_alcance'] = 'DECISIONES.md#checkpoint135'
        row['observaciones'].append(scope)
    data['requisitos'].append(row)
    notes += '\n### '+ident+'\n\n'+problem+'\n\nCriterio: '+criterion+'\n\nEstado: '+observation+'\n'
assert {key:value for key,value in immutable(data).items() if key in original} == original
assert len(data['requisitos']) == 133
for row in data['requisitos']:
    if row['id'] in {'R09','R20','R21','QA-06','QA-10','R33','R18','OPS07'}:
        row['observaciones'].append('Checkpoint135: '+scope)
    if row['id'] in {'R23','R04','R19','R31'}:
        row['observaciones'].append('Checkpoint135: autor Backend34 tiene91SQLitePASS/28PG distintos/5 migraciones/restore1, pero SEC independiente confirmó SEC20 y QA-21 con4RED; no hay aceptación global34 ni código34/35 enMAIN.')
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
for name, paragraph in {
    'NUEVOS_HALLAZGOS.md':notes,
    'DECISIONES.md':'\n\n## Checkpoint135\n\n'+scope,
    'VALIDACION.md':'\n\n## Checkpoint135\n\nBackend34 autor81f190:91SQLitePASS/5PGdeselected;28IDs PG distintos,5 migraciones y1restore poblado con67aserciones históricas conservadas. Doce UUID propias cerradas sinFORCE y ausencia fresca. La revisión SEC posterior confirma4RED (SEC20/QA-21), no aceptación global. Desktop queda excluido del trabajo futuro; sus100casos son sólo autor histórico0d20. QA no ejecutó su revisión Desktop. Las pruebas SaaS35 yQA-20 continúan aisladas.',
    'CAMBIOS.md':'\n\n## Checkpoint135\n\n'+scope+' Se importan únicamente30archivos de evidencia anterior, sin producto34/35/desktop. Se añaden SEC19/SEC20/QA-19/QA-20/QA-21 y se conserva íntegra la definición de los128criterios anteriores.',
    'RIESGOS.md':'\n\n## Checkpoint135\n\nSEC19 conserva riesgo de hidratación innecesaria hasta revisión independiente; SEC20 yQA-21 están reproducidos enPG y requieren reparación antes de integración34. QA-20 bloquea el guardado progresivo delAPI en perfil vacío. Responsable:backend/seguridad/coordinación. Desktop tiene excepción expresa de alcance para la entrega actual; no se afirma que el defectoQA-19 haya desaparecido.',
}.items():
    path = D/name
    assert b'## Checkpoint135' not in path.read_bytes()
    path.write_bytes(path.read_bytes().rstrip()+paragraph.encode()+b'\n')
state = (D/'ESTADO.md').read_text(encoding='utf-8')
state = state.replace('Checkpoint134 local: esquema33 y128 requisitos (92 originales y36 añadidos).',
    'Checkpoint135 local: esquema33 y133 requisitos (92 originales y41 añadidos).',1)
state = state.replace('1 plan por cliente al día y10 planes totales por gimnasio al día. Desktop sigue\nsoportado.',
    '1 plan por cliente al día y10 planes totales por gimnasio al día. Por instrucción\nexpresa posterior, el trabajo continúa únicamente en el servicio web.',1)
state += '\n## Checkpoint135\n\n'+scope+'\n\nBackend34 autor cerrado, SEC reproduce4RED enPG paraSEC20/QA-21 y corrige enWT propia. QA independiente API35 yUI35 siguen en curso. MAIN conserva esquema33; no integraDesktop35 ni producto34/35. QA-20 parcialAPI confirmado y en reparación. Próximo: repetir canarios originales, recapturar34 si cambia trigger ycapturarPG35 después del handoff exclusivo.\n'
(D/'ESTADO.md').write_bytes(state.encode())
(D/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint135:133requisitos, los128criterios previos exactos. Trabajo y entrega
limitados al servicio web por instrucción expresa del usuario. Desktop35 ysu
evidencia quedan conservados en rama aislada, sin integración ni revisión futura.

MAIN continúa en esquema33 conCI33/R05v2. Backend34 tiene evidencia de autor,
pero revisión independiente confirmaSEC20 yQA-21; corrección en curso. API35,
UI35 yQA-20 permanecen aislados yrequieren aceptación integrada. R05 global
sigueRED1603. R27,R31,imagen,broad y navegador actuales siguen abiertos.
Free10clientes/1plancliente/día/10totalgym/día. Sin publicación ni despliegue.
''').encode())
proof = D/'evidence/checkpoint135-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
confirmed = {'scope':'Only web after explicit user instruction; existing desktop work preserved, no integration.',
    'independent_PG34':{'product':'81f19009df3ba7b34872cedde68a98d42f99cbb9','head':'f848256ceac6a8c6a7c2cc8e3a8159d8b61e0759',
        'original_canaries':4,'failures':4,'errors':0,'skips':0,'factories':['api.app','web.main_web'],
        'findings':['SEC20','QA-21'],'own_database':'metodobase_test_followup34_bb634036d3594a5ab669ec5527a94956',
        'reported_closure':'normal DROP, zero sessions, fresh absence','evidence_scope':'Coordinator receipt of independent agent; sealed peer RAW pending.'},
    'QA20':{'frontend_original':'1FAIL_API_1PASS_SaaS','root_source':'54e511b3ac8636c6ffb6c20cd3b4f8d86922ad2e',
        'corrected_framing_phase':'metodobase-web-phase-qa20-before-corrected-20261020','cases':8,'failures':2,'errors':0,
        'initial_phase':'29 cases with21boundary replays and8new;6failures, four due to erroneous expectation that unknown declaration serializes as null. Preserved, not attributed as product defects.'},
    'ID_erratum':'SEC18 already identifies withdrawal session checkout. Old informal Sec18projection refers to new SEC19; original evidence is unchanged.'}
(proof/'confirmed-web-findings.json').write_bytes(encode(confirmed))
(proof/'imports.json').write_bytes(encode(imports))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
proc = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(O/'registry.stdout').write_bytes(proc.stdout)
(O/'registry.stderr').write_bytes(proc.stderr)
controls = ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','NUEVOS_HALLAZGOS.md','DECISIONES.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md']
git('-c','core.autocrlf=false','add','-f','--',*paths,proof.relative_to(R).as_posix())
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
checked = git('diff','--cached','--check',check=False)
(O/'whitespace-before.stdout').write_bytes(checked.stdout)
(O/'whitespace-before.stderr').write_bytes(checked.stderr)
cr_files = {}
observations = 0
if checked.returncode:
    assert checked.returncode == 2
    for line in checked.stdout.decode().splitlines():
        match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
        if not match:
            continue
        path, number = match.group(1), int(match.group(2))
        assert path in paths
        raw = cr_files.setdefault(path,git('show',':'+path).stdout)
        physical = raw.split(b'\n')[number-1]
        assert physical.endswith(b'\r') and not physical[:-1].endswith((b' ',b'\t'))
        observations += 1
    assert cr_files and observations
    attribute = D/'evidence/.gitattributes'
    prefix = 'docs/implementation/20261018-evolution/evidence/'
    attribute.write_bytes(attribute.read_bytes().rstrip()+b'\n'+''.join(path.removeprefix(prefix)+' whitespace=cr-at-eol\n' for path in sorted(cr_files)).encode())
    git('-c','core.autocrlf=false','add','--',attribute.relative_to(R).as_posix())
git('diff','--cached','--check')
assert all(sha((R/path).read_bytes()) == digest for path,digest in preserved.items())
assert all(git('show',':'+path).stdout == (R/path).read_bytes() for path in paths)
assert all(path.startswith('docs/') for path in git('diff','--cached','--name-only').stdout.decode().splitlines())
receipt = {'base':BASE,'requirements':133,'prior_immutable_criteria_preserved':128,
    'untracked_files_preserved':len(preserved),'evidence_imports':30,'product_imported':False,
    'CRLF_raw_preserved_paths':sorted(cr_files),'CR_only_findings':observations,'whitespace_check_exit':0,
    'scope':'web_only_explicit_user_instruction','desktop_review_executed':False,'global_acceptance':False}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Limit execution to the web service and register confirmed review findings')
assert not git('status','--porcelain','-uno').stdout.strip()
result = {'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
