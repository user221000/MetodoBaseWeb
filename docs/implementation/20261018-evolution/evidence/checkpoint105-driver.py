import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path('F:/MetodoBaseWeb-execution-20261018')
RUN = ROOT / 'docs/implementation/20261018-evolution'
EV = RUN / 'evidence'
TEMP = Path('C:/Users/Consu/AppData/Local/Temp')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head.startswith('6b0dc01')
receipt = EV / 'checkpoint105-local-source.json'
assert not receipt.exists()

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

verified = {}
for name, manifest_name, expected in [
    ('qa-integrated28-history-landing-postfix-20261019', 'evidence-manifest.json', 'c7ea6765bfbd36c25c55e2c8093786de6a092881f93ca1d413e3c41e802de00f'),
    ('linux-recovery28-image-abd559a', 'evidence-manifest.json', 'fc0053a28039d61c8b7a82b99fd6f13b4a9ed595d9d8cd4711d96c1223aa6705'),
]:
    folder = EV / name
    raw = (folder / manifest_name).read_bytes()
    assert sha(raw) == expected, name
    files = load(folder / manifest_name)['files']
    for relative, value in files.items():
        target = folder / relative
        assert target.resolve().is_relative_to(folder.resolve())
        digest = value if isinstance(value, str) else value['sha256']
        assert sha(target.read_bytes()) == digest, str(target)
        if isinstance(value, dict) and 'bytes' in value:
            assert target.stat().st_size == value['bytes']
    verified[name] = {'manifest_sha256': expected, 'files_rehashed': len(files)}
assert sha((EV / 'qa-integrated28-history-landing-postfix-20261019/final-summary.json').read_bytes()) == 'ca17f9f64a84221d61a2eaaea9a8742ae3870994ebdb07136617a7b222ae990a'
assert sha((EV / 'r12-contract-security-review-20261019/source.json').read_bytes()) == '620a48561d351c591b062bfdea99c6b3fe83d50bc6f973a4f6dc6340a2f192a1'
assert sha((EV / 'r12-root-mechanism-review-20261019/review-summary.json').read_bytes()) == 'ca283877d9805cb2afb8c86c34c09b4de69c6abb3ab3c6d685ee7c2b3634ac3c'

