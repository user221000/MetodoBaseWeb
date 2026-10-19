"""Record peer fixture acceptance and preserve the rejected CI preimage."""
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
RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence'
TMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
BASE='a79b4b0640b586f3ca24d510bc29a73e841160f2'
SHA=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args,**kw:subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT,**kw)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((TMP/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
raw=set()
reviews=[
 ('qa-mfa31-fixture-peer-independent-20261019','b0d947c463f2b87ccd6da782d6653314a9a812e56eae638bd53307ef9c2a01ff'),
 ('mfa31-ci-e0-offline-20261019','d9e39537dbd89395be3770ca2aec4565e50d94cdf2bfa3627b4a3ce684901feb'),
]
for prefix,digest in reviews:
    parent=EV/prefix;manifest=parent/'manifest.json'
    assert SHA(manifest.read_bytes())==digest
    rows=json.loads(manifest.read_bytes())['files']
    if isinstance(rows,dict):rows=[{'path':name,**meta} for name,meta in rows.items()]
    for row in rows:
        assert ('sha256' in row)!=('SHA256' in row)
        path=parent/row['path'];blob=path.read_bytes()
        assert path.resolve().is_relative_to(parent.resolve()) and len(blob)==row['bytes']
        assert SHA(blob)==row.get('sha256',row.get('SHA256'))
        scan(blob,path.name);raw.add(path)
    assert (parent/'.gitattributes').read_text(encoding='ascii').strip()=='* -text'
    raw.update([manifest,parent/'.gitattributes'])
seal=EV/'checkpoint120-seal-receipt-20261019';seal.mkdir(exist_ok=False)
(seal/'.gitattributes').write_bytes(b'* -text\n')
(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
for p in (TMP/'metodobase-ci31-compose-20261019').iterdir():
    if p.is_file():
        scan(p.read_bytes(),p.name)
        (seal/('candidate-'+p.name)).write_bytes(p.read_bytes())

data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda d:{r['id']:{k:r[k] for k in fields} for r in d['requisitos']}
before=criteria(json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json')))
assert criteria(data)==before and len(before)==112
notes={
 'R05':'CI e0 congelado y preservado como preimagen sin aceptación. Offline: histórico auténtico573 FULL+348 VM; actual31 ejecutó31 módulos/494 comprobaciones, con alcance incompleto por omisión del módulo snapshot25 (18 repeticiones y7 casos nuevos). QA revisa además la frontera CLI y confirmó que el marcador de rol era opcional. Sin173PG ni Actions. La composición aislada bd348 cambia33 archivos CI/tests, conserva23 helpers y deja los productos4a exactos.',
 'R12':'QA aceptó la nueva fixture de acompañantes:16 callbacks heredados exactos y16/16 sobre módulosR24 reales; parser compartido exit0. No es evidencia HTTP ni Chrome adicional.',
 'R32':'QA peer aceptó la adopciónDAB:24/24 SQLite (20 replays y4 propios) y16/16 VM;109/110 aserciones originales de team/entitlement exactas, única404→403 aprobada,66 diary intactas y conftest global913 exacto. Mantiene pendiente regresión amplia31/CI/imagen y los aspectos operativos deMFA.',
 'QA-12':'Revisión independiente de fixture aceptada:16/16 con módulos reales y callbacks exactos. CI e0 omite snapshotR24; sus gates siguen sin aceptación. El históricoeea8 rojo y el contraste causal permanecen intactos.',
}
refs={
 'R05':['mfa31-ci-e0-offline-20261019/manifest.json','checkpoint120-seal-receipt-20261019/candidate-receipt.json'],
 'R12':['qa-mfa31-fixture-peer-independent-20261019/phase-summary.json'],
 'R32':['qa-mfa31-fixture-peer-independent-20261019/phase-summary.json'],
 'QA-12':['qa-mfa31-fixture-peer-independent-20261019/phase-summary.json','mfa31-ci-e0-offline-20261019/manifest.json'],
}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint120: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        ref='evidence/'+ref
        if ref not in row['evidencia']:row['evidencia'].append(ref)
(RUN/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
(RUN/'ESTADO.md').write_text('''# Estado de ejecución 20261018-evolution

Checkpoint 120 local. El registro conserva 112 requisitos: 92 originales y veinte hallazgos añadidos. Sus criterios permanecen exactos. MAIN sigue en esquema 30 con R12, R23, SEC11 y R24 parcial. El workspace original permanece intacto. Free conserva diez clientes activos, un plan por cliente al día y diez planes totales por gimnasio al día. Desktop sigue soportado. No hubo push, PR, despliegue, cargos ni comunicaciones reales.

La candidata MFA 31 está aislada en bd34893c4b6f806041b0cc6b7f156e9286886748. Compone el producto 4a con 33 archivos de CI y pruebas de e0, sin conflictos; conserva los 23 helpers históricos exactos. Esta composición es preparatoria: CI no está aceptado. La regresión SaaS completa está en diagnóstico serial con cobertura y maxfail20; no hay resultado todavía. [Composición](evidence/checkpoint120-seal-receipt-20261019/candidate-receipt.json).

Seguridad aceptó el backend 440 con alcance acotado. QA comprobó diez VM propios y cuatro flujos HTTP en SQLite sobre da343, y repitió esos mismos cuatro en PostgreSQL restringido sobre c669. Las bases temporales quedaron ausentes y sin sesiones. QA también repitió quince grupos mantenidos de Chrome sobre c669 y revisó doce pantallas: sin violaciones axe AA en los bloques nuevos, overflow ni errores de página. Conservó un fallo preparatorio antes de Chrome y un timeout de STOP; el cierre final sólo señalizó el proceso propio tras verificar su identidad completa. No se observó el snapshot final de clave MFA en RAM ni se afirma cierre grácil. [QA de composición](evidence/qa-mfa31-composition-independent-20261019/phase-summary.json), [PG](evidence/qa-mfa31-pg-independent-20261019/phase-summary.json), [Chrome y límites](evidence/qa-mfa31-browser-v2-independent-20261019/phase-summary.json).

UX-19 corrigió el resumen obsoleto de factor y códigos que seguía visible después del ACK. El mismo canary pasó de tres rojos a tres verdes; QA añadió dos cambios de cuenta durante el renderizado, también verdes. Es aceptación focal sobre 4a; los quince grupos anteriores no se reatribuyen a ese cambio. [Revisión](evidence/qa-mfa31-summary-after-independent-20261019/phase-summary.json).

QA restauró el esquema 31 poblado sobre 4a: una prueba verde, con las 61 aserciones del módulo 30 y las 36 del helper 28 preservadas mediante inversa completa. Verificó 32 modelos, 33 tablas físicas, 25 familias FORCE RLS y las filas nuevas de MFA. Ambas bases se eliminaron exactamente y su ausencia se comprobó desde otra conexión. No define RPO/RTO ni prueba recuperación de producción. [Restauración](evidence/qa-mfa31-restore-independent-20261019/phase-summary.json).

La adopción DAB de cinco archivos de tests tiene 174 resultados verdes del autor y aceptación independiente focal: 24 SQLite —veinte replays y cuatro propios— y dieciséis VM del lector con los acompañantes R24 reales. La única expectativa 404→403 aprobada conserva opacidad e integridad; las demás aserciones se mantienen. QA-12 sigue en revisión de integración: la fixture antigua omitía esos módulos. Sus rojos auténticos eea8 y el contraste causal con stubs permanecen separados del pase con módulos reales. [Peer de fixtures](evidence/qa-mfa31-fixture-peer-independent-20261019/phase-summary.json).

CI e0 queda preservado sin aceptación: el histórico auténtico 573 pasó FULL y 348 VM; el actual ejecutó 31 módulos y 494 comprobaciones, pero omitió snapshot25, que incorpora siete casos nuevos y repite dieciocho anteriores. QA también confirmó un marcador de rol opcional y revisa la frontera CLI del checker. La corrección debe pasar los mismos negativos antes de ejecutar las 173 identidades PostgreSQL actuales. [Preimagen offline](evidence/mfa31-ci-e0-offline-20261019/manifest.json).

La regresión amplia de MAIN 30 sigue verde: 2597 aprobadas y una omisión de symlinks en Windows por modo serial con cobertura y dos workers con orden mezclado. Ese resultado no acredita 31. MFA aún requiere CI, regresión amplia e imagen común, avisos por cambios de factor, custodia y rotación de claves, configuración real y un procedimiento legítimo ante pérdida total de factores.

Linux: D60 actualiza sólo el hash de InRelease que detuvo la compilación anterior. Seguridad validó firmas, 409 hojas e índices y paquetes invariantes, con siete negativos verdes: PASS_METADATA_ONLY. La nueva compilación sigue activa bajo TCG y ya instaló libpq y compilador. QEMU propio conserva una ventana exclusiva para esas pruebas y la revisión posterior de Seguridad, sin PG ni proxies. No hay aceptación de ABI, linkage, runtime54 ni cierre de los 71 IDs OS. [Metadata](evidence/security-apt-metadata-refresh-independent-20261019/source.json).

R23 y R24 siguen parciales. R25, R27, R30, R31, R33, R34 y R35 conservan sus dependencias documentadas. Países y conservación, y volumen y p95, siguen consultados y pendientes; no se inventaron políticas, SLO, pilotos ni dictámenes. El diagnóstico R34 obtuvo dieciséis respuestas 200 sin reproducir el timeout histórico; sigue abierto.

Siguiente acción: corregir y revisar los gates CI, ejecutar las 173 identidades actuales en PostgreSQL y resolver la regresión amplia, mientras Operación termina el target nativo. Después continuar las capacidades de producto y privacidad pendientes. [Registro](TRAZABILIDAD.md).
''',encoding='utf8')
for name,text in {
 'VALIDACION.md':'QA peer de fixtures aceptado: 24 SQLite (20 replays y4 propios) y16 VM con módulos reales. CI e0 se conserva sin aceptación: histórico573 FULL+348; actual31/494 con snapshot25 omitido. Los173PG siguen pendientes. Composición bd348 sólo cambia33 archivos CI/tests y conserva23 helpers; la regresión amplia está activa, aún sin resultado.',
 'CAMBIOS.md':'Se incorpora documentación de la aceptación focal de fixtures, y se preserva e0 como preimagen CI incompleta. MAIN no cambia producto ni esquema. La candidata bd348 incorpora el delta CI e0 para revisión; sus gates no están aceptados.',
 'DECISIONES.md':'No atribuir los quince grupos Chrome c669 a la corrección UX19 posterior. No sumar los veinte replays de QA como casos nuevos. Exigir snapshot25 en el CI actual y confirmación obligatoria de rol restringido en los marcadores; la revisión CLI continúa antes de PostgreSQL.',
 'RIESGOS.md':'CI e0 no tiene aceptación por omisión de siete casos nuevos snapshot y marcador de rol opcional. El checker CLI sigue en revisión. La compilación nativa está activa, sin prueba final de ABI/linkage ni SCA. No se infiere seguridad de producto desde un marcador incompleto del laboratorio.',
}.items():
    with (RUN/name).open('ab') as out:out.write(('\n\n## Checkpoint 120\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True,capture_output=True)
assert criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))==before
(seal/'receipt.json').write_bytes((json.dumps({'base':BASE,'registry':112,'criteria_exact':112,'new_ids':[],
 'main_product_changed':False,'authenticated_manifests':reviews,
 'RAW_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':SHA(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n').encode())
raw.update(p for p in seal.iterdir() if p.is_file())
names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
docs=[(RUN/n).relative_to(ROOT).as_posix() for n in ['ESTADO.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(ROOT/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record independent fixture acceptance and incomplete CI preimage'],cwd=ROOT,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'RAW_authenticated':len(names),'criteria_exact':112,'main_product_changed':False}))
