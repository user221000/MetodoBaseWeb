from pathlib import Path
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile

root=Path(r'F:\MetodoBaseWeb-execution-20261018');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
run=root/'docs/implementation/20261018-evolution';ev=run/'evidence'
base='0a35ad5cead1fa6dea0f2c4dcd4df39426beb402'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
reviews=[
 ('qa-mfa31-current-fixtures-peer-independent-20261019','8b4afcabc5c2a9af3ae371690417f9cf2fd9fd08f324693c2bc9dda348582d1f','phase-summary.json','61ffbfb152cf8de21a42697ca089d03abddf06ae3de877627d40d7d84ed54891'),
 ('expat-sec10-call-visibility-author-20261019','02c7914625ac641a8e13843cfafa1f791a1a917425b182414c5e53725fe76805','source.json','cc8e4454303047ef835d5ee1a149808ab49986df2380849526a73043fce3396c'),
 ('security-expat-de69-diagnostic-independent-20261019','de12b33168426e43a69acec8d70c70c947d334036699ea145d219f576837b3df','source.json','8b1c2d1548e261e7264287ce31b335e97efa1b46fa06100a7729b080a08ff056'),
 ('security-expat-call-visibility-independent-20261019','30f97f414f975cc2a4fddb5e48a62556de0d91e78372f02bd95873934427b97c','source.json','a2d9ce8779169a123042c30e40bebfe0066d2e2f9c18689e586985b02781ded4'),
]
raw=set()
for prefix,digest,attestation,source_digest in reviews:
    parent=ev/prefix;manifest=parent/'manifest.json';blob=manifest.read_bytes();assert sha(blob)==digest
    doc=json.loads(blob)
    if prefix=='qa-mfa31-current-fixtures-peer-independent-20261019':
        assert set(doc)=={'source_head','attributes','entries','count','phase_summary_SHA256'}
        assert doc['count']==len(doc['entries'])==25
        assert doc['phase_summary_SHA256']=='61ffbfb152cf8de21a42697ca089d03abddf06ae3de877627d40d7d84ed54891'
        assert doc['source_head']=='79dce040a9d79b51c1971bf4a99338a06c2ac659'
        rows=doc['entries']
    else:rows=doc.get('files',doc)
    if isinstance(rows,dict):rows=[{'path':name,**meta} for name,meta in rows.items()]
    for row in rows:
        assert ('sha256' in row)!=('SHA256' in row)
        path=parent/row.get('path',row.get('file',''));data=path.read_bytes()
        assert path.resolve().is_relative_to(parent.resolve()) and sha(data)==row.get('sha256',row.get('SHA256'))
        assert 'bytes' not in row or len(data)==row['bytes']
        scan(data,path.name);raw.add(path)
    source=parent/attestation;assert sha(source.read_bytes())==source_digest
    scan(source.read_bytes(),source.name)
    assert (parent/'.gitattributes').read_text(encoding='ascii').strip()=='* -text'
    raw.update([manifest,source,parent/'.gitattributes'])

prefix=ev/'prepared-wave123-20261019';assert not prefix.exists()
contents={'driver.py':Path(__file__).read_bytes()}
contents['preconditions/driver-v3-guard.py']=(tmp/'metodobase-checkpoint123-v3.py').read_bytes()
contents['preconditions/prepare-v4.py']=(tmp/'metodobase-checkpoint123-v4-prepare.py').read_bytes()
contents['preconditions/v3-guard-cause.json']=(json.dumps({'failed_before_any_writes':True,'cause':'The manifest metadata also includes count and phase_summary_SHA256; a guard inferred from a partial head read rejected the complete authenticated format.','correction':'Read actual complete top-level keys, preserve exact schema guard and authenticate count25 and phase-summary anchor explicitly.'},indent=2)+'\n').encode()
contents['preconditions/driver-v2-manifest-format.py']=(tmp/'metodobase-checkpoint123-v2.py').read_bytes()
contents['preconditions/prepare-v3.py']=(tmp/'metodobase-checkpoint123-v3-prepare.py').read_bytes()
contents['preconditions/manifest-format-cause.json']=(json.dumps({'failed_before_any_writes':True,'cause':'The QA peer producer uses entries with separate metadata. Treating its top-level metadata as files raised TypeError.','correction':'Authenticate the same pinned manifest and select its exact entries schema, with expected metadata keys and source head. No evidence bytes modified.'},indent=2)+'\n').encode()
contents['preconditions/driver-v1-SyntaxError.py']=(tmp/'metodobase-checkpoint123.py').read_bytes()
contents['preconditions/prepare-v2.py']=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-checkpoint123-v2-prepare.py').read_bytes()
for path in (tmp/'metodobase-mfa31-compose-fixtures79-20261019').iterdir():
    assert path.is_file();contents['fixture-compose/'+path.name]=path.read_bytes()
