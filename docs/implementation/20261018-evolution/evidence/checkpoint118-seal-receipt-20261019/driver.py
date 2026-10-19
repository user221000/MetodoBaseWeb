"""Seal scoped MFA reviews, the UI composition and the nonreproducing pool diagnostic."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(r'F:\MetodoBaseWeb-execution-20261018')
RUN = ROOT / 'docs/implementation/20261018-evolution'
EV = RUN / 'evidence'
BASE = '4d2a828612d5fbc08c5fabafb4c179990cf19438'
SHA = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args, **kwargs: subprocess.check_output(['git', *args], cwd=ROOT, **kwargs)
assert git('rev-parse', 'HEAD').decode().strip() == BASE and not git('status', '--porcelain', '--untracked-files=no')


def scan(blob, name):
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])', blob):
        start = match.start()
        assert not (start >= 30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}', blob[start-30:start])), name
    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+', blob), name
    if name.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            seen = set()
            for member in archive.infolist():
                if member.is_dir():
                    continue
                path = PurePosixPath(member.filename)
                assert not path.is_absolute() and '..' not in path.parts and member.filename not in seen
                seen.add(member.filename)
                assert member.file_size < 50_000_000 and not member.filename.lower().endswith('.zip')
                scan(archive.read(member), name + '/' + member.filename)


raw = set()
reviews = [
    ('security-mfa31-full-independent-20261019', 'source.json', '1003e35ed656c7090bd06551db9756d7e413717535fbc5b5eb4c72f32735f50d'),
    ('security-mfa31-alias-primary-independent-20261019', 'source.json', 'bd83ad84910cfd2eb9d0dfaaefff566513132161ae266f278e8661ff7c7f337f'),
    ('security-mfa31-pg-independent-20261019', 'source.json', '25ade8a282b7937034adfbbe985b833d11e9012d09f077ad7b96cf5515399fbd'),
    ('security-mfa31-canonical-final-independent-20261019', 'source.json', '6836e3a3d5d560c3f3873d78f25cabb0e60febbe2af4992eb0061e1332f989e8'),
    ('security-mfa31-composition-static-independent-20261019', 'source.json', '8224d3f6a93b8dee2aef611a3e5d06d81df1a96d259a020272172887b9ed08e8'),
    ('qa-r34-holder-runtime-independent-20261019', 'manifest.json', 'c78b09fe0ab037811ea5e9c37631bf9ee4c248db854a7a78a72f7486d6f0debf'),
    ('mfa31-refinements-and-legacy-prepared-20261019', 'manifest.json', 'eb70c36b9129706ea66e354901105d2bd4cdab96b299882dfacb56b24f2bc72d'),
    ('prepared-wave118-20261019', 'manifest.json', 'f6f7708d6b1c919dab734a47e704b3609180d8d58c9fb90473930276aed1b2ca'),
]
for prefix, name, digest in reviews:
    source = EV / prefix / name
    assert SHA(source.read_bytes()) == digest, prefix
    document = json.loads(source.read_bytes())
    rows = document['files']
    if isinstance(rows, dict):
        rows = [{'path': key, **value} for key, value in rows.items()]
    for row in rows:
        path = source.parent / row.get('path', row.get('file', ''))
        assert path.resolve().is_relative_to(source.parent.resolve())
        blob = path.read_bytes()
        assert SHA(blob) == row['sha256'] and ('bytes' not in row or len(blob) == row['bytes']), path.name
        scan(blob, path.name)
        raw.add(path)
    assert (source.parent / '.gitattributes').read_bytes() == b'* -text\n'
    scan(source.read_bytes(), source.name)
    raw.update([source, source.parent / '.gitattributes'])

data = json.loads((RUN / 'TRAZABILIDAD.json').read_bytes())
keys = ['fuente', 'seccion', 'problema', 'criterio_exacto']
criteria = lambda value: {row['id']: {key: row[key] for key in keys} for row in value['requisitos']}
before = criteria(json.loads(git('show', BASE + ':docs/implementation/20261018-evolution/TRAZABILIDAD.json')))
assert criteria(data) == before and len(before) == 110
notes = {
    'R01': 'Seguridad acepta el delta de aliases de pago en440 mediante los mismos5casos inmutables, sin sumarlos como nuevos. La composición913 conserva los3productos de440 y el header unido. La adopción defixtures sensibles usa enrolamiento ygrants reales, sin bypass.',
    'R02': 'SEC13 corregido y aceptado enbackend440:6parent+4NULL estrictamente verdes; actor/OWNER requieren invitation_token IS NULL bajo los mismos locks. Composición913 sólo verificada estáticamente. No se afirma origen legítimo de estados ambiguos.',
    'R05': 'CI31 en implementación aislada desde913/da343, con histórico30 auténtico eea8 y23helpers inmutables. Current31 tendrá gates propios; no basta reejecutar30. AmpliaMAIN30 ya verde2597+1 por modo permanece sin cambios.',
    'R12': 'MFA UI compuesta en5e91115 sin conflictos:24fuentes producto/pruebas exactas087 y5productos backend exactos913. Ajuste de20literales en3archivos da343, sinlógica. Root74VM+14SSR/HTTP verdes; QA independiente actual pendiente.',
    'R13': 'AutorUI15grupos Chrome/12pantallas sinaxeAA enbloques nuevos, overflow nipageerrors sobre sufreeze. Primera captura decontraste era animación finita, conservada; etiquetasfor/id corregidas aparte. Rootreplay da343 no acredita navegador/accesibilidad independiente.',
    'R21': 'Los136blobs de entregaUI y3ZIP expandidos pasaron preflight sin tokens. Se distingue RAW/GitLF; primer guard de texto comparó CRLF conGitLF ydetuvo antes de escribir, corregido mediante OIDfiltrado ypreimágenes RAW/inversa exactas.',
    'R31': 'PrivacidadPRIMARY corregida en8b64 yrevisada en440 con20inmutables verdes. Pruebas RAW privadas yproyecciones SANITIZED explícitas preservadas. UI no persiste seed/kit/proof/grant; límites legacy de sesión ypolítica de conservación siguen abiertos.',
    'R32': 'Seguridad acepta BACKEND_SCOPED440:replays6+4+5+20 verdes, no sumados como casos nuevos;4PG propios pertenecen sólo56. Composición913 revisada estáticamente. UIda343 compuesta, autor74VM/4puentes/15gruposChrome yroot74VM+14SSR/HTTP; QA/CI31/restore independiente yavisos/custodia/configuración real siguen pendientes.',
    'R34': 'Diagnóstico propio sobreMAIN4d2:16HTTP200 conpool1/overflow0 ytimeout diagnóstico2s frente30s original;0timeouts.9snapshots incluían6carreras deobservación y3solapamientos reales, todosliberados naturalmente. No causa histórica nifix niSLO demostrado.3UUID cerradasexactas,8804sinlistener;objetivos consultados alusuario.',
    'SEC12': 'Mismo driver5alias final440 verde. APIaliases sóloapi.app yWebcanónicos/alias404 conalcances separados. Revisión independiente aceptada enbackendaislado; integracióncurrent31 yregresión aún pendientes.',
    'SEC13': 'Final440aceptado acotadamente:6parent+4NULLliteral verdes. Los4PG de56 sonunhitoanterior, no reatribuidos440. Composición913 conserva3productos exactos yheader66e652 coninversaAST independiente; aceptación deUI/restore31 pendiente.',
}
refs = {
    'R01': ['security-mfa31-alias-primary-independent-20261019/source.json'],
    'R02': ['security-mfa31-canonical-final-independent-20261019/source.json'],
    'R05': ['prepared-wave118-20261019/receipt.json'],
    'R12': ['prepared-wave118-20261019/receipt.json'],
    'R13': ['prepared-wave118-20261019/ui-author-report.md'],
    'R21': ['prepared-wave118-20261019/UI-preflight/receipt.json'],
    'R31': ['security-mfa31-full-independent-20261019/source.json'],
    'R32': ['security-mfa31-canonical-final-independent-20261019/source.json', 'security-mfa31-pg-independent-20261019/source.json', 'prepared-wave118-20261019/UI-copy-check/summary.json'],
    'R34': ['qa-r34-holder-runtime-independent-20261019/final-summary.json'],
    'SEC12': ['security-mfa31-alias-primary-independent-20261019/source.json'],
    'SEC13': ['security-mfa31-canonical-final-independent-20261019/source.json', 'security-mfa31-composition-static-independent-20261019/source.json'],
}
for row in data['requisitos']:
    if row['id'] in notes:
        row['observaciones'].append('Checkpoint118: ' + notes[row['id']])
    for name in refs.get(row['id'], []):
        ref = 'evidence/' + name
        if ref not in row['evidencia']:
            row['evidencia'].append(ref)
assert criteria(data) == before
(RUN / 'TRAZABILIDAD.json').write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())
(RUN / 'ESTADO.md').write_text('''# Estado de ejecución 20261018-evolution

Checkpoint 118 local. El registro conserva 110 requisitos: los 92 identificadores originales y 18 hallazgos nuevos. Sus 110 criterios permanecen exactos. La rama principal de ejecución continúa en esquema30, con R12, R23, SEC11 y R24 parcial integrados. El workspace original `F:/MetodoBaseWeb-main` permanece intacto. No hubo push, PR, despliegue, cargos ni comunicaciones reales.

La regresión amplia de esa fuente sigue verde: 2597 aprobadas y una omisión conocida de symlinks en Windows por modo, tanto serial con cobertura como con dos workers y orden mezclado. Se conservaron los 2492 casos anteriores y 106 adicionales. Los tres módulos exigidos alcanzaron 100% de líneas y ramas. Ese resultado no acredita Linux, Actions, imagen, PostgreSQL ni un SLO. [Resultado](evidence/main-r23-r24-regression-20261019/summary.json).

MFA31 sigue en una candidata aislada. Seguridad aceptó el backend440 con alcance acotado: los mismos conjuntos de 6, 4, 5 y 20 casos quedaron verdes; los replays no son casos nuevos. Sus cuatro controles PostgreSQL propios pertenecen al freeze56, no al440. Una revisión estática adicional confirmó la composición913 y la conservación de los contratos de ambos padres. [Aceptación](evidence/security-mfa31-canonical-final-independent-20261019/source.json), [alcance PG](evidence/security-mfa31-pg-independent-20261019/source.json), [composición](evidence/security-mfa31-composition-static-independent-20261019/source.json).

La UI087 se compuso sin conflictos en5e91115: trece productos y once archivos de pruebas iguales al autor, con cinco productos backend intactos. La candidata da34304aaf9066f45c6fc854cfd81d00e2fbc581 añade únicamente veinte ajustes de texto en tres archivos para explicar la seguridad de la cuenta. El replay de root pasó 74 comprobaciones VM y 14 de páginas/HTTP; 679 archivos y 89 paquetes permanecieron estables. El autor conserva por separado sus cuatro puentes ASGI y quince grupos de navegador con doce pantallas. QA está revisando la integración de forma independiente. [Composición y replay](evidence/prepared-wave118-20261019/receipt.json).

Un diagnóstico inicial sobre913 terminó con 72 aprobadas y veinte fallos de pruebas de invitación, detenido por maxfail20. Backend está adaptando fixtures mediante enrolamiento, TOTP y grants reales. Tres expectativas404 pasan legítimamente a403 por la precedencia de MFA, conservando la misma denegación para un recurso ajeno o inexistente. Las preimágenes y comprobaciones de negocio se conservan; la adaptación aún no está integrada. CI31 está en implementación: ejecutará los controles históricos sobre fuente30 auténtica y añadirá contratos de integración sobre31 real. No se fabricarán marcadores antiguos desde modelos nuevos.

R34 sigue abierto. QA ejecutó dieciséis solicitudes naturales sobre esquema30 con pool1 y overflow0: todas respondieron200 y no hubo timeout. Nueve snapshots comprendían seis carreras de observación y tres solapamientos reales que se liberaron naturalmente. Esto no reproduce ni explica el timeout histórico. Las tres bases creadas por los intentos quedaron eliminadas de forma exacta y el puerto8804 cerrado. Los objetivos de volumen y p95 se consultaron al usuario. [Diagnóstico](evidence/qa-r34-holder-runtime-independent-20261019/final-summary.json).

R23 y R24 continúan parciales por responsables/eventos persistidos y por sustituciones/R33 y conservación/R31. MFA aún necesita QA, CI31, restauración independiente, avisos por cambios de factor, custodia de claves y configuración real. La política de países y conservación sigue pendiente; no se activaron purgas nuevas. Los pilotos y dictámenes requieren participación real autorizada.

Linux conserva el arranque rojo42501 anterior a web en la imagen99c. El parche Docker/ExpatM2 sólo tiene aceptación estática: falta compilación, imports, linkage, SCA y arranque con ProductionSettings y rol restringido. Siguen abiertos71 identificadores OS. QEMU y los servicios de esa ventana permanecen cerrados. Desktop sigue soportado; faltan instalación, firma e inventario DLL exhaustivo.

Free mantiene lo aprobado: diez clientes activos, un plan por cliente al día y diez planes totales por gimnasio al día. Los límites mensuales y el producto individual permanecen separados según el catálogo acordado.

Siguiente acción: terminar la revisión independiente de MFA/UI y la adopción de fixtures, completar CI31 sin alterar históricos, integrar y ejecutar sus gates. Después reconstruir la imagen Linux y continuar las capacidades de producto y privacidad pendientes. [Registro](TRAZABILIDAD.md).
''', encoding='utf8')
(RUN / 'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint118:110 requisitos,92 identificadores originales y110 criterios intactos. La rama de ejecución continúa con esquema30; su última regresión amplia pasó2597 casos y una omisión Windows por modo serial/cobertura y dos workers con orden mezclado.

MFA31 está en la candidata aislada da34304aaf9066f45c6fc854cfd81d00e2fbc581. El backend440 tiene aceptación de seguridad acotada; la UI está compuesta y pasó el replay de74VM y14SSR/HTTP. QA y CI31 siguen en curso. No se atribuyen a esa candidata las pruebas de otro freeze ni se declara aceptación integral.

R34 completó un diagnóstico natural de16 solicitudes200 sin reproducir el timeout histórico; no demuestra un SLO ni una corrección del pool. Linux/Expat sigue pendiente de build y validación dinámica, con71 identificadores OS abiertos. Desktop continúa soportado. Free:10 clientes,1 plan por cliente al día y10 totales por gimnasio al día.

No es una entrega final. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [validación](VALIDACION.md), [riesgos](RIESGOS.md) y [registro](TRAZABILIDAD.md).
''', encoding='utf8')
appendices = {
    'VALIDACION.md': 'Seguridad: backend440 aceptado con los mismos replays6+4+5+20; PG4 pertenece sólo56 y composición913 sólo tiene peer estático. Autor UI087 conserva15 grupos/12 pantallas; root da343 pasó74VM+14SSR/HTTP,679 fuentes/89 paquetes estables. R34:16 solicitudes200,0 timeout,9 snapshots de los cuales3 son solapamientos efectivos;3UUID cerradas y8804 sin listener. No capacidad, SLO, Actions, Linux ni proveedor real inferidos.',
    'CAMBIOS.md': 'Se sellan revisiones independientes de MFA, su composición UI aislada y el diagnóstico del pool. La rama principal no cambia producto ni esquema. En la candidata da343 se ajustan veinte textos en tres archivos; la inversa reconstruye exactamente los bytes anteriores. Las pruebas de invitación se adaptan con MFA real y tres expectativas de status cambian por una precedencia deliberada de autorización, documentada y aún sin integrar.',
    'RIESGOS.md': 'MFA no está aceptado integralmente: faltan QA de integración/UI, CI31 y restauración independiente, avisos, custodia/rotación de claves y configuración real de servicios. No existe recuperación administrativa simulada ante pérdida de todos los factores. R34 no reprodujo el timeout, por lo que ampliar el pool no acredita solución. Continúan los71 IDs OS, la política de privacidad y los pilotos externos.',
    'DECISIONES.md': 'Conservar separados los freezes56,440,913,087 yda343 y sus alcances. Los replays no se suman como casos nuevos. Los históricos se ejecutan con su fuente auténtica y current31 tendrá contratos propios. Se acepta documentar la nueva precedencia403 de MFA para recursos ajenos o inexistentes, preservando la opacidad, la denegación y las demás aserciones; no se modifica producto para eludir el control. Objetivos R34 consultados y pendientes.',
}
for name, text in appendices.items():
    with (RUN / name).open('ab') as output:
        output.write(('\n\n## Checkpoint 118\n\n' + text + '\n').encode())
subprocess.run([sys.executable, '-X', 'utf8', 'scripts/implementation_registry.py', '--render', '--check'], cwd=ROOT, check=True, capture_output=True)
assert criteria(json.loads((RUN / 'TRAZABILIDAD.json').read_bytes())) == before
seal = EV / 'checkpoint118-seal-receipt-20261019'
seal.mkdir(exist_ok=False)
(seal / '.gitattributes').write_bytes(b'* -text\n')
(seal / 'driver.py').write_bytes(Path(__file__).read_bytes())
review = {'base': BASE, 'registry': 110, 'previous_criteria_exact': 110, 'new_ids': [], 'main_product_changed': False,
          'original_freezes_unchanged': True, 'authenticated_manifests': reviews,
          'raw_files': {p.relative_to(ROOT).as_posix(): {'bytes': p.stat().st_size, 'sha256': SHA(p.read_bytes())} for p in sorted(raw)}}
(seal / 'receipt.json').write_bytes((json.dumps(review, indent=2) + '\n').encode())
raw.update(p for p in seal.iterdir() if p.is_file())
names = sorted(p.relative_to(ROOT).as_posix() for p in raw)
docs = [(RUN / n).relative_to(ROOT).as_posix() for n in ['ESTADO.md', 'ENTREGA.md', 'VALIDACION.md', 'CAMBIOS.md', 'RIESGOS.md', 'DECISIONES.md', 'TRAZABILIDAD.json', 'TRAZABILIDAD.md']]
for start in range(0, len(names), 25):
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'add', '-f', '--', *names[start:start+25]], cwd=ROOT, check=True, capture_output=True)
subprocess.run(['git', 'add', '--', *docs], cwd=ROOT, check=True, capture_output=True)
buffer = git('cat-file', '--batch', input=''.join(':' + name + '\n' for name in names).encode())
cursor = 0
for name in names:
    end = buffer.index(b'\n', cursor)
    header = buffer[cursor:end].split()
    assert header[1] == b'blob'
    size = int(header[2])
    cursor = end + 1
    assert buffer[cursor:cursor+size] == (ROOT / name).read_bytes(), name
    cursor += size + 1
assert cursor == len(buffer)
assert set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')[:-1]) == set(names + docs)
subprocess.run(['git', 'diff', '--cached', '--check', '--', *docs], cwd=ROOT, check=True, capture_output=True)
subprocess.run(['git', 'commit', '-m', 'Record scoped MFA acceptance, composed UI and bounded pool diagnostic'], cwd=ROOT, check=True, capture_output=True)
assert not git('status', '--porcelain', '--untracked-files=no')
print(json.dumps({'head': git('rev-parse', 'HEAD').decode().strip(), 'RAW_authenticated': len(names),
                  'registry': 110, 'previous_criteria_exact': 110, 'main_product_changed': False}))