win = TEMP / 'metodobase-python31215-windows-provenance-20261019'
dest = EV / 'desktop31215-security-20261019'
dest.mkdir(exist_ok=False)
prepared = load(win / 'prepared.json')
summary = load(win / 'desktop-audit-tests/summary.json')
assert prepared['archive_sha256'] == 'bbc902d4d187ac4914915bf538196a064b49109a33a104965b5164ced5b80a1e'
assert summary['audit_exit'] == 0 and summary['audited_dependencies'] == 83
assert [r['tests'] for r in summary['results']] == [45, 97]
assert all(r['exit'] == r['bad_or_skipped'] == 0 for r in summary['results'])
assert summary['source_commit'] == 'dd9877350aad3f483299c990a1e97aab63c83f5d'
copy_names = [
    'prepared.json', 'selection.json', 'runtime-inspect.log',
    *('desktop-environment/' + p.name for p in (win / 'desktop-environment').iterdir() if p.is_file()),
    *('desktop-audit-tests/' + p.name for p in (win / 'desktop-audit-tests').iterdir() if p.is_file() and p.name != 'source-photos-private.json'),
]
for name in copy_names:
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(win / name, target)
runners = [
    'metodobase-discover-python31215-windows-20261019.py',
    'metodobase-prepare-python31215-windows-20261019.py',
    'metodobase-prepare-desktop31215-environment-20261019.py',
    'metodobase-desktop31215-audit-tests-20261019.py',
]
zip_members = {}
with zipfile.ZipFile(dest / 'official-metadata-and-runners-raw.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
    for path, name in [(win / 'release-20261013.raw.json', 'release-20261013.raw.json'), (win / 'SHA256SUMS', 'SHA256SUMS'), *((TEMP / p, 'runners/' + p) for p in runners)]:
        raw = path.read_bytes()
        archive.writestr(name, raw)
        zip_members[name] = {'bytes': len(raw), 'sha256': sha(raw)}
(dest / 'raw-bundle-members.json').write_text(json.dumps(zip_members, indent=2) + '\n', encoding='utf-8')
(dest / 'README.md').write_text('''# Windows desktop: preparación de runtime corregido

CPython3.12.15 x64 procede del release inmutable20261013 de python-build-standalone del proyecto Astral; SHA/API/checksums coinciden. Se extrajo en Temp con validación de rutas y tipos, sin ejecutar instalador ni modificar PATH, registro o entornos anteriores. OpenSSL3.5.9 y Expat2.8.5 inspeccionados. No se acredita firma del artefacto.

Entorno nuevo:83 paquetes instalados con hashes y sólo wheels; incluye pip26.2.1. OSV sobre inventario efectivo83:0 coincidencias, pip check0. Fuente dd987:45 pruebas desktop soportadas y97 de receta/entrypoints nativos Windows, todas sin skips/fallos/errores.576 fuentes y83/89 paquetes target/herramienta estables. No se suman a la regresión SaaS2360.

Esto no es un nuevo bundle/ZIP/Setup ni una auditoría CVE de DLL nativas. Los artefactos históricos con3.12.13 se conservan. Reconstrucción, revisión independiente del payload e instalación siguen pendientes. El archivo de46MB y entornos están sólo en Temp; el ZIP conserva metadatos oficiales y runners RAW. La foto completa de fuentes queda privada; el resumen conserva su agregado.
''', encoding='utf-8')
(dest / 'manifest.json').write_text(json.dumps({'files': {p.relative_to(dest).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}}, indent=2) + '\n', encoding='utf-8')

cleanup = EV / 'owned-export-fixture-cleanup-20261019'
cleanup.mkdir(exist_ok=False)
for name in ['metodobase-cleanup-owned-export-fixture-20261019.ps1', 'metodobase-owned-export-fixture-cleanup-20261019.json']:
    shutil.copyfile(TEMP / name, cleanup / name)
(cleanup / 'README.md').write_text('''Se cerraron únicamente el listener30168 y su launcher288 tras verificar PID, nacimiento, ejecutable, comando y recibo histórico propio. No se borraron archivos.8776 se conservó por falta de atribución exacta;8780/8781/8784 ya estaban ausentes. El primer intento fue bloqueado antes de ejecutar el script por la política PowerShell; se usó Bypass sólo en el proceso de ejecución, sin cambio persistente de política. No se atribuye al cierre ninguna otra desaparición de listeners.
''', encoding='utf-8')

data = load(RUN / 'TRAZABILIDAD.json')
assert len(data['requisitos']) == 104
preserved = {r['id']: {k: r[k] for k in ['fuente', 'seccion', 'problema', 'criterio_exacto']} for r in data['requisitos']}
rows = {r['id']: r for r in data['requisitos']}
for ident in ['R05', 'R31', 'QA-01', 'QA-02', 'QA-07']:
    row = rows[ident]
    row['pruebas'].append('Gate amplio independiente a753b2c:2360passed/1skip conocido en serial588.64s y n2shuffle20261018/275.43s;2361nodeids/resultados idénticos,0fallos/errores.667fuentes/89paquetes idénticos en4fotos y4pipcheck0; cobertura100%líneas/ramas sólo tres módulos de dominio.')
    row['evidencia'].append('evidence/qa-integrated28-history-landing-postfix-20261019/final-summary.json')
    row['observaciones'].append('El primer serial dd987 dio2358pass/2fail/1skip por una aserción que conservaba checkout huérfano ya retirado. Originales intactos; a753 cambia sólo ese test, sin runtime ni pérdida de casos. CI nuevo y Linux/Actions separados.')
for ident in ['R29', 'UX-16']:
    rows[ident]['commits'].append('a753b2cdf61a91133bd58c3159b0b35e02167396')
    rows[ident]['evidencia'].append('evidence/landing-retirement-test-fix-20261019/summary.json')
    rows[ident]['observaciones'].append('Test vecino que esperaba checkout sin uso corregido tras2fallos del amplio;15nodosAST previos/resto módulo intactos,20dirigidas verdes y amplio2360/1skip en ambos órdenes.')
row = rows['R12']
row['estado'] = row['implementacion'] = row['validacion'] = 'en_curso'
row['cambios'].append('Contrato v2 aprobado por seguridad sólo para implementar29 aislado: vínculo explícito consentido, invitación por token de propósito, publicación inmutable derivada del Plan exacto y lector por destinatario. No integrado ni API aceptada todavía.')
row['commits'].extend(['4d537e4', '6b0dc01'])
row['evidencia'].extend(['evidence/backend-r12-contract-v2.md', 'evidence/r12-contract-security-review-20261019/source.json', 'evidence/r12-root-mechanism-review-20261019/review-summary.json'])
row['pruebas'].append('Prototipo SQL:35mecanismos autor; root4criterios propios positivos y1rojo real de payload no derivado. Canonical29 aislado reporta55dirigidas tras corregir payload y lock owner; revisión independiente de29/API pendiente, no se suma a amplio28.')
row['observaciones'].append('Conservados rojos de invalidación con owner inactivo, payload y lock owner. Las20políticas antiguas y contratos22–28 no se retargetean;29 añade3tablas/23familias cuando se acepte. Servicio/API/PDF/restore aún en desarrollo.')
for ident in ['SEC08', 'R18', 'R09']:
    row = rows[ident]
    row['evidencia'].extend(['evidence/linux-recovery28-image-abd559a/evidence-manifest.json', 'evidence/desktop31215-security-20261019/desktop-audit-tests/summary.json'])
    row['pruebas'].append('Linuxecae/abd:55paquetes Python reales,OSV0;TrivyOS87paquetes,166entradas/73IDs,exit1. Matriz73/21grupos conserva primarias y pendientes. Sólo liblzma5 tiene actualización binaria trixie disponible:2alias del mismo defecto;sinignore-unfixed ni excepciones.')
    row['pruebas'].append('WindowsCPython3.12.15 separado:83paquetes OSV0,pipcheck0,45desktop+97packaging/entrypoints nativos verdes;no bundle/Setup nuevo todavía.')
    row['observaciones'].append('Candidato Linuxbc365c1 sobre runtimeMAINa753 construido0/900.985s:imagen99c846bd28b0,87OS sólo liblzma5u1→u2,55PyPI sin cambios yOSV0. ScanOS exacto/comparación aún en ejecución;no startup ni aceptaciónOS global.')
rows['R34']['observaciones'].append('Amplio2360/1skip no mide carga. Próximo200HTTP C1/C5 de historial y EXPLAIN PG requieren ventana coordinada sin pruebas backend29; baseline1400 intacto y SLO/otros flujos pendientes.')
rows['R21']['observaciones'].append('Checkpoint105 añade pruebas RAW públicas; el scan41708e5 no cubre este nuevo HEAD. Nuevo scan exacto pendiente, sin ampliar excepciones globales.')
for row in data['requisitos']:
    assert {k: row[k] for k in preserved[row['id']]} == preserved[row['id']]
(RUN / 'TRAZABILIDAD.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def append(name, value):
    path = RUN / name
    path.write_text(path.read_text(encoding='utf-8').rstrip() + '\n\n' + value.strip() + '\n', encoding='utf-8')

(RUN / 'ESTADO.md').write_text('''# Estado de ejecución 20261018-evolution

Checkpoint105: implementación local en curso de104registros,92identificadores originales y12hallazgos añadidos. [Registro canónico](TRAZABILIDAD.json) conserva los criterios y fuentes completos. Original F:/MetodoBaseWeb-main intacto; trabajo F:/MetodoBaseWeb-execution-20261018, rama implementation/20261018-execution, base daa25efbf51d154710bad625025b345fa9ec9252. Sin push, PR, despliegue, cargos ni comunicaciones reales.

Producto integrado28 con recuperación, historial paginado y landing: runtime6270658, corrección de test a753b2c. Contrato R12v2 integrado sólo como documentación4d537e4/6b0dc01. [Cambios](CAMBIOS.md) y [validación](VALIDACION.md) conservan la historia por fuente y entorno.

Gate amplio independiente a753b2c aceptado:2360pass/1skip Windows conocido, serial588.64s y n2shuffle20261018 en275.43s.2361nodeids/resultados iguales,0fallos/errores;4fotos667fuentes/89paquetes y4pipcheck0. Cobertura100%líneas/ramas sólo nutrition_validation,food_catalog,profile_schemas;26tablas SQLite y3campos recovery verificados readonly.6mensajes de deprecación iguales,8avisos n2 por imports repetidos. Primer serial dd987 tuvo2fallos por una aserción que conservaba checkout ya retirado; original retenido, test focal corregido sin runtime ni pérdida de casos. [Aceptación](evidence/qa-integrated28-history-landing-postfix-20261019/final-summary.json).

Recuperación28:26tablas/20familiasRLS,QA/seguridad/restore28 aceptados,CI21PG/restore28/marker28 integrado. Historial R34:50/default,200máximo,keyset HMAC y summaries acotados;QA74Python+8propios/23VM/10browser autor+3propios,seguridad24 y composición36 aceptadas. R34 completo sigue abierto:200HTTP posteriores/EXPLAIN PG,SLO y otros flujos/entorno pendientes;baseline1400 intacto. R29/UX-16 ySEC07 verificados sólo localmente. [Carga](CARGA_LOCAL.md),[cuenta](RECUPERACION_CUENTA.md).

CI28 actual conserva gates anteriores. Extensión historia/landing aislada edcf164/57dba41:guard versionado con primarias fijadas,13canarios delta/16inertes,23VM nuevos y2fixtures. QA está ejecutando negativos propios y browser secuencial; no integrado ni Actions ejecutado todavía.

R12 en curso:contrato v2 aceptado para autoría aislada29;vínculo consentido/publicación por fuente exacta/sin acceso genérico a objetos. Prototipo35dirigidas y4criterios root positivos;rojos reales de invalidación/payload/lock preservados. Autor informa55canónicas verdes tras fixes;falta revisión independiente de29,servicios/rutas/PDF/restore e integración. Las20políticas y contratos22–28 permanecen históricos, sin reinterpretación. [Contrato](evidence/backend-r12-contract-v2.md),[seguridad](evidence/r12-contract-security-review-20261019/source.json),[rojo propio](evidence/r12-root-mechanism-review-20261019/review-summary.json).

Linux temporal:QEMU TCG propio2vCPU/2GiB,Debian12,Docker20.10.24,RedisTTL real sintético;SSH/QMP sólo loopback. Sin cambios BIOS/WSL/HyperV. Primera imagen5eb6d300 conservada:SCArojo6IDs pip25.0.1/Python3.12.13. Candidatoecae/abd usaPython3.12.15/pip26.2.1:55PyPI OSV0,87OS Trivyrojo166entradas/73IDs. Matriz primaria73/21grupos,noignores/noexcepciones. Sólo liblzma5 tiene fix binario trixie disponible (2alias de1defecto);restantes71IDs siguen abiertos. OpenSSL3.5.7 Debian tiene los13backports publicados, no se infiere vulnerabilidad sólo de comparar versión upstream3.5.9. [Evidencia OS](evidence/linux-recovery28-image-abd559a/evidence-manifest.json).

Candidato Linuxbc365c1 sobreMAINa753 construido0/900.985s:imagen99c846bd28b0,55PyPI iguales/OSV0,87OS con único cambio liblzma5u1→u2 por.deb SHA/size fijados. ScanOS/comparación en ejecución. No startup de producto,egress controlado,PG/Redis de aplicación ni aceptaciónOS global todavía. QEMU sin firma válida acreditada y Debian sin GPG acreditado;TCG no acredita p95 representativo.

Desktop soportado. Artefactos7bde30b históricos:ZIPf57a964b/Setup25ed92b1,51bundle/27payload exactos,OPS10 ausente;Python3.12.13,no instalación/upgrade/desinstalación/firma. NuevoCPythonWindows3.12.15 oficialAstral separado enTemp,OpenSSL3.5.9/Expat2.8.5,83paquetes con hashes,pipcheck0/OSV0.45desktop+97packaging/entrypoints Windows verdes sobredd987,576fuentes/83target/89tool estables. Nuevo bundle/Setup y revisión independiente pendientes;no cobertura de CVE deDLL por pip-audit. [Preparación](evidence/desktop31215-security-20261019/README.md).

Free confirmado:10clientes activos,1plan por cliente/día,10totales/gimnasio/día;mensuales existentesFree20/Standard100/Gym+Clínica0ilimitado. IndividualStarter1/Pro5 y79MXN separados. Sin inventar impuestos,gracia,dispositivos,retención o precios.

PostgreSQLQA17.11 en127.0.0.1:55483,datadir propio,appNOSUPER/NOBYPASS/no propietaria;sin initdb/cambios5432. Tres residuosUUID no atribuidos se conservan. R21scan41708e5:3028archivos/2clasificados/0pendientes sólo en esa fuente;scan nuevoHEAD pendiente. Diario/sesionesR14/R25/retención,dictámenes clínico/legal,pilotos y criterios restantes del registro continúan;no se cierran con una suite parcial.

Siguiente:cerrar revisión CI y auditoría imagen candidata;reconstruir desktop corregido en ventana de memoria;terminar29 aislado y someterlo a seguridad/QA;medir200HTTP PostgreSQL tras coordinar pausa backend. Continuar los demás criterios sin operación externa ni nuevas decisiones comerciales.
''', encoding='utf-8')
(RUN / 'ENTREGA.md').write_text('''# Entrega candidata

Implementación local en curso:104registros/92originales intactos. Rama implementation/20261018-execution,base daa25efbf51d154710bad625025b345fa9ec9252;runtime28 con historial/landing y corrección de test a753b2c. Gate amplio independiente2360pass/1skip en serial/n2,0fallos/errores. Sin release final ni despliegue. [Estado](ESTADO.md),[registro](TRAZABILIDAD.md),[validación](VALIDACION.md).

| Alcance | Evidencia local | Pendiente material |
| --- | --- | --- |
| Datos/RLS/restore/cuenta | Recuperación28,26tablas/20familias,restore28,21PG/marker28,seguridad/QA aceptados | Backup/staging/live;R12nuevo29 aislado sinAPI aceptada |
| Regresión actual | a753b2c:2360/1skip,serial588.64s,n2shuffle275.43s;667fuentes/89paquetes estables | SymlinkLinux,Actions/runtime imagen;CI historia/landing en revisión |
| Historial/oferta | Paginación50/200 ycursor firmado;SEC07/R29/UX-16verificados localmente | Medición200HTTP/EXPLAIN PG,SLO ycriteriosR34 restantes |
| Linux corregido | ecae:55PyPI OSV0/87OS Trivyrojo73IDs;bc365c1 construido conliblzma5u2 yOSV0 | ScanOS final/triage independiente/startup real/egress/PG/Redis;sin excepción de riesgo |
| Desktop | 7bdeZIPf57a964b/Setup25ed92b1 revisados51+27;entorno nuevo3.12.15/83PyPI OSV0 y45+97tests verdes | Reconstruir y revisar nuevo payload,instalación/upgrade/desinstalación/firma/nativeDLL |
| Archivos/diario/sesiones | Contratos25–28,lectores/worker/SDK/export/ACK/UI162VM aceptados por alcance | Legacy,destino durable real,reload/cross-tab/R12/borrado/retención |
| Catálogo/compras | Free10/1/10 y ledger atómico;individual separado | Sandbox,reconciliaciónlegacy/transiciónworkers y demásR01 |
| R21 | Scan41708e5:3028fuentes/2clasificados/0restantes | Nuevo scan exacto delcandidato completo;sin ampliación deexcepciones |

El primer amplio dd987 falló2tests que esperaban el HTMLcheckout retirado;se conservaron originales y se corrigió sólo la aserción vecina,con20focales y ambos amplios verdes. No runtime modificado ni casos perdidos. Los2064/1813 anteriores quedan históricos y no se suman al2360.

Artefactos desktop7bde30b:ZIP122492985bytes SHA256f57a964b11bf547f25e1883b12519516ac513dcd521c2e3306916f80c9779161;Setup89965414bytes SHA25625ed92b1a29b0675a1eecc15dc10a4432ed1046fb7734631ec828164f055d06d. Conservados conPython3.12.13. Preparar3.12.15 no los corrige;no nuevoSetup aún.

Antes de operación externa siguen pendientes candidato exacto completo,digests/config sin secretos,migraciones/backup/restore,transición de workers,rollback yobservación. Migración26 exige drenar workers antiguos. No push,PR,Railway,cargos,mensajes o contactos reales. Dictámenes legales/clínicos ypilotos no se sustituyen con agentes ni resultados sintéticos.
''', encoding='utf-8')
append('VALIDACION.md', '''## Checkpoint105: gate amplio actual y correcciones de runtime

[Aceptación independiente a753b2c](evidence/qa-integrated28-history-landing-postfix-20261019/final-summary.json):2360passed/1skip,serial588.64s y n2shuffle20261018/275.43s.2361nodeids/resultados iguales;667fuentes/89paquetes idénticos en4fotos,4pipcheck0. TresSQLite readonly integrity ok/26tablas/diario/3camposrecovery. Cobertura100%líneas/ramas sólo nutrition_validation,food_catalog,profile_schemas.6mensajes de deprecación existentes iguales,8avisos n2 por imports repetidos. No nuevoPG/Actions/Linux/performance por este gate.

Originaldd987:2358pass/2fail/1skip;ambos fallos esperaban checkout HTML huérfano ya retirado. [Original](evidence/qa-integrated28-history-landing-20261019/serial-red-review.json) intacto. a753 modifica sólo esa aserción y exige ausencia/404 de rutas públicas;15nodosprevios/restomódulo AST idénticos,20dirigidas verdes. [Fix](evidence/landing-retirement-test-fix-20261019/summary.json). No tests excluidos ni runtime cambiado.

Linuxecae/abd:55inventariados reales/OSV0,pipcheck0. Trivy0.76.0 sobre87OS:exit1,166entradas/73IDs(67CVE+5TEMP+1DSA),sinignore. [Matriz73](evidence/linux-recovery28-image-abd559a/os-audit/triage-matrix/TRIAGE.md):21grupos;2alias del mismoXZfixu2,otros71abiertos. BackportsOpenSSL13 confirmados por fuentes primarias. Candidatobc365c1 sobreMAINa753:build0/900.985s/imagen99c846bd28b0;55PyPI OSV0 yúnico cambioOS liblzma5u1→u2. AuditoríaOS final/startup/independencia aún pendientes.

[Windows3.12.15](evidence/desktop31215-security-20261019/README.md):83paquetes OSV0,pipcheck0;45desktop+97packaging/entrypoints nativos sinfallos/errores/skips,dd987/576fuentes estables. Runtime extraído desdefuente oficialAstral inmutable conAPI/checksum iguales;sin firma acreditada. OpenSSL3.5.9/Expat2.8.5. No bundle/Setup nuevo ni auditoríaDLL nativa.

[R12v2](evidence/r12-contract-security-review-20261019/source.json) aceptado sólo paradiseño/autoría29 aislada. [Rootprototipo](evidence/r12-root-mechanism-review-20261019/review-summary.json):4criterios propios positivos y1rojo payload real;1error propio deharness corregido sólo paraesecriterio,original intacto. Autor informa55canónicos verdes traspayload/lockowner;no aceptación independiente29/API. CI57dba41 en revisión independiente,16inertes/13delta/23VM autor más negativos propios aún sin integración.
''')
append('CAMBIOS.md', '''## Checkpoint105: regresión integrada y candidatos separados

a753b2c corrige únicamente la aserción de un test vecino que esperaba checkout sinuso ya retirado;conserva15nodosAST previos yresto del módulo. Original2fallos preservado;20focales y ambos amplios2360/1skip verdes. No runtime modificado por elfix.

Contrato R12v2 documentado4d537e4/6b0dc01 y aceptado porseguridad para implementar29 aislado;productoMAIN sigue28. Nuevo runtimeLinux fijaCPython3.12.15,pip26.2.1 yliblzma5u2 porfuentes oficiales/digest/hash;build2 yPythonSCA verdes,OS/startup noaceptados todavía. Windows3.12.15 separado tiene83paquetes/OSV0 y45+97tests verdes;artefactosdesktop anteriores permanecen históricos,porreconstruir.
''')
append('RIESGOS.md', '''Checkpoint105: elgate amplio actual2360/1skip enserial/n2 acepta runtime28+historial/landing;la omisiónWindows de symlink requiereLinux.2fallos anteriores fueron unaaserción de test desactualizada trasretirarHTML sinuso yse conservan antes del fix a753.

SEC08 sigue abierto:LinuxPyPI55 verde no implicaOS verde;Trivy87 detectó73IDs/21grupos,sinignore ni excepción. Sólo2alias delmismo defectoliblzma5 tienenfixbinario trixie;restantes71no se descartan porausencia deservicio o comparación deversión. Candidatonuevo conu2 enscan. Windows3.12.15/83PyPI y142tests verdes noactualizanlosZIP/Setup3.12.13 históricos ni acreditanCVE deDLL. R12canónico29 corrige rojosdeprototipo,peroAPI/PDF/restore/seguridad independiente pendientes. NuevosRAW requieren scanexactoR21 posterior.
''')
append('CARGA_LOCAL.md', '''Checkpoint105: amplio2360/1skip no constituye carga. Continúa pendiente elensayo focal200HTTP C1/C5 sobre1000planes/limit50 yEXPLAIN ANALYZE BUFFERS dePostgreSQL. Se coordinará pausa de pruebas backend29 yventana de recursos;no se atribuirá mejorap95 a cambiardehost,TCG o contención. No repetir baseline1400 sin nueva incertidumbre;objetivos/otrosflujos/colas/RSS/entorno representativo siguenabiertos.
''')
subprocess.run([str(TEMP / 'metodobase-candidate-web-20261018/Scripts/python.exe'), '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=ROOT, check=True)
receipt.write_text(json.dumps({'checkpoint':105, 'head_before_docs':head, 'registry_rows':104, 'preserved_source_problem_exact_criteria':len(preserved), 'verified_evidence':verified, 'new_desktop_proof':'evidence/desktop31215-security-20261019/manifest.json', 'runtime_gate_head':'a753b2cdf61a91133bd58c3159b0b35e02167396', 'main_runtime_revision':28, 'r12_revision29_isolated_only':True, 'os_scan_not_green':True, 'no_new_desktop_artifact':True, 'no_external_mutation':True}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'head':head,'registry':104,'rehash':verified,'desktop_files':len(list(dest.rglob('*'))),'receipt':str(receipt)}))