contents['ci-preflight/review.json']=(tmp/'metodobase-mfa31-composed-ci-preflight-20261019/review.json').read_bytes()
for name in ['driver.py','before.json','pip-before.raw.log']:
    contents['broad-serial-start/'+name]=(tmp/'metodobase-mfa31-composed-serial-20261019'/name).read_bytes()
contents['broad-serial-start/scope.json']=(json.dumps({'source':'809eab28c40c112cb6e3c9d8caceebae28683abd',
 'status':'RUNNING; no result or acceptance yet','command_mode':'serial coverage','started_utc':'2026-10-19 19:16 UTC',
 'parallel':'Not started; runs only after serial acceptance or an explicit new diagnostic need.'},indent=2)+'\n').encode()
for name,blob in contents.items():scan(blob,name)
prefix.mkdir();(prefix/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in contents.items():
    path=prefix/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob);raw.add(path)
(prefix/'manifest.json').write_bytes((json.dumps({name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in contents.items()},indent=2)+'\n').encode())
raw.update([prefix/'manifest.json',prefix/'.gitattributes'])

path=run/'TRAZABILIDAD.json';data=json.loads(path.read_bytes());fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{r['id']:{field:r[field] for field in fields} for r in value['requisitos']}
before=criteria(data);assert len(before)==119
notes={
 'R05':'CI ed4 y los 173 nodos PG permanecen exactos tras la composición 809eab2. El preflight real verifica 145 controles workflow y source pins sin repin. Regresión serial con cobertura en ejecución; no resultado adelantado.',
 'R17':'b500, con aceptación independiente focal24+2, está compuesto en809eab2. Regresión común en ejecución. No métricas distribuidas, streaming completo ni SLO acreditados.',
 'R18':'Seguridad confirmó de69 con parser ELF propio:1→93exports, argvvacío y _compile/link→call. Nuevo72c44a1 preserva31inputs y corrige call/visibilidad/gates. Autor41 y propios13 (replays separados), PASS_STATIC_ONLY. Nuevo build autorizado tras revisión; aceptación nativa aún pendiente.',
 'R19':'Peer79 cerrado:56/56,54originales y2controles deautor,58asserts e inversas exactas.10176fuentes/89paquetes/Python quietos,pip0,mismaSQLite29→31/33tablas;sinPG niChrome. Merge809 conserva4tests y otros10143blobs. PreflightCI145 pasa. Broadserial809 en curso; n2 pendiente.',
 'R25':'Implementación32 iniciada en WT separado desde5637. Before real4GET404/2factories con registro/login ySQLite31 comprobada. No se acepta función pública que trate GUCactor como firma. Backend evalúa lector interno mínimo con autoridad persistida/locks/restauración/pool1; requiereSEC. UI coordinada aparte. Nada32 integrado ni aceptado.',
 'R32':'Fixtures79 aceptados porQA56/56 y compuestos809;MFA/producto/R17/CI/173map intactos. Regresión serial con cobertura en curso, n2 aún pendiente. Sin aprobación global ni operaciones/configuración real.',
 'OPS12':'72c44a1 hookcall y gate4compile+1link aceptados sólo estáticamente:13propios y41replayautor,31inputs exactos,4786fuentes/89paquetes/Python quietos. Falta traza nativa real del nuevo target; de69 vacío queda preservado.',
 'OPS13':'Parser ELF independiente confirmó93exportsDE69 frente1base sin RPATH/RUNPATH/libcúnica.72c44a1 deriva hidden deMakefilebase y exigePyInitúnico; gate rechaza93anteriores. Sóloestática aceptada; nuevoartefactonativo pendiente.',
 'SEC10':'Seguridad aceptó estáticamente72c44a1 después de autenticar beforeDE69 y fuentes:setuptools84call/configNamespacePSF.13propios y41replay solapados,31prepare/12locks/pins/patch intactos; noVM/ELFload/nm en esta revisión. Nativo/SCA71 siguen pendientes.',
}
refs={
 'R05':['prepared-wave123-20261019/ci-preflight/review.json'],
 'R18':['security-expat-call-visibility-independent-20261019/source.json','security-expat-de69-diagnostic-independent-20261019/source.json'],
 'R19':['qa-mfa31-current-fixtures-peer-independent-20261019/phase-summary.json','prepared-wave123-20261019/fixture-compose/receipt.json'],
 'R32':['qa-mfa31-current-fixtures-peer-independent-20261019/phase-summary.json'],
 'OPS12':['security-expat-call-visibility-independent-20261019/source.json'],
 'OPS13':['security-expat-de69-diagnostic-independent-20261019/source.json','security-expat-call-visibility-independent-20261019/source.json'],
 'SEC10':['security-expat-call-visibility-independent-20261019/source.json'],
}
for row in data['requisitos']:
    ident=row['id']
    if ident in notes:row['observaciones'].append('Checkpoint123: '+notes[ident])
    for item in refs.get(ident,[]):
        ref='evidence/'+item
        if ref not in row['evidencia']:row['evidencia'].append(ref)
    if ident in {'OPS12','OPS13'}:
        row.update(estado='en_revision',implementacion='en_revision',revisor='Seguridad independiente: PASS_STATIC_ONLY72c44a1; nativo pendiente')
        row['commits'].append('72c44a1834d7bd9803b4b8846c6c87e85a53bfd3')
