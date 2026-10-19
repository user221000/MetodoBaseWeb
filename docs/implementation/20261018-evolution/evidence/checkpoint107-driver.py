"""Integrate independently sealed review evidence only; preserve RAW bytes."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('F:/MetodoBaseWeb-execution-20261018')
RUN = ROOT/'docs/implementation/20261018-evolution'
EV = RUN/'evidence'
PYTHON = 'C:/Users/Consu/AppData/Local/Temp/metodobase-candidate-web-20261018/Scripts/python.exe'
BASE = 'b59c99f04c5bb164ec54a467c866bcca21a9e328'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def git(*args, **kwargs):
    return subprocess.check_output(['git', *args], cwd=ROOT, **kwargs)

assert git('rev-parse', 'HEAD', text=True).strip() == BASE
assert not git('status', '--porcelain', '--untracked-files=no')
seals = {
    'desktop31215-independent-20261019': {
        'final-summary.json': '56dff578b1954a3e7c21582597b5082d7ddd6cd41820f7ea7cd4c5afbf76530c',
        'final-manifest.json': '043c536ee008bd9159d726986f97bc2706a24aadf27319c1fb8d846b0be9e7c6',
    },
    'qa-r12-core29-independent-20261019': {
        'final-summary.json': '5f9f299e0d6832df92473a16ebe4df8fbe18e3ed277eaedcac2f37901dd8ddb3',
        'final-manifest.json': 'c4a0e8f37d9ec3780a497d3a58383dc4c86a277fc44decf3893c35d85203c823',
    },
    'security-r12-core29-independent-20261019': {
        'source.json': 'f02414062e52b8d0bb12475270b4a96a749bc6924bfb0deb0a9abeb70ee6a767',
        'review.md': '897c6f6e7e2431af170bbbbdef08d43fe12085eeee358b59190c2a9d4bb3f201',
        'r12_core29_security_driver_frozen.py': 'a51dde94ef7e2a7197c063ceb0b37c95d030c6cf05279bc8f3e0b2ad237fffdb',
    },
    'security-r12-core29-v2-independent-20261019': {
        'source.json': '5a4a12d5522ed68c845005c2c6b4dae8c63ddccc21090c7a437bacef11cbe543',
        'review.md': 'c77e9f44b18e1dff9182082f904130a4889758050c64105be2d9f21481c80150',
        'results.json': 'd43382935764b6974ccef331b86d86180148ba6d01f97b0a1f203f628edf241b',
    },
}
raw = []
receipts = {}
for folder, expected in seals.items():
    directory = EV/folder
    for name, digest in expected.items():
        assert sha((directory/name).read_bytes()) == digest, (folder, name)
    manifest = directory/'final-manifest.json'
    if manifest.exists():
        data = json.loads(manifest.read_bytes())
        assert len(data['files']) == data['file_count']
        for name, detail in data['files'].items():
            content = (directory/name).read_bytes()
            assert len(content) == detail['bytes'] and sha(content) == detail['sha256'], (folder, name)
    originals = sorted(p for p in directory.rglob('*') if p.is_file())
    receipts[folder] = {p.relative_to(directory).as_posix(): {'bytes':p.stat().st_size, 'sha256':sha(p.read_bytes())} for p in originals}
    attrs = directory/'.gitattributes'
    assert not attrs.exists()
    attrs.write_bytes(b'* -text\n')
    raw.extend(originals+[attrs])

data = json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
old = {r['id']:{key:r[key] for key in ('fuente','seccion','problema','criterio_exacto')} for r in data['requisitos']}
assert len(old) == 104
notes = {
    'R12': ('Núcleo V1 ad712: QA95 verdes y seguridad18/21 con tres fallos reales; originales conservados. Corrección selectiva V2 1aac: el mismo driver independiente21/21 verde, fuentes3354 y paquetes estables, UUID propio cerrado. Se acepta sólo ese delta; no API, casts/restore ni integración29. Front consumer y restore del autor continúan aislados.', ['qa-r12-core29-independent-20261019/final-summary.json','security-r12-core29-independent-20261019/source.json','security-r12-core29-v2-independent-20261019/source.json']),
    'UX-07': ('R12 tiene consumer local de tres páginas y exportación de vínculos por componer. La aceptación de núcleo V2 no acredita recorrido HTTP29 ni entrega de correo real.', ['security-r12-core29-v2-independent-20261019/source.json']),
    'R18': ('Desktop66 con Python3.12.15: QA independiente93 controles verdes (51 bundle,27 payload Inno,15 propios). ZIP4966896c y Setup5651f418,1215 archivos idénticos,4433 fuentes y83 paquetes estables. Sin instalación/upgrade/uninstall/firma o evaluación exhaustiva de DLL nativas. Linux mantiene71 IDs OS abiertos.', ['desktop31215-independent-20261019/final-summary.json']),
    'B21': ('QA independiente del nuevo artefacto desktop3.12.15 aceptada en alcance bundle/ZIP/payload/runtime93 controles. No sustituye validación de CVE de librerías nativas ni instalación.', ['desktop31215-independent-20261019/final-summary.json']),
    'QA-10': ('Se preservan los scans originales y se vincula inventario83 al bundle desktop sin repetir SCA. La revisión de artefacto93 es acotada y no cierra LinuxOS71 ni el scan final de secretos de fuente actual.', ['desktop31215-independent-20261019/final-summary.json']),
    'OPS07': ('Nuevo ZIP/Setup desktop de fuente66 revisado independientemente:93 verdes y payload exacto1215; sin ejecutar Setup ni cambiar HKCU. Artefactos históricos3.12.13 permanecen conservados.', ['desktop31215-independent-20261019/final-summary.json']),
    'SEC08': ('Runtime desktop oficial Astral3.12.15/OpenSSL3.5.9/Expat2.8.5 verificado contra archivo autenticado; Qt6.8.3. El inventario83 coincide con OSV original0matches. QA no afirma cobertura exhaustiva de DLL ni cierre de71 IDs OS Linux.', ['desktop31215-independent-20261019/final-summary.json']),
}
for row in data['requisitos']:
    if row['id'] in notes:
        note, evidence = notes[row['id']]
        row['observaciones'].append('Checkpoint107: '+note)
        for value in evidence:
            path = 'docs/implementation/20261018-evolution/evidence/'+value
            if path not in row['evidencia']:
                row['evidencia'].append(path)
    assert {key:row[key] for key in old[row['id']]} == old[row['id']]
(RUN/'TRAZABILIDAD.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

state = '''# Estado de ejecución 20261018-evolution

Checkpoint 107: implementación local en curso, 104 registros con los 92 identificadores originales y sus criterios intactos. Original F:/MetodoBaseWeb-main conservado. Rama implementation/20261018-execution en F:/MetodoBaseWeb-execution-20261018, base daa25efbf51d154710bad625025b345fa9ec9252. Sin push, PR, despliegue, cargos o comunicaciones reales.

La composición integrada continúa en esquema28: recuperación, historial paginado y landing. Regresión amplia independiente sobre a753b2c: 2360 pruebas aprobadas y una omisión conocida de Windows, tanto en serie como n2 mezclado; mismos2361 IDs/resultados, fuentes y dependencias estables. No se atribuye esa ejecución al nuevo29 ni a un runtime Linux. CIhistory/landing52af400 y cuatro correcciones Docker hasta66d9dec están integradas tras revisión independiente. [Validación](VALIDACION.md), [registro](TRAZABILIDAD.md).

Desktop soportado: nuevos artefactos desde66d9dec con Python3.12.15, OpenSSL3.5.9, Expat2.8.5 y Qt6.8.3. QA independiente aceptó93 controles:51bundle/ZIP,27payload de Inno y15 propios. Los1215 archivos coinciden y los83 paquetes/fuentes4433 permanecen estables. ZIP4966896c y Setup5651f418 conservados fuera de Git. Sin ejecutar Setup, instalación, upgrade, desinstalación ni firma; sin afirmar análisis completo de CVE de DLL. Artefactos anteriores3.12.13 conservados. [Aceptación](evidence/desktop31215-independent-20261019/final-summary.json).

R12 continúa aislado. Núcleo V1 ad712 tuvo95 pruebas de QA verdes, pero seguridad reprodujo tres defectos reales de permisos/NULL antes de commit; por eso fue rechazado. Corrección V2 1aac pasó el mismo driver independiente21/21, con3354 fuentes y paquetes estables y UUID propio cerrado. Esa aceptación cubre sólo el delta canónico y los checks totales, sin API, restore, nuevos casts o integración29. El autor trabaja en restore29 y API; frontend prepara los tres consumidores y la composición de privacidad/exportación. Contrato v2 aceptado, veinte políticas y targets22–28 históricos sin reinterpretar. [V1](evidence/security-r12-core29-independent-20261019/source.json), [V2](evidence/security-r12-core29-v2-independent-20261019/source.json), [QA](evidence/qa-r12-core29-independent-20261019/final-summary.json).

R34: historial por defecto50/máximo200 y cursor firmado aceptados. Ensayo posterior de200 HTTP/200 ACK con50 resúmenes/8161bytes por respuesta: p95 descriptivo C1 16.2312ms y C5 144.2441ms, sin causalidad ni SLO. EXPLAIN muestra1000 filas. Índice y lector UNION en rama aislada reducen a51 en corpus fechado y pasan96 regresiones; migración30, mezcla con NULL y revisión independiente siguen pendientes. No están integrados. [Carga](CARGA_LOCAL.md).

Linux: imagen99c846bd28b0 de fuente bc365c1 (a753 más cuatro fixes Docker) construida en QEMU propio2vCPU/2GiB. Python3.12.15/pip26.2.1,55 paquetes PyPI con OSV0;87 paquetes OS, sólo liblzma5 cambió de u1 a u2. Trivy final164 entradas/71 IDs abiertos; dos alias XZ desaparecieron y no hubo entradas nuevas. Seguridad aceptó sólo el delta Docker, sin excepción de riesgo ni cierre OS. QEMU se apagó ordenadamente antes del ensayoPG/desktop; el siguiente lote prepara inventario nativo y arranque de producto con red acotada, sin atribuir ejecución todavía.

Free confirmado:10 clientes activos, un plan por cliente al día y10 planes totales diarios por gimnasio. Mensuales existentes Free20/Standard100/Gym+Clínica0 ilimitado; individual Starter1/Pro5 y79MXN, separado. No se inventaron impuestos, gracia, dispositivos, retención o precios.

PostgreSQL QA17.11 loopback55483, rol app NOSUPER/NOBYPASS/no propietario, datos sintéticos y UUID propios. Tres residuos previos sin atribución conservados. R21 sólo cubre fuente41708e5/3028 archivos; el scan exacto final aún falta. Permanecen abiertos otros criterios de diario, sesiones, R14/R25, retención, dictámenes humanos y pilotos del registro.

Siguiente: completar restore/API29 y consumidores con revisión independiente; verificar e integrar30 después del29 aceptado; ejecutar el runtime Linux y resolver el gateOS; continuar los demás criterios. Evidencia histórica por commit permanece en Git y en los manifiestos originales.
'''
(RUN/'ESTADO.md').write_text(state, encoding='utf-8')
delivery = '''# Entrega candidata

Checkpoint107: trabajo local en curso sobre104 registros,92 originales intactos. Esquema integrado28, sin release final ni despliegue. [Estado](ESTADO.md), [registro](TRAZABILIDAD.md), [validación](VALIDACION.md).

| Alcance | Resultado verificable | Pendiente material |
| --- | --- | --- |
| Regresión integrada28 | a753:2360 aprobadas/1skip conocido en serial y n2, mismos IDs y fuentes estables; CIhistory/landing integrado | Composición29/30, runtimeLinux y Actions |
| Datos/cuenta | Recuperación28,26tablas/20familiasRLS, restore28 y gates aceptados | R12API/restore/UI29 todavía aislados; staging/live |
| R12 | V1rechazado por3 negativos; coreV2 1aac revisado con mismo21/21verde | Casts/restore, API/PDF/privacidad, UI y revisión de composición29 |
| Historial/oferta | Historial50/200, cursorHMAC, landing y200HTTP medidos | Índice/lector30 aislados; SLO y demásR34 |
| Linux | Docker fixes aceptados; imagen99c846bd28b0,55PyPI OSV0;71IDsOS abiertos | Inventario nativo, arranque real/egress/PG/Redis, resolver gateOS |
| Desktop | Python3.12.15; ZIP/Setup66 aceptados93 controles y1215 archivos idénticos | Setup sin ejecutar; instalación/upgrade/uninstall/firma y análisis nativo |
| Privacidad/sesiones | Contratos y gates anteriores conservados | Composición exportvínculos, reload/cross-tab, R14/R25/borrado/retención |
| Secretos | Scan41708e5 conservado,3028archivos y0pendientes en esa fuente | Scan exacto del candidato final |

ZIP actual: F:/mb-d31215-20261019/dist/MetodoBase_v2.0.0_win32.zip,122441614bytes, SHA2564966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353. Setup: C:/Users/Consu/AppData/Local/Temp/metodobase-desktop31215-build66-20261019/inno/compiled/MetodoBaseSetup_v2.0.0.exe,89973261bytes, SHA2565651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363. [Aceptación independiente](evidence/desktop31215-independent-20261019/final-summary.json). Paquetes anteriores conservados; no se ejecutó el instalador.

La aceptación del núcleo29 y la del paquete desktop tienen alcances separados. No acreditan API29, runtimeLinux, cumplimiento clínico/legal, pilotos o un despliegue. Antes de operación externa se completará candidato exacto, configuración sin secretos, migraciones/backup/restore, transición de workers, rollback y observación. No push,PR,Railway,cargos,mensajes o contactos reales autorizados.
'''
(RUN/'ENTREGA.md').write_text(delivery, encoding='utf-8')
paragraph = '''Checkpoint107: selladas la revisión independiente desktop66 (93 controles verdes, payload1215 exacto, Python3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3; sin ejecutar Setup) y las revisiones R12V1/V2. QA95 de V1 no cerró sus tres fallos de seguridad; V2 1aac pasó los mismos21 criterios independientes, sin cambiar el driver. Fuentes y paquetes estables; bases propias cerradas. Aceptación limitada al coreV2, sin casts/restore/API ni integración29. Los RAW y manifiestos originales permanecen exactos y se añaden atributos binarios sólo a estas nuevas carpetas para conservarlos en Git.'''
for name in ('VALIDACION.md', 'CAMBIOS.md', 'RIESGOS.md', 'DECISIONES.md'):
    path = RUN/name
    path.write_text(path.read_text(encoding='utf-8').rstrip()+'\n\n'+paragraph+'\n', encoding='utf-8')
subprocess.run([PYTHON, '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=ROOT, check=True)
driver = EV/'checkpoint107-driver.py'
assert not driver.exists()
shutil.copyfile(__file__, driver)
raw.append(driver)
receipt = EV/'checkpoint107-review.json'
assert not receipt.exists()
receipt.write_text(json.dumps({'base_commit': BASE, 'kind':'evidence_and_current_prose_only', 'original_criteria_preserved':104,
    'author_seals_verified':seals, 'RAW_original_files':receipts,
    'coordinator_added_attributes_outside_author_manifests':'* -text in exactly four new proof directories',
    'R12_V1_original_reds_preserved':True, 'core_V2_ACCEPTANCE_scope':'Same21 local synthetic SQL criteria; API/restore/casts/integration excluded',
    'desktop93_scope':'Unsigned bundle/ZIP/compiled payload/runtime only; no Setup execution', 'production_mutation':False}, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
raw.append(receipt)
docs = [RUN/name for name in ('ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md')]
names = sorted({p.relative_to(ROOT).as_posix() for p in raw+docs})
for start in range(0, len(names), 25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]], cwd=ROOT, check=True, capture_output=True)
for folder in seals:
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',(EV/folder).relative_to(ROOT).as_posix()], cwd=ROOT, check=True, capture_output=True)
check = git('diff','--cached','--check','--',*[p.relative_to(ROOT).as_posix() for p in docs], stderr=subprocess.STDOUT)
assert not check, check
raw_names = sorted(p.relative_to(ROOT).as_posix() for p in raw)
buffer = git('cat-file','--batch', input=''.join(':'+name+'\n' for name in raw_names).encode())
cursor = 0
for name in raw_names:
    end = buffer.index(b'\n', cursor)
    parts = buffer[cursor:end].split()
    assert parts[1] == b'blob', (name, parts)
    size = int(parts[2])
    cursor = end+1
    assert buffer[cursor:cursor+size] == (ROOT/name).read_bytes(), name
    cursor += size+1
assert cursor == len(buffer)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]) == set(names)
subprocess.run(['git','commit','-m','Record desktop93 and independent R12 core V1/V2 reviews'], cwd=ROOT, check=True)
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(), 'RAW_git_blobs_byte_identical':len(raw_names), 'docs':len(docs), 'registry':104, 'product_changes':False}))
