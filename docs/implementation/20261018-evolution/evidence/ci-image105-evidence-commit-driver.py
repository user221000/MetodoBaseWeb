import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root = Path('F:/MetodoBaseWeb-execution-20261018')
run = root / 'docs/implementation/20261018-evolution'
ev = run / 'evidence'
temp = Path('C:/Users/Consu/AppData/Local/Temp')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip().startswith('52af400')
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root).strip()
image = ev/'linux-recovery28-image-bc365c1'
assert sha((image/'evidence-manifest.json').read_bytes()) == '15ff83b09c2340195de8677977ce0d9bd4c7e8cc238c7da2607484d63f71b566'
manifest = json.loads((image/'evidence-manifest.json').read_text(encoding='utf-8'))
for name,value in manifest['files'].items():
    assert sha((image/name).read_bytes()) == (value if isinstance(value,str) else value['sha256']), name
closure = temp/'metodobase-linux-owned-shutdown-20261019'
c = json.loads((closure/'after-closure-confirmed.json').read_text(encoding='utf-8-sig'))
assert c['process_absent'] and c['owned_listener_count'] == 0
closed = ev/'linux-owned-shutdown-20261019'
closed.mkdir(exist_ok=False)
for p in closure.iterdir():
    if p.is_file():shutil.copyfile(p,closed/p.name)
shutil.copyfile(Path('F:/MetodoBaseWeb-linux-lab-20261019/scripts/lab_control.py'),closed/'lab_control-frozen.py')
(closed/'README.md').write_text('La VM propia29456 recibió QMP system_powerdown después de que operación cerró sus sesiones y exportó toda evidencia. La primera observación todavía encontró el proceso y se conserva. La segunda confirmó PID y ambos listeners53105/53106 ausentes sin terminación forzada ni apagadoWindows. Se preservan overlay y artefactos para reiniciar después. El runtime de producto no se ejecutó por esta operación.\n',encoding='utf-8')

data = json.loads((run/'TRAZABILIDAD.json').read_text(encoding='utf-8'))
preserved = {r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in data['requisitos']}
rows = {r['id']:r for r in data['requisitos']}
for ident in ['R05','QA-07','R34','R29']:
    r = rows[ident]
    r['commits'].append('52af40007eed53d32d0dca06b06b44dcbf7c64f3')
    r['evidencia'].extend(['evidence/history-landing-ci-independent-20261019/final-summary.json','evidence/history-landing-main-ci-review-20261019/summary.json'])
    r['pruebas'].append('Extensión CI aceptada por QA57dba41:13canarios delta/16inertes,23VM nuevos,30canarios propios,history10/landing8 browser una vez cada uno,4screenscada/0axe-overflow-pageErrors;742fuentes/89paquetes/146deps estables. Históricos21PG/restore28/7fixtures/162VM preservados sinrepetirlos. MAIN52af400 verify-only+13delta verdes,623fuentes/89paquetes quietos,pipcheck0.')
    r['observaciones'].append('CI local integrado; sin ejecuciónGitHubActions/Linux por esta revisión. CierreQA KeyError de clave screenshot corregido en helper separado con originales intactos;sin replay ni cambios decriterio.')
for ident in ['SEC08','R18']:
    r = rows[ident]
    r['evidencia'].append('evidence/linux-recovery28-image-bc365c1/evidence-manifest.json')
    r['pruebas'].append('Imagenbc365c1/99c846bd28b0:55PyPI OSV0;Trivy87OS exit1/142.835s,164entradas/71IDs. MismaDB OCI ybytes exactos:desaparecen sóloDSA-6549-1 yTEMP-1147318-639065 deXZ;0nuevas,otras164idénticas enID/paquete/versión/fix/status/severidad.162affected+2fix_deferred;sinignore.')
    r['observaciones'].append('DeltaDocker/base/bootstrap/liblzma enrevisión de seguridadindependiente antes deintegrar;OSglobalrojo ystartup deproducto pendientes. VM propia cerradaordenadamente trasexportarpruebas para ventana derecursos;sin borrar overlay.')
assert len(data['requisitos']) == 104
for r in data['requisitos']:
    assert {k:r[k] for k in preserved[r['id']]} == preserved[r['id']]
