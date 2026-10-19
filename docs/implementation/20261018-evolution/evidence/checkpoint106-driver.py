"""Checkpoint closed evidence only; keep schema29/API and history30 work isolated."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import zipfile

root=Path('F:/MetodoBaseWeb-execution-20261018')
run=root/'docs/implementation/20261018-evolution'
ev=run/'evidence'
temp=Path('C:/Users/Consu/AppData/Local/Temp')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='66d9dec0e15dd873038bd248d3883daeeb27d4ca'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root).strip()
qa=ev/'history-pg200-independent-20261019'
assert sha((qa/'final-summary.json').read_bytes())=='a128a9f42c147bfb6b8f94030ef26cd74c8ded64fe7eca34264490bc953e16fe'
assert sha((qa/'final-manifest.json').read_bytes())=='c46bbed998d5d52115130c7460986f972c04487bd20c4a37cf909c4bcf1e5f0a'
files=json.loads((qa/'final-manifest.json').read_text(encoding='utf-8'))['files']
for name,value in files.items():assert sha((qa/name).read_bytes())==(value if isinstance(value,str) else value['sha256'])
samples=json.loads((qa/'run-66d9dec-20261019T1112/samples.json').read_text(encoding='utf-8'))
assert len(samples)==200 and len({s['sample'] for s in samples})==200
assert all(s['status']==200 and s['semantic_valid'] and s['records']==50 and s['response_bytes']==8161 and s['server']['sample']==s['sample'] for s in samples)
recalculated={}
for concurrency in [1,5]:
    rows=[s for s in samples if s['sample'].startswith('history-c'+str(concurrency)+'-')]
    assert len(rows)==100
    values=sorted(s['client_ms'] for s in rows)
    recalculated[str(concurrency)]={'n':100,'p50_ms':values[49],'p95_ms':values[94],'max_ms':values[-1]}
assert abs(recalculated['1']['p95_ms']-16.23120001750067)<1e-9
assert abs(recalculated['5']['p95_ms']-144.24409996718168)<1e-9
sec=ev/'sec08-linux-independent-20261019'
assert sha((sec/'source.json').read_bytes())=='cbac8970490358dd37a21a5911ca6f34bf58dbf59c75f3c09cb8a63f82646521'
assert sha((sec/'docker-delta-milestone.json').read_bytes())=='16a79fad23c96059afe931b947b8c980a74c451ce83daeebbbb61f8f425a95f0'

desktop=ev/'desktop31215-build66-20261019';desktop.mkdir(exist_ok=False)
author=temp/'metodobase-desktop31215-build66-20261019'
build_summary=json.loads((author/'summary.json').read_text(encoding='utf-8'))
inno_summary=json.loads((author/'inno/summary.json').read_text(encoding='utf-8'))
assert build_summary['exit']==0 and build_summary['sources_stable'] and build_summary['packages_stable']
assert build_summary['runtime']['version']=='3.12.15' and build_summary['target_packages']==83
assert inno_summary['exit']==0 and inno_summary['bundle_files']==1215
for flag in ['sources_stable','bundle_stable','inputs_stable','tools_stable']:assert inno_summary[flag]
for name in ['summary.json','build.log','pip-check.log','package-inventory.json','inno/summary.json','inno/compile.log']:
    target=desktop/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(author/name,target)
bundle_root=Path('F:/mb-d31215-20261019/dist/MetodoBase')
shutil.copyfile(bundle_root/'build-manifest.json',desktop/'build-manifest.json')
for name in ['installer-entry.iss','installer-preparation.json']:
    shutil.copyfile(bundle_root.parent/'installer-inputs'/name,desktop/name)
zip_path=bundle_root.parent/'MetodoBase_v2.0.0_win32.zip'
assert zip_path.stat().st_size==122441614 and sha(zip_path.read_bytes())=='4966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353'
setup=Path(inno_summary['outputs'][0]['path'])
assert setup.stat().st_size==89973261 and sha(setup.read_bytes())=='5651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363'
(desktop/'artifact-pointers.json').write_text(json.dumps({'source_commit':build_summary['source_commit'],'zip':{'path':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':sha(zip_path.read_bytes())},'setup':inno_summary['outputs'][0],'binaries_in_repository':False,'independent_payload_review':'pending','setup_executed':False},indent=2)+'\n',encoding='utf-8')
for name in ['metodobase-desktop31215-build66-20261019.py','metodobase-desktop31215-inno66-20261019.py']:shutil.copyfile(temp/name,desktop/name)
(desktop/'README.md').write_text('''# Desktop 3.12.15: reconstrucción real de fuente 66d9dec

Build exit 0 en 474.859 s: 78 pruebas de fuente y siete subtests, PyInstaller onedir de 1215 archivos, diagnóstico Qt offscreen, ZIP y preparación de instalador. Las 4433 fuentes y 83 paquetes permanecieron iguales; pip check terminó en cero. El diagnóstico declara explícitamente que no ejecuta flujos de negocio ni acredita aislamiento de red del sistema operativo.

Inno 6.7.3 compiló el Setup con exit 0 en 102.906 s. Bundle, inputs, fuentes y 119 archivos de herramienta permanecieron iguales. El compilador y el instalador oficial se contrastaron con la procedencia fijada anterior; no se ejecutó una nueva comprobación de firma.

ZIP: 122441614 bytes, SHA256 4966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353. Setup: 89973261 bytes, SHA256 5651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363. Los binarios siguen en las rutas locales registradas. La revisión independiente del payload está pendiente. No instalación, upgrade, desinstalación, firma de MetodoBase o auditoría completa de bibliotecas nativas por estas pruebas.
''',encoding='utf-8')

probe=ev/'history-index-probes-root-20261019';probe.mkdir(exist_ok=False)
for label,folder in [('first-page','metodobase-history-index-probe-20261019'),('late-before','metodobase-history-late-cursor-before-20261019'),('late-after','metodobase-history-late-cursor-after-20261019')]:
    origin=temp/folder;target=probe/label;target.mkdir()
    for p in origin.iterdir():
        if p.is_file() and p.name!='failure-private.log':shutil.copyfile(p,target/p.name)
    assert json.loads((target/'owned-database.json').read_text(encoding='utf-8'))['removed']
assert json.loads((probe/'late-before/summary.json').read_text(encoding='utf-8'))['actual_plan_row_work']==1000
assert json.loads((probe/'late-after/summary.json').read_text(encoding='utf-8'))['actual_plan_row_work']==51
shutil.copyfile(temp/'metodobase-history-bounded-reader-20261019.xml',probe/'maintained96.xml')
shutil.copyfile(temp/'metodobase-history-bounded-reader-20261019.log',probe/'maintained96-raw-powershell.log')
with zipfile.ZipFile(probe/'drivers-and-source-raw.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in ['metodobase-history-index-probe-20261019.py','metodobase-history-late-cursor-before-20261019.py','metodobase-history-late-cursor-after-20261019.py']:
        archive.writestr(name,(temp/name).read_bytes())
    work=Path('F:/mb-hidx-20261019')
    archive.writestr('before/web/routes/usuario.py',subprocess.check_output(['git','show','50085ad:web/routes/usuario.py'],cwd=work))
    for name in ['web/routes/usuario.py','web/services/personal_history_query.py']:archive.writestr('after/'+name,(work/name).read_bytes())
(probe/'README.md').write_text('''# Experimentos funcionales del índice y cursor

Tres bases UUID propias, todas eliminadas con ausencia verificada. Sin carga HTTP, benchmark, SLO o migración productiva. El primer ensayo en 28 conservó las 1000 filas ordenadas, cinco empates y diez fechas NULL: el índice propuesto eliminó Sort y redujo el lector de planes de 1000 a 51. Las estructuras anteriores y 20 familias RLS quedaron iguales al quitar el índice adicional de la comparación.

La consulta real del cursor avanzado se capturó sobre núcleo 29 aislado con el índice adicional: visitó 1000 filas para devolver 50. El cambio de lector usa comparación de tupla y UNION de ramas acotadas en una sola sentencia. El mismo criterio de cursor devolvió las mismas 50 filas visitando 51 en el corpus sin fechas NULL. La mezcla dated/NULL y la migración 30 aún requieren gates propios. Las 96 pruebas mantenidas de historial/cursor/headers/error pasaron, con cuatro avisos existentes; log PowerShell UTF16 conservado sin transcodificar.

Fotos de los probes cubren archivos ya tracked. El nuevo helper estaba untracked y su SHA se conserva después en el ZIP, sin inventar una foto previa de ese archivo. La revisión independiente deberá fijar también ese helper antes de ejecutar. Fuente y cambios sólo en F:/mb-hidx-20261019; MAIN no contiene el lector nuevo ni la migración 30.
''',encoding='utf-8')

for folder in [desktop,probe]:
    (folder/'manifest.json').write_text(json.dumps({'files':{p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(folder.rglob('*')) if p.is_file()}},indent=2)+'\n',encoding='utf-8')

data=json.loads((run/'TRAZABILIDAD.json').read_text(encoding='utf-8'))
preserved={r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in data['requisitos']}
rows={r['id']:r for r in data['requisitos']}
for ident in ['R18','SEC08']:
    r=rows[ident];r['commits'].extend(['9401b5e','b6cdaac','f8ceaa1','66d9dec0e15dd873038bd248d3883daeeb27d4ca'])
    r['evidencia'].extend(['evidence/sec08-linux-independent-20261019/source.json','evidence/desktop31215-build66-20261019/artifact-pointers.json'])
    r['observaciones'].append('Docker/bootstrap integrado tras hito independiente16a79fad. OS mantiene164entradas/71IDs y matriz73 sinignores;capdrop/NNP/rootfsRO son flagsdel laboratorio,no defaultsDockerfile. Inventario de bibliotecas vendorizadas pendiente. Desktop3.12.15 ya reconstruido,ZIP4966896c/Setup5651f418,1215archivos;independencia payload y nativos pendientes.')
r=rows['R34'];r['evidencia'].extend(['evidence/history-pg200-independent-20261019/final-summary.json','evidence/history-index-probes-root-20261019/README.md'])
r['pruebas'].append('200HTTPmedidos exactamente100C1+100C5,todos200/50resúmenes/8161bytes/200ACK,737fuentes89paquetes quietos. p95observados16.2312/144.2441ms;3intentosreadiness+1warmupexcluidos. EXPLAIN51salidas pero1000filasvisitadas/ordenadas. SinSLO/causalidad;baseline1400intacto.')
r['observaciones'].append('Prototipo indexroot:primerapágina1000→51sinSort yordenNULL/tiespreservado;cursoravanzadoaún1000coníndice,luegolectorUNIONaislado reduce51 y96mantenidasverdes. NoMAIN/migración30 aún;faltan mezclaNULL/dated,DDLfirmado/preservación/revisiónindependiente/SLO/otrosflujos.')
rows['R09']['evidencia'].append('evidence/desktop31215-build66-20261019/artifact-pointers.json')
rows['R09']['observaciones'].append('Soporte desktop mantiene nuevoZIP/Setup3.12.15 de66d9dec;revisiónindependiente payload pendiente,no instalación.')
rows['R12']['observaciones'].append('Núcleo29 aislado ad712416 selectivo25paths:QA repitió mismos55casos sinfallos(no110). Negativos propios yseguridad enproceso;APIautor79casosfocales más42privacidad/baseline enalcancesseparados,restore29enautoría. UI146d873 prepara41VM,nomontada;adendaDTO backenddisponible,integraciónUIpendiente. Nada29integradoMAIN.')
assert len(data['requisitos'])==104
for r in data['requisitos']:assert {k:r[k] for k in preserved[r['id']]}==preserved[r['id']]
(run/'TRAZABILIDAD.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def append(name,text):
    p=run/name;p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n'+text+'\n',encoding='utf-8')
append('VALIDACION.md','''## Checkpoint 106: imagen aceptada por delta, historial medido y desktop reconstruido

Docker/bootstrap integrado en9401b5e/b6cdaac/f8ceaa1/66d9dec tras revisión independiente del delta. [Seguridad](evidence/sec08-linux-independent-20261019/source.json) conserva164entradas/71IDs rojos, matriz73 y ceroignores. Los seis campos de164hallazgos coinciden; Fingerprint/PkgIdentifier cambian, sin afirmar igualdad de objetos completos. FlagsNNP/capdrop/rootfsRO pertenecen al laboratorio. Bibliotecas vendorizadas y runtime de producto pendientes.

[Ensayo200](evidence/history-pg200-independent-20261019/final-summary.json):100C1+100C5,todos200/50filas/8161bytes/200ACK;737fuentes89paquetes quietos. Root rehashó37artefactos y recalculó p95 por rango más cercano16.2312/144.2441ms. Tresintentosauth/readiness y unwarmup excluidos. EXPLAINLimit51 procesa1000;UUID/PIDs eliminados. SinSLO ni atribución causal;baseline1400 intacto.

[Probesroot](evidence/history-index-probes-root-20261019/README.md):índice adicional reduceprimerapágina1000→51 sinSort,pero cursoravanzado siguevisitando1000. LectorUNION aislado produce51candidatos para mismas50filas;96mantenidas verdes. BasesUUID eliminadas. No migración30 ni integraciónMAIN;mezclaNULL/dated y revisión independiente pendientes. Nuevohelper no estaba tracked enlaprimera foto,limitación explícita conservada.

[Desktop66](evidence/desktop31215-build66-20261019/README.md):build0/474.859s bajo3.12.15,78pruebas/siete subtests,Qt offscreen,ZIP y1215archivos;4433fuentes83paquetes estables,pip0. Inno0/102.906s,inputs/bundle/tools quietos. ZIP122441614B SHA4966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353;Setup89973261B SHA5651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363. Revisión independiente payload/nativos pendiente;Setup no ejecutado.
''')
append('CARGA_LOCAL.md','''Medición focal terminada sobre66d9dec:200/200HTTP válidos,50resúmenes/8161bytes,p95observadoC1=16.2312ms/C5=144.2441ms. Root recalculó las200muestras. Elcomparativo delbaseline se limita a20muestras porconcurrencia de lacohorte1000;datos,semántica,muestra ycontención distintos,sin mejora causal niSLO cumplido. EXPLAIN actual visita/ordena1000 antes deLimit51. Índice ylectorUNION se evalúan aparte enprobesfuncionales,con96regresionesverdes,nomigrados/integrados. [Ensayo](evidence/history-pg200-independent-20261019/final-summary.json),[probes](evidence/history-index-probes-root-20261019/README.md).''')
append('CAMBIOS.md','Checkpoint106: Dockerbase/bootstrap/liblzma integrado tras seguridad independiente;OS71IDs abiertos. Desktop66 recompilado con3.12.15,ZIP4966896c/Setup5651f418,pendiente payloadindependiente. R34medido200HTTP;prototipo adicional deíndice/lectoraislado,noMAIN. R12núcleo29 enQA/seguridad yAPI/UI/restore aún aislados.')
append('RIESGOS.md','Checkpoint106: respuesta limitada no prueba trabajoSQL limitado;EXPLAIN dehistorial sigue1000filas. Probes deíndice ylectorUNION ya muestran51,pero faltan migración30/mezclaNULL/revisiónindependiente. Desktop3.12.15 recompilado noimplica payloadrevisado niinstalación. SEC08mantiene71IDsOS ybibliotecasvendorizadas pendientes;capdrop/NNP/rootfsRO no son defaults deDockerfile. Sinexcepcionesderiesgo.')
append('ENTREGA.md','Checkpoint106: Dockercorregido integrado localmente trasseguridad;OS71IDs abierto. Ensayo200HTTP/200ACK completado con límites descriptivos,EXPLAIN revela1000filas. Desktop3.12.15 ZIP4966896c/Setup5651f418 construido,pendiente revisiónindependiente delpayload. Núcleo29/API/UI/restore yoptimización30 siguenaislados. No nuevo despliegue niSetup ejecutado.')
p=run/'ESTADO.md';text=p.read_text(encoding='utf-8')
text=text.replace('Checkpoint 105:', 'Checkpoint 106:')
text=text.replace('faltan 200 HTTP posteriores, EXPLAIN PG, SLO y otros flujos y entornos.', 'se completaron 200 HTTP posteriores y EXPLAIN PG; siguen pendientes optimización del plan, SLO y otros flujos y entornos.')
text=text.replace('el delta Docker aún no está integrado.', 'el delta Docker está integrado en 9401b5e/b6cdaac/f8ceaa1/66d9dec tras aceptación independiente; el gate OS continúa rojo.')
text=text.replace('Nuevo bundle, Setup y revisión independiente pendientes.', 'Nuevo bundle y Setup construidos de 66d9dec: ZIP 4966896c y Setup 5651f418, 1215 archivos. Revisión independiente del payload pendiente.')
text=text.replace('medir 200 HTTP PostgreSQL tras coordinar pausa del backend.', 'incorporar una optimización del historial en la revisión 30 después de aceptar 29.')
text+='\nEnsayo focal 200 completado: todos HTTP 200, 50 resúmenes y 8161 bytes; p95 observado C1 16.2312 ms y C5 144.2441 ms, sin causalidad ni SLO. EXPLAIN todavía visita 1000 filas. Prototipo aislado de índice y lector UNION reduce trabajo a 51 candidatos y pasa 96 regresiones, con mezcla NULL y migración 30 por validar. Backend liberado de la ventana PG.\n\nR12: núcleo selectivo ad712416 en revisión independiente de QA y seguridad; replay de los mismos 55 casos verde. API, restore 29 e integración UI continúan aislados. UI 146d873 prepara 41 VM sin montaje ni E2E; adenda DTO del backend disponible para continuar. MAIN sigue en esquema 28.\n'
p.write_text(text,encoding='utf-8')
subprocess.run([str(temp/'metodobase-candidate-web-20261018/Scripts/python.exe'),'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True)
receipt=ev/'checkpoint106-root-review.json';assert not receipt.exists()
receipt.write_text(json.dumps({'checkpoint':106,'head':'66d9dec0e15dd873038bd248d3883daeeb27d4ca','registry_rows':104,'source_problem_criteria_preserved':104,'qa200_manifest_rehashed':len(files),'samples_recalculated':200,'quantiles_nearest_rank':recalculated,'desktop_source_count':4433,'new_desktop_payload_review':'pending','main_schema':28,'r12_29_isolated':True,'history30_not_yet_migrated_or_integrated':True,'OS_gate':'RED71IDs','external_mutations':False},indent=2)+'\n',encoding='utf-8')
shutil.copyfile(__file__,ev/'checkpoint106-driver.py')
folders=['history-pg200-independent-20261019','sec08-linux-independent-20261019','desktop31215-build66-20261019','history-index-probes-root-20261019']
for name in folders:
    p=ev/name/'.gitattributes';assert not p.exists();p.write_bytes(b'# Preserve RAW evidence bytes only in this new proof directory.\n* -text\n')
raw=[receipt,ev/'checkpoint106-driver.py']
for name in folders:raw.extend(p for p in (ev/name).rglob('*') if p.is_file())
names=sorted(p.relative_to(root).as_posix() for p in raw)
for start in range(0,len(names),20):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+20]],cwd=root,check=True,capture_output=True)
# Explicitly refresh cached blobs under the new scoped RAW attributes.
for name in folders:subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',(ev/name).relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
buf=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(':'+n+'\n' for n in names).encode());position=0;pairs={}
for name in names:
    end=buf.index(b'\n',position);header=buf[position:end].split();assert header[1]==b'blob'
    size=int(header[2]);blob=buf[end+1:end+1+size];position=end+size+2
    assert blob==(root/name).read_bytes(),name
    pairs[name]=sha(blob)
assert position==len(buf)
raw_receipt=ev/'checkpoint106-raw-preservation.json';assert not raw_receipt.exists()
raw_receipt.write_text(json.dumps({'new_raw_files':len(names),'all_git_index_pairs_byte_identical':True,'pair_hashes_sha256':sha(json.dumps(pairs,sort_keys=True,separators=(',',':')).encode()),'scoped_new_attributes':folders,'original_author_manifests_unchanged':True,'policy':'Original line endings/whitespace/binary logs retained. Scoped attributes and coordinator receipts are packaging metadata outside frozen author manifests. No historical proof rewritten.'},indent=2)+'\n',encoding='utf-8')
subprocess.run(['git','-c','core.autocrlf=false','add','--',raw_receipt.relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
docs=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','VALIDACION.md','CAMBIOS.md','CARGA_LOCAL.md','RIESGOS.md','ENTREGA.md']
docpaths=[(run/n).relative_to(root).as_posix() for n in docs]
subprocess.run(['git','diff','--check','--',*docpaths],cwd=root,check=True)
subprocess.run(['git','add','--',*docpaths],cwd=root,check=True,capture_output=True)
staged=set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1])
assert staged==set(names+docpaths+[raw_receipt.relative_to(root).as_posix()])
subprocess.run(['git','commit','-m','docs: checkpoint106 records PG200, security review and rebuilt desktop'],cwd=root,check=True,capture_output=True)
print(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'registry':104,'new_raw_files':len(names),'all_raw_index_identical':True}))