assert criteria(data)==before
path.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())

(run/'ESTADO.md').write_text('''# Estado de ejecución 20261018-evolution

Checkpoint 123 local. El registro conserva 119 requisitos: 92 originales y 27 hallazgos añadidos. Los 119 criterios anteriores permanecen exactos. MAIN sigue en esquema 30 y el workspace original permanece intacto. Free: diez clientes activos, un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales.

La candidata MFA31 está aislada en 809eab28c40c112cb6e3c9d8caceebae28683abd. Compone CI ed4, observabilidad R17 b500 y fixtures79, con los respectivos blobs revisados exactos. El preflight CI real pasó 145 controles y sus anclas sin repin. La regresión serial completa con cobertura está en ejecución; dos workers con orden mezclado todavía no comenzaron. No se adelantan sus resultados.

QA aprobó los fixtures79 en una única tanda de 56 casos: 54 originales y dos controles del autor. Conservó las 58 aserciones, inversas completas, helpers históricos y producto. Observó las mismas bases SQLite migradas29→31, 33 tablas y login MFA real; una mutación privilegiada sin grant quedó403 sin negocio ni mail. Sus 10176 archivos, 89 paquetes y Python permanecieron estables, con pip check verde. [Peer](evidence/qa-mfa31-current-fixtures-peer-independent-20261019/phase-summary.json). El diagnóstico amplio rojo bd348 sigue preservado; no se convirtió en aceptación por editar sus resultados.

CI ed4 ya tiene contrato y 173 casos PostgreSQL aceptados independientemente: doce comandos y checker real, sin errores ni omisiones. QA cerró 42 bases propias con cero sesiones y ausencia desde otra conexión, sin FORCE ni terminar backends. Se mantuvieron archivos, paquetes, Python, binarios PG, config y helpers. Ese alcance no acredita Actions, Redis, Chrome ni imagen. [PG173](evidence/qa-mfa-ci31-pg-independent-20261019/phase-summary.json).

R17 b500 tiene aceptación independiente focal: el mismo driver pasó de doce fallos de cabeceras y doce controles verdes a24verdes, más los mismos dos controles de límites. Conserva errores opacos y sólo amplía la frontera privada existente a tres rutas canónicas; no se demostró una fuga. Autor103, freeze52, fix84 y replay24 son fases solapadas. Falta la regresión compuesta y operación real; no acredita agregación distribuida, streaming completo ni SLO. [Antes](evidence/security-r17-observability-independent-20261019/source.json), [después](evidence/security-r17-observability-after-independent-20261019/source.json).

El backend MFA440 tiene aceptación de Seguridad acotada; QA preserva sus revisiones SQLite, PostgreSQL, restauración31 y navegador con sus fuentes exactas. Los quince grupos Chrome y doce pantallas anteriores no se reatribuyen a809. UX19 pasó sus tres mismos casos y dos cambios de cuenta propios. El timeout de cierre del servidor, la intervención limitada al proceso propio y la ausencia de un snapshot final de clave en RAM siguen documentados. No se afirma cierre grácil ni una comprobación de RAM que no ocurrió. [Chrome](evidence/qa-mfa31-browser-v2-independent-20261019/phase-summary.json), [restauración](evidence/qa-mfa31-restore-independent-20261019/phase-summary.json), [UX19](evidence/qa-mfa31-summary-after-independent-20261019/phase-summary.json).

La regresión amplia anterior de MAIN30 permanece en2597aprobadas y una omisión de symlink Windows por cada modo serial y n2; no acredita31. La nueva candidata todavía requiere regresión compuesta e imagen común, además de avisos por cambios de factor, custodia y rotación de claves, configuración real y procedimiento legítimo ante pérdida total de factores.

Linux: el fallo D60 por encabezado Clinic omitido permanece intacto. de69 añadió ese único input, compiló y pasó seis comprobaciones XML, pero conservó argv vacío y93exports frente al único PyInit de la base. Seguridad confirmó ambos defectos con parser ELF y revisión de setuptools propios.72c44a1 corrige el hookcall, valida cuatro compilaciones y un enlace reales, deriva visibilidad mínima de la base y exige un único export. Está aceptado sólo estáticamente:41controles de autor y13propios, con31inputs y12locks exactos. Se autorizó un nuevo build después del sello; falta aceptación nativa, runtime54 y SCA/OS71. Las imágenes y contextos previos permanecen intactos. [Before independiente](evidence/security-expat-de69-diagnostic-independent-20261019/source.json), [fix estático](evidence/security-expat-call-visibility-independent-20261019/source.json).

R25 empezó en ramas separadas de backend y frontend. El before tiene cuatro GET404 reales, ambas factories y SQLite31 verificada con registro/login real. DDL32 permanece reservado exclusivamente a R25. No se acepta usar un GUC de actor como firma; la lectura compartida necesita autoridad persistida, consentimiento exacto, minimización y pruebas de restauración y pool1. Se preserva el catálogo: lecturas profesionales según derecho vigente de clínica; medidas personales, consentimiento, retirada y exportación sin ese paywall. Nada32 está integrado ni aceptado. [Contrato](evidence/prepared-wave121-20261019/R25/contract.RAW.md).

R23, R24, R27, R30, R31, R33, R34 y R35 conservan sus pendientes y dependencias. Países y conservación, y volumen y p95, siguen consultados sin respuesta; no se inventaron políticas, objetivos, pilotos ni dictámenes. El diagnóstico R34 obtuvo dieciséis respuestas200 sin reproducir el timeout histórico y continúa abierto.

Siguiente acción: evaluar la regresión serial, ejecutar n2 cuando proceda y validar el nuevo target nativo. Continuar R25 en paralelo y someterlo a revisión independiente antes de integrar producto32. [Registro](TRAZABILIDAD.md).
''',encoding='utf8')
(run/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint 123: 119 requisitos y sus criterios anteriores intactos. MAIN permanece en esquema30. La candidata31 aislada809 compone CIed4, R17b500 y fixtures79 revisados; regresión completa serial con cobertura en ejecución, n2 pendiente.

QA aceptó 173 casos PostgreSQL y 56 de fixtures en alcances separados. Seguridad aceptó R17 con el mismo driver24 y dos controles. Los fallos anteriores siguen preservados.

Expat72 tiene aceptación sólo estática; nuevo build autorizado, aún sin resultado nativo. R25 está en implementación separada con DDL32 exclusivo y revisión de lectura compartida pendiente.

Free: diez clientes, un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''',encoding='utf8')
for name,text in {
 'VALIDACION.md':'QA peer79:56/56,58aserciones originales e inversas completas, misma SQLite31/33tablas;10176fuentes89paquetes/Python quietos,pip0. Composición809 conserva4tests exactos y otros10143blobs; preflightCI145 pasa. Broadserial en curso, n2 pendiente. Expat72:41autor+13propios son alcances solapados; PASS_STATIC_ONLY, nuevo build todavía sin resultado.',
 'CAMBIOS.md':'La candidata aislada809 integra fixtures79 después del peer, preservando producto y CI. Expat72 corrige call, visibilidad y gates sin cambiar pines, parche,31inputs ni12locks. Backend/UI R25 comenzaron en ramas separadas; MAIN sólo registra evidencia y estado.',
 'DECISIONES.md':'No interpretar el GUCactor como firma verificable. R25 requiere un lector mínimo con autoridad derivada, consentimiento y locks; probar pool1/restauración y revisar antes de aceptar alternativa. Conservar entitlement profesional de clínica sin impedir medidas personales, retirada ni exportación por ese paywall. La aceptación estática del compilador no equivale a un artefacto nativo aceptado.',
 'RIESGOS.md':'Pendientes resultado broadserial/n2 de809, imagen común y validación nativa72. R25 añade mediciones/consentimiento32 bajo revisión; el acceso compartido no puede depender de un GUC falsificable ni exponer sesiones o filas privadas. Siguen configuración/operacionesMFA, políticas, objetivos de carga, pilotos y dictámenes reales pendientes.',
}.items():
    with(run/name).open('ab') as handle:handle.write(('\n\n## Checkpoint 123\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
assert criteria(json.loads(path.read_bytes()))==before
seal=ev/'checkpoint123-seal-receipt-20261019';assert not seal.exists();seal.mkdir()
(seal/'.gitattributes').write_bytes(b'* -text\n');(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
(seal/'receipt.json').write_bytes((json.dumps({'base':base,'registry':119,'previous_criteria_exact':119,'main_product_changed':False,'authenticated_reviews':reviews,
 'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n').encode())
raw.update(p for p in seal.iterdir() if p.is_file());names=sorted(p.relative_to(root).as_posix() for p in raw)
docs=[(run/name).relative_to(root).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(root/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Preserve fixture peer and compiler static reviews before composed runtime acceptance'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':119,'previous_criteria_exact':119,'RAW_authenticated':len(names),'main_product_changed':False}))