(run/'TRAZABILIDAD.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def append(name,text):
    p=run/name;p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n'+text+'\n',encoding='utf-8')
append('VALIDACION.md','''CI de historial y landing integrado en52af400 tras aceptación independiente57dba41. Verificador13delta/16inertes/65Bash/90refs,23VM y30canariospropios verdes. Browserhistory10/4pantallas ylanding8/4pantallas ejecutados una vez cada uno,0axe/overflow/pageErrors;fuentes742comunes/89paquetes/146deps estables. Elverificador históricoCI28 y21PG/restore28/7fixtures/162VM permanecen íntegros,sinrepetiresosensayos. ComposiciónMAINverify-only/13delta verde,623fuentes/89paquetes quietos,pipcheck0. [QA](evidence/history-landing-ci-independent-20261019/final-summary.json),[composición](evidence/history-landing-main-ci-review-20261019/summary.json). No Actions/Linux/PG/perf por estegate.

Imagenbc365c1/99c846bd28b0:55PyPI OSV0. Trivy sobre87OS finalizóexit1/142.835s:164entradas/71IDs,162affected+2fix_deferred. MismaDB yhashes exactos:elimina sóloDSA-6549-1 yTEMP-1147318-639065 (mismoXZ),sinentradas nuevas;otras164idénticas enID/paquete/versión/fix/status/severidad. [Manifiesto53](evidence/linux-recovery28-image-bc365c1/evidence-manifest.json). Seguridad revisa deltaDocker ymatriz;sinaceptaciónOSglobal. VMQEMUpropia cerradaordenadamente porQMPtrasexportarpruebas;PID29456 ylisteners ausentesconfirmados,overlayconservado. [Cierre](evidence/linux-owned-shutdown-20261019/after-closure-confirmed.json).''')
append('CAMBIOS.md','52af400 integra CI para23VM dehistorial ydosfixturesactuales (history10,landing8),conguardversionado yprimariasfijadas;QAindependienteycomposiciónaceptadas. Conserva21PG/restore28/7fixtures/162VM anteriores ynoejecutaActions poresteincremento.')
append('ENTREGA.md','Actualización local: CIhistory/landing52af400 integrado trasQA ycomposición. CandidatoLinuxbc365c1 finalizóauditoríaOS:71IDs abiertos,sólo2aliasXZ corregidos y0hallazgos nuevos;55PyPI siguenOSV0. Docker aún enrevisiónindependiente. QEMUpropioapagadoordenadamente para ventanaPG/desktop,overlayconservado. No startupdeproductoni nuevoSetup.')
p=run/'ESTADO.md'
t=p.read_text(encoding='utf-8')
t=t.replace('QA está cerrando los negativos propios y navegador secuencial; todavía sin integración ni ejecución de Actions.','QA aceptó el delta, 30 canarios propios y ambos navegadores. Integrado en 52af400; composición verify-only y 13 canarios verdes con 623 fuentes y 89 paquetes estables. Sin ejecución de Actions.')
t=t.replace('Scan OS y comparación en cierre.','Scan OS final: 164 entradas y 71 IDs; desaparecieron exactamente los dos alias de XZ, sin entradas nuevas y con las demás 164 idénticas. Revisión independiente de seguridad en curso; el delta Docker aún no está integrado.')
t=t.replace('Siguiente: cerrar revisión CI y auditoría de imagen candidata; reconstruir desktop corregido en una ventana de memoria;','Siguiente: revisar el delta Docker y los 71 IDs OS abiertos; reconstruir desktop corregido en una ventana de memoria;')
t+='\nLa VM temporal propia cerró de forma ordenada por QMP después de exportar pruebas. PID 29456 y listeners 53105/53106 ausentes; overlay y artefactos conservados. Ventana PostgreSQL reservada para el ensayo focal de 200 solicitudes, con pruebas PG del backend en pausa.\n'
p.write_text(t,encoding='utf-8')
subprocess.run([str(temp/'metodobase-candidate-web-20261018/Scripts/python.exe'),'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True)
docs=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','VALIDACION.md','CAMBIOS.md','ENTREGA.md']
docpaths=[(run/n).relative_to(root).as_posix() for n in docs]
subprocess.run(['git','diff','--check','--',*docpaths],cwd=root,check=True)
subprocess.run(['git','add','--',*docpaths],cwd=root,check=True,capture_output=True)
shutil.copyfile(__file__,ev/'ci-image105-evidence-commit-driver.py')
raw=[ev/'ci-image105-evidence-commit-driver.py']
for folder in ['history-landing-ci-independent-20261019','history-landing-main-ci-review-20261019','linux-recovery28-image-bc365c1','linux-owned-shutdown-20261019']:
    raw.extend(p for p in (ev/folder).rglob('*') if p.is_file())
names=sorted(p.relative_to(root).as_posix() for p in raw)
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=root,check=True,capture_output=True)
buf=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(':'+n+'\n' for n in names).encode())
pos=0;digests={}
for name in names:
    e=buf.index(b'\n',pos);header=buf[pos:e].split();assert header[1]==b'blob'
    size=int(header[2]);blob=buf[e+1:e+1+size];pos=e+size+2
    assert blob==(root/name).read_bytes(),name
    digests[name]=sha(blob)
assert pos==len(buf)
receipt=ev/'ci-image105-raw-preservation.json'
assert not receipt.exists()
receipt.write_text(json.dumps({'new_raw_files':len(names),'git_index_bytes_match_all':True,'pair_hashes_sha256':sha(json.dumps(digests,sort_keys=True,separators=(',',':')).encode()),'image_manifest_files_rehashed':len(manifest['files']),'historical_criteria_preserved':104,'scope':'Only exact owned proof files (including original QA bytecode named by its manifest); CRLF/UTF16/whitespace retained. Docs whitespace checked separately. No historical rewrite or runtime change.'},indent=2)+'\n',encoding='utf-8')
subprocess.run(['git','-c','core.autocrlf=false','add','--',receipt.relative_to(root).as_posix()],cwd=root,check=True,capture_output=True)
staged=set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1])
assert staged==set(names+docpaths+[receipt.relative_to(root).as_posix()])
subprocess.run(['git','commit','-m','docs: accept CI composition and preserve final Linux OS comparison'],cwd=root,check=True,capture_output=True)
print(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'raw_files':len(names),'all_raw_index_identical':True,'registry':104}))
