from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018')
TMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
RUN=ROOT/'docs/implementation/20261018-evolution'
EV=RUN/'evidence'
BASE='edf267ca9f44228620535c8a661c3196598c1b8d'
sha=lambda blob:hashlib.sha256(blob).hexdigest()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((TMP/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
# Authenticate every evidence prerequisite before editing the control documents.
receipt=json.loads((TMP/'metodobase-checkpoint125-import-result.json').read_bytes())
delta=json.loads((TMP/'metodobase-checkpoint125-delta-result.json').read_bytes())
assert not set(receipt['files'])&set(delta['files'])
receipt['files'].update(delta['files'])
raw={ROOT/name for name in receipt['files']}
for path in raw:
    meta=receipt['files'][path.relative_to(ROOT).as_posix()]
    blob=path.read_bytes();assert len(blob)==meta['bytes'] and sha(blob)==meta['sha256'];scan(blob,path.name)
for prefix,expected_manifest in {
    'root-mfa31-terminal-sv-serial-diagnostic-20261019':'e7474296a125900dc81a49de723b51d558e65465db59a7c777d927f1770cce6e',
    'root-bootstrap-outcome-logging-author-20261019':'f28ad773af4b2d5210b5bca721ec9c1c6266348ef59612bbfe779303c41a8e13',
    'root-mfa31-fixture-clock-author-20261019':'aac112d2c79029cffde99fff13c465f4959620100b0c37b7d03bbccf45347736',
}.items():
    folder=EV/prefix
    assert folder.is_dir(), ('author seal still pending',prefix)
    assert sha((folder/'manifest.json').read_bytes())==expected_manifest
    manifest=json.loads((folder/'manifest.json').read_bytes())
    members=manifest.get('files',manifest)
    if isinstance(members,list):members={row.get('path',row.get('file')):row for row in members}
    for name,meta in members.items():
        blob=(folder/name).read_bytes();assert sha(blob)==meta.get('sha256',meta.get('SHA256'));assert 'bytes' not in meta or len(blob)==meta['bytes']
    for path in folder.rglob('*'):
        if path.is_file():scan(path.read_bytes(),path.name);raw.add(path)
data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{row['id']:{field:row[field] for field in fields} for row in value['requisitos']}
prior=criteria(data)
assert len(prior)==120
new_ids=['OPS14','QA-16','SEC16','UX-20']
assert not set(new_ids)&set(prior)
def row(ident,source,problem,criterion,owner,tasks,commits,evidence,tests,notes,validation='verificado'):
    assert (ROOT/source).is_file(), source
    return {'id':ident,'identificador_original':ident,'fuente':source,'seccion':'Hallazgo nuevo checkpoint125',
        'problema':problem,'criterio_exacto':criterion,'prioridad':'P2','responsable':owner,'tareas':tasks,
        'dependencias':tasks,'estado':'en_revision','implementacion':'en_revision','validacion':validation,
        'despliegue':'no_desplegado','entorno':'local','cambios':notes,'commits':commits,'pruebas':tests,
        'evidencia':evidence,'documentacion':['ESTADO.md','VALIDACION.md','DECISIONES.md'],
        'revisor':owner+'; QA independiente en evidencias','bloqueo':None,
        'observaciones':['Verificación acotada a las fuentes indicadas. MAIN permanece en esquema30; la integración común sigue pendiente.']}
prefix='docs/implementation/20261018-evolution/'
data['requisitos'].extend([
    row('OPS14',prefix+'evidence/qa-bootstrap-outcome-logging-independent-20261019/source.json',
        'La configuración de Alembic deshabilita el logger de bootstrap ya existente: un fallo posterior a migrar conserva exit1 pero pierde el registro de resultado, y también se silencia la confirmación de éxito.',
        'El CLI debe registrar un resultado explícito después de la verificación completa y un error opaco cuando falla migración o verificación; no anunciar éxito prematuro, incluir secretos ni habilitar loggers ajenos. Conservar los códigos de salida, transacciones y validadores existentes.',
        'Operación y QA',['R03','R17','R18'],['4740fa235170ded9596927c9ea261a9d7998122e'],
        ['evidence/qa-bootstrap-outcome-logging-independent-20261019/source.json'],
        ['Autor: mismos2 rojos→2 verdes;34 históricos+2 nuevos=36 verdes. Peer: mismos2+1 fallo forzado después de migrar/verificar=3 verdes; no marcador privado ni traceback ni falso éxito.'],
        ['Cambio aislado en alembic.ini y prueba nueva. El resto de loggers conserva su política previa; imagen con este cambio pendiente.']),
    row('QA-16',prefix+'evidence/qa-current31-fixture-clock-focal-independent-20261019/source.json',
        'Dos helpers de pruebas MFA pueden generar un TOTP en una ventana y confirmarlo en la siguiente antes del cuerpo de negocio; el segundo wrapper inicial además cambia la firma instant(now=...).',
        'Cada setup MFA debe observar un instante consciente único para sus peticiones reales de autenticación y generar el TOTP correspondiente. Restaurar reloj e identidad de función antes del cuerpo de negocio y ante excepción, conservar la firma y validación original y no añadir reintentos, bypass de autenticación ni cambios a las aserciones históricas. El fixture current_link_fixtures se ejecuta en setup serial por proceso; MfaContractClient debe aislar su contexto de threads síncronos ajenos y serializar sus owners cooperantes.',
        'Backend y QA',['R05','R19','R32'],['9b14e2e9c3279a9a85eef444f1ef50f3f5f8750b','9abdabf5e1e7c2aa6b2c005cee15068a6ef9b9cb','d0121919e6207dd76bbb8c0c9bff5966c6930d3f'],
        ['evidence/qa-current31-fixture-clock-focal-independent-20261019/source.json','evidence/qa-current31-fixture-clock-pg34-independent-20261019/source.json','evidence/backend-mfa31-contract-clock-20261019/source.json','evidence/backend-mfa31-contract-keyword-20261019/source.json','evidence/qa-mfa31-contract-clock-independent-20261019/source.json'],
        ['Primer helper: mismos2 setupERROR→2 PASS;31 autor,35 positivos SQLite independientes y34/34 PostgreSQL. Segundo9ab:51autor y1canary verde,2keywords rojos del peer preservados; sucesord012 mismos2→verdes. Peer final53+4=57IDs distintos, sin sumar replays.'],
        ['Sólo fixtures y pruebas. No se atribuye retrospectivamente el único error de la regresión3047: faltó telemetría de status/counter en ese resultado. El contrato actual es síncrono; no implica aislamiento de tareas con contextos copiados ni CAS frente a instaladores externos no cooperantes.']),
    row('SEC16',prefix+'evidence/qa-r25-ui-http-replay-independent-20261019/independent-test.py',
        'La octava sección de exportación rechaza correctamente un cursor de UUID con mayúsculas, pero la respuesta422 usa Referrer-Policy general en la ruta privada de exportación.',
        'Aplicar no-referrer y no-store a la ruta canónica /api/usuario/privacidad/exportar y su única variante con barra final, para todos los métodos y resultados, incluidos errores y fallback. Mantener las rutas vecinas, controles de autorización y DTO de exportación intactos.',
        'Backend, seguridad y QA',['R17','R25','R31'],['2002959122f142162192a122fad7ba2cafbb12b1','345aa7ce16f65fec9481b48cfcd63c33ff3835fc'],
        ['evidence/backend-r25-export-private-headers-20261019/source.json','evidence/security-export-private-headers-independent-20261019/source.json','evidence/qa-r25-ui-after-review-20261019/review.json'],
        ['Mismos2 canarios422 rojos→2 verdes en autor y composición345. Seguridad20/20: métodos, errores500/fallback503, slash307 y vecinos.'],
        ['Middleware limita el cambio a dos rutas exactas; no se demostró fuga de contenido. Reparación revisada sobre345, sin aceptación global de R25/R31.']),
    row('UX-20',prefix+'evidence/qa-r25-ui-layout-before-independent-20261019/manifest.json',
        'Las tablas de progreso comprimen cifras, unidades y fechas en varias líneas a320/390px; los controles axe y overflow de página no detectaron esa pérdida de legibilidad.',
        'Mostrar cada cifra con su unidad y cada fecha civil como un token legible en320,390,768 y1440px. Las tablas amplias deben desplazarse dentro de una región etiquetada y enfocable, con ArrowRight efectivo, sin desbordamiento horizontal de página ni degradación de los controles accesibles existentes.',
        'Frontend, UX y QA',['R13','R25'],['ef9dca7aa7d7008def92a5ec64b12f4585798fd7','345aa7ce16f65fec9481b48cfcd63c33ff3835fc'],
        ['evidence/r25-table-layout/freeze.json','evidence/qa-r25-ui-after-review-20261019/review.json'],
        ['Driver móvil y parser idénticos:0/4→4/4. Ocho vistas reales personal/profesional en320/390/768/1440:0 violaciones axe,0 overflow de página,0 errores JS; capturas observadas.'],
        ['Sólo CSS: mínimo36rem, columnas9rem y tokens sin partir. No se reatribuyen a345 los14 grupos funcionales históricos de b7.']),
])
notes={
 'R03':'OPS14 confirmado: Alembic silenciaba db_bootstrap. Fix474 conserva validadores/transacciones y logging opaco;36autor/3peer verdes. La matriz independiente de ACL de PostgreSQL confirma guard29→30 correcto; el DEFAULT FUNCTIONS adicional era deriva del harness.',
 'R05':'QA-16: primer helper9b14 aceptado focalmente SQLite35/PG34,19asserts e inversa conservados. Segundohelper9ab dio51 verdes deautor, pero2keywords rojos delpeer; sucesord012 preserva firma y pasa57IDs peer distintos. Comúnde506 sóloalembic.ini ytests:preflight145workflow/205parser/173PGIDs/23helpers,4grupos/5módulos. Serial única inició21:07UTC,n2pendiente.',
 'R13':'UX-20 real: cifras/fechas fragmentadas aunque axe/bodyoverflow ya pasaban. CSSef9 +composición345 conserva driver/parser: mismos4rojos→4verdes;8vistas afectadas con controles y capturas revisados. Lease Chrome/RAM devuelto y procesos propios ausentes.',
 'R17':'OPS14 logging y SEC16 export privado revisados acotadamente. Seguridad20/20 para exactas2rutas export todosmétodos/status/fallback, vecinosintactos; nofuga demostrada. Se mantiene la limitación de métrica call_next y ausencia de SLO/distribución.',
 'R18':'Runtimec538 se construyó:54metadata+54imports/355fuentesexactas,ELF0f618 y5argv/1export medidos. Primer startup producción rojo y rollback total; no health/ready/worker acreditados. QA matriz2DB/4roles confirmó deriva DEFAULT FUNCTIONS, guardcorrecto. f74(app6a75+native72+logger474) preparado366Gitblobs/TARa644; build/startup pendientes del margen RAM. OpenSSL sistema3.5.7 y cryptography4.0.3 son mediciones distintas; noSCA71/globalSEC10.',
 'R19':'Serial6a75 cerró3047:3045PASS+1setupERROR+1skipWindows conocido; ambos antiguos recoveryMAX pasan. No Timeout ni causa retrospectiva del error confirmada; gate real100%líneas/ramas en3módulos. Amboshelpers ylogger aceptados focalmente. Comúnde506 conserva10176otrasentradas y sóloalembic.ini deproducción; preflight145/205/173/23quieto yserial3057esperados inició21:07UTC. n2pendiente.',
 'R25':'Backendbd0501 yUI8dc congelados, composiciónb7. Seguridad aceptó lector de mismaConnection/SAVEPOINT con22criterios en fases20/22+3/3,5UUID propias cerradas; primer22setupERROR era ctypesdelharness. QA152VM+2SSR+22autorHTTP y14grupos Chrome sóloenb7. Header+CSS integradosen345, mismos2+4antesrojos ahora verdes y8vistas afectadas. Restore32/CI32/matrizcomún pendientes. Límite de padreinactivo sigueabierto: retirorequiereunflujo específico, sinrelajarlogin general.',
 'R29':'SEC15 aceptado independientemente: mismos14+27controles=41/41; loginMAX originalpasa enserial6a75. Capacidad409 antes deconsumo/incremento ysinwrap/reset. Candidata31 aúnpendiente de broadcomún final.',
 'R31':'Exportación8 aislada y cabecerasSEC16 revisadas. Seguridad demostró parentOFF dejaownlist/withdraw401 hastaON; grantno retiradovuelvea serlegible. No hay endpointpúblicodeOFF demostrado. Diseño de retiroconpruebaprimaria/MFAfresca acotada sinJWT estádocumentado, aúnnoimplementado. Países/retención yborrado siguenabiertos.',
 'R32':'SEC15 terminalSV41peerverde. Amboshelpers sólofixtures, noendpointsniDDL;9b14SQLite35/PG34yd01257peer aceptados acotadamente. Alertasporcambiodefactor/custodia/rotación/proveedoresGoogleRedisMail/pérdidatotal continúanpendientes.',
 'SEC15':'Peer41/41 deSeguridad aceptado; same14+27propios. RecoveryMAX2casos originales verdes enserial6a75. Broadfinal ycomposiciónMAIN31pendientes.',
 'SEC10':'Fullruntimec538 medido54/355/nativeSHA ysystemOpenSSL3.5.7 frentecryptography4.0.3. Startuporiginalrojo preservado; matrizACLindependiente atribuye DEFAULTFUNCTIONS alharness. Fuenteimagenf74 actualpreparada, nopasaSCA71/producciónpor esehecho.',
 'QA-15':'CI145/173/23 permanece byteexacta. Precisión:4grupos de publicación contienen5módulos/pins; member_races incluye2. No modificar el mapa sellado ni interpretar un mero conteo como ejecución32.',
}
for item in data['requisitos']:
    if item['id'] in notes:
        item['observaciones'].append('Checkpoint125: '+notes[item['id']])
refs={
 'R03':['qa-bootstrap-outcome-logging-independent-20261019/source.json','qa-runtime31-c538-acl-independent-public-20261019/source.json'],
 'R05':['qa-current31-fixture-clock-focal-independent-20261019/source.json','qa-current31-fixture-clock-pg34-independent-20261019/source.json'],
 'R13':['qa-r25-ui-after-review-20261019/review.json'],
 'R18':['prepared-wave125-20261019/runtime-logging/source-context-freeze.json','qa-runtime31-c538-acl-independent-public-20261019/source.json'],
 'R25':['backend-r25-progress32-20261019/source-freeze.json','r25-ui/functional-source.json','security-progress32-reader-review-independent-20261019/source.json','qa-r25-ui-after-review-20261019/review.json'],
 'R29':['security-terminal-sv-peer-independent-20261019/source.json'],
 'R31':['security-progress32-reader-review-independent-20261019/retirement-design.md','security-export-private-headers-independent-20261019/source.json'],
 'SEC15':['security-terminal-sv-peer-independent-20261019/source.json'],
}
for item in data['requisitos']:
    for ref in refs.get(item['id'],[]):
        assert (EV/ref).is_file(),ref
        value='evidence/'+ref
        if value not in item['evidencia']:item['evidencia'].append(value)
assert len(criteria(data))==124 and {ident:criteria(data)[ident] for ident in prior}==prior
(RUN/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
(RUN/'ESTADO.md').write_text('''# Estado de ejecución 20261018-evolution

Checkpoint 125 local. Se conservan los 92 IDs originales y los 120 criterios anteriores exactos; el registro contiene 124 requisitos. Nuevos: OPS14 (logging de bootstrap), QA-16 (relojes de fixtures MFA), SEC16 (cabeceras de exportación) y UX-20 (tablas móviles). MAIN permanece en esquema 30; las candidatas 31 y 32 siguen aisladas. Free: diez clientes activos, un plan por cliente al día y diez planes totales por gimnasio al día. Desktop continúa soportado.

La candidata 31 en 6a75 conserva una regresión roja de 3.047 casos: 3.045 aprobados, un error de setup MFA y la omisión Windows conocida de symlink. Los dos casos originales de recuperación con SV máximo ya pasan. Seguridad aprobó 41/41 controles de SEC15. El primer helper de reloj 9b14 tiene 35 positivos SQLite y 34/34 PostgreSQL independientes. El segundo, 9ab, tuvo dos incompatibilidades de argumento `now=`: se conservan los rojos y el sucesor d012 pasó 57 IDs distintos de QA. La causa exacta del error amplio original permanece sin atribuir por falta de telemetría. [Diagnóstico rechazado](evidence/root-mfa31-terminal-sv-serial-diagnostic-20261019/source.json), [peer del segundo helper](evidence/qa-mfa31-contract-clock-independent-20261019/source.json).

La composición 31 de506b6 mantiene exactas otras 10.176 entradas Git y cambia en producción sólo alembic.ini. El preflight pasó 145 canarios de workflow y 205 del parser; conserva 173 IDs PostgreSQL y 23 helpers históricos. Fuentes, 89 paquetes y Python estables; pip check verde antes y después. La nueva serial con cobertura inició a las 21:07 UTC, con 3.057 casos previstos y preservación obligatoria de los 3.047 anteriores. n2 sigue pendiente; no se declara una aceptación amplia antes de esos resultados.

El logging de Alembic se corrigió en 474: 36 casos del autor y 3 independientes verdes. La imagen c538 midió 54 paquetes/imports, 355 fuentes y el ELF nativo esperado; su primer startup falló y se conserva como diagnóstico. QA aisló el DEFAULT FUNCTIONS añadido por el harness como causa, sin cambiar la migración. La nueva fuente f74 une app 6a75, native72 y logger 474; 366 Gitblobs y el contexto TAR a644 están congelados. La imagen dc8fab5 se construyó una vez y el probe del usuario real está aprobado por Operación; smoke y cierre aún en curso, pendientes de sello. No hay aceptación SCA71 ni despliegue.

R25: backendbd0501 y UI8dc están congelados. Seguridad aceptó el lector acotado de la misma conexión y SAVEPOINT;22 criterios repartidos en fases documentadas, sin convertir los errores de harness previos en éxitos. QA anterior sobreb7 ejecutó152 controles VM,2 SSR,22 HTTP del autor y14 grupos de navegador. Esos resultados conservan su fuente. La sucesora345 contiene las correcciones de cabeceras y CSS: mismos2 canarios422 y4 móviles rojos→verdes, más8 vistas afectadas sin violaciones axe, desbordamiento de página ni errores JS. Los servidores y procesos propios cerraron y el lease de RAM volvió a Operación. [Revisión posterior](evidence/qa-r25-ui-after-review-20261019/review.json).

El retiro propio con autoridad parental inactiva continúa abierto. El comportamiento401 se reprodujo al cambiar administrativamente el padre; no se demostró una ruta pública para desactivarlo. Está diseñado un flujo de retiro con prueba primaria y MFA fresca, acotado al consentimiento propio y sin sesión general, pero aún no está implementado. R25 también requiere restore32 independiente, CI32 y matriz común. [Diseño](evidence/security-progress32-reader-review-independent-20261019/retirement-design.md).

Las revisiones anteriores mantienen su alcance: CI31 con173 casos PostgreSQL, R17 focal, restauración31 y fixtures79. La precisión del mapa de CI es cuatro grupos y cinco módulos/pins, porque member_races contiene dos. No se reatribuyen a otras fuentes los resultados de Chrome ni los diagnósticos nativos.

R23, R24, R27, R30, R31, R32, R33, R34 y R35 conservan trabajo pendiente. Países y retención, y volumen y p95, siguen consultados sin respuesta; no se inventan políticas, objetivos, entrevistas ni dictámenes. Desktop necesita su validación sobre la fuente final. El workspace original permanece intacto. No hay push, PR, despliegue, cargos, recursos pagados ni comunicaciones a terceros.

Siguiente acción: completar la serial de506 y luego n2, y sellar imagen, smoke y cierre de recursos. Después integrar 31 y continuar restore, CI y retirada de 32. [Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''',encoding='utf8')
(RUN/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint 125: 124 requisitos, 92 originales; 120 criterios anteriores exactos. MAIN sigue en esquema 30. Las candidatas 31 y 32 todavía necesitan integración y comprobaciones comunes; no constituyen una versión lista para desplegar.

31: SEC15 tiene 41 controles independientes verdes. La serial 6a75 se conserva roja: 3.045 PASS, un error de setup MFA y un skip Windows. Ambos helpers de reloj están aceptados acotadamente: 35 SQLite/34 PG para 9b14 y 57 IDs de QA para d012. Logger 474 tiene 36 del autor/3 del peer verdes. Común de506: preflight 145 workflow/205 parser y serial en curso; n2 pendiente. Imagen dc8fab5 construida y probe aprobado por Operación; startup, health, ready, worker y cierre todavía pendientes de sello.

32: backendbd0501/UI8dc y lector acotado revisados; composición345 corrige exportación privada y tablas móviles con los mismos2+4 canarios verdes y8 vistas afectadas. Pendientes retiro con padre inactivo, restore32 independiente, CI32 y matriz común. No se reatribuyen resultados históricos a345.

Free:diez clientes activos,un plan por cliente al día y diez totales por gimnasio al día. Desktop soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''',encoding='utf8')
addenda={
 'VALIDACION.md':'SEC15:41/41 peer. Logger474:36autor/3peer. Reloj9b14:35positivos SQLite y34/34 PostgreSQL;CI145/173/23 quieto,4grupos/5módulos. Helper9ab:51autor pero2keyword now= rojos independientes;d012 conserva esos2canarios y pasa53+4=57IDs distintos deQA. Comúnde506 preflight145workflow/205parser/173PGIDs/23helpers,10208fuentes/89paquetes/Pythonquiet,pip0/0; nueva serial iniciada21:07UTC,n2pendiente. Serial6a75:3045PASS+1setupERROR+1skip, no aprobación ni causalidad retrospectiva; cobertura real100%líneas/ramas en3módulos. R25lector:22criterios repartidos20/22+3/3; no23green enuna tanda. UIb7:152VM/2SSR/22autorHTTP/14Chrome con sufuente;345: mismos2HTTP+4móviles afterverdes,8vistas axe/reflow/capturas revisadas. Todos los recursos propios de esas fases cerrados. Runtimec538:54metadata/import/355fuentes medidos perostartup rojo; QA ACLsinDEFAULTFUNCTIONS29/head31green,conDEFAULTFUNCTIONS29commit+headrollback correctamente rojos. No SLO ni SCA71.',
 'CAMBIOS.md':'MAIN sólo incorpora evidencia y control, sin producto31/32. Cambios aislados: loggerAlembic474, clocks9b14/9ab, exportprivate200295 y CSSef9; composiciónUI345. Backend32bd0501 ofrece medidas explícitas, consentimientos append-only/CAS y lector limitado; UI8dc conserva RAMfences y export8. Las reparaciones no cambian contratos clínicos/comerciales. Fuenteimagenf74=app6a75+native72+logger474; contextoa644366Gitblobs. Se conservan todos los befores y diagnósticos rechazados.',
 'DECISIONES.md':'No debilitar assertions para corregir carreras de fixtures: congelar sólo setup, restaurar antes del negocio y preservar la firma original. No atribuir el error3047 a una carrera sin telemetría histórica suficiente. El DEFAULTFUNCTIONS del harness era redundante y alteraba proacl: retirar ese estímulo de la nueva prueba, no relajar el guard29→30. Aceptar header/CSS sólo con los mismos canarios y fuente345. Mantener login general inválido con padreOFF; retiro necesita un flujo limitado con pruebas frescas y sin JWT, todavía pendiente. Corrección de redacción CI:4grupos,5módulos/pins. El lease autor32 usa UUID, pero write_text inicial no demuestra creación exclusiva; no alterar ese sello ni repetir la afirmación.',
 'RIESGOS.md':'QA-16 helpers aceptados acotadamente; serial/n2 de la composición31 siguen pendientes, y las pruebas seriales no garantizan aislamiento de contextos copiados. R25/R31 retiroparentOFF sigue abierto, al igual que restore32/CI32/matrizcomún. Runtime nuevo requiere sello delsmoke/cierre yrevisión; c538rojo no acreditahealth/ready/worker. RAMhostobservada cerca1.5GiBconVM2GiB: sinChrome ni nuevos trabajos pesados simultáneos, cierrecooperativo de propios. CryptographyOpenSSL4.0.3 ysystem3.5.7 son identidades distintas y no cierranSCA71. Se conserva lease32write_text noexclusivo como límite de evidencia. Políticas/retención/países, SLOrepresentativo, pilotos, dictamen especialista y dependenciasMFA/proveedores siguen pendientes.',
}
for name,text in addenda.items():
    with (RUN/name).open('ab') as handle:handle.write(('\n\n## Checkpoint125\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True,capture_output=True)
assert {ident:criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))[ident] for ident in prior}==prior
# This checkpoint authenticates imported bytes, but does not claim tests were rerun by this driver.
seal=EV/'checkpoint125-seal-receipt-20261019'
assert not seal.exists();seal.mkdir();(seal/'.gitattributes').write_bytes(b'* -text\n')
(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
(seal/'receipt.json').write_bytes((json.dumps({'base':BASE,'registry':124,'previous_criteria_exact':120,'new_ids':new_ids,'main_product_changed':False,
    'files':{path.relative_to(ROOT).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(raw)}},indent=2)+'\n').encode())
raw.update(path for path in seal.iterdir() if path.is_file())
names=sorted(path.relative_to(ROOT).as_posix() for path in raw)
docs=[(RUN/name).relative_to(ROOT).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record independent runtime, privacy, layout and MFA fixture reviews'],cwd=ROOT,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':124,'previous_criteria_exact':120,'authenticated_RAW':len(names),'main_product_changed':False}))
