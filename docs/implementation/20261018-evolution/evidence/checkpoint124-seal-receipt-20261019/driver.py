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
base='6992043daa0df54da9a9c619a6e92cf7948f15d6'
sha=lambda blob:hashlib.sha256(blob).hexdigest()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
data=json.loads((run/'TRAZABILIDAD.json').read_bytes());fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{r['id']:{field:r[field] for field in fields} for r in value['requisitos']}
before=criteria(data);assert len(before)==119 and 'SEC15' not in before
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
native=Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\expat-sec10-72c-native-candidate-20261019')
manifest=(native/'manifest.json').read_bytes();assert sha(manifest)=='0ec7fbc00d6c8c83c17d8a9e6e4eedaddb11ef8dfdd7f3a3b1717067d243568a'
originals={}
for name,meta in json.loads(manifest).items():
    assert set(meta)=={'bytes','sha256'}
    blob=(native/name).read_bytes();assert len(blob)==meta['bytes'] and sha(blob)==meta['sha256']
    scan(blob,name);originals[name]=blob
attestation=(native/'source.json').read_bytes();assert sha(attestation)=='11352bc3a4afd16e69ed52c92f10ed9786f85a1ae2caf54633e6f9189fb37ee7'
originals['source.json']=attestation;scan(attestation,'source.json')
target=ev/native.name;assert not target.exists();target.mkdir()
(target/'.gitattributes').write_bytes(originals.get('.gitattributes',b'* -text\n'))
for name,blob in originals.items():
    path=target/name;assert path.resolve().is_relative_to(target.resolve())
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
(target/'manifest.json').write_bytes(manifest)

reviews=[
 ('expat-sec10-72c-native-candidate-20261019','0ec7fbc00d6c8c83c17d8a9e6e4eedaddb11ef8dfdd7f3a3b1717067d243568a'),
 ('security-expat-72c-native-independent-20261019','492397f2198544f6a0f559dda043c9000c476cda667e4c5c053bd311305d596f'),
 ('root-mfa31-composed-serial-diagnostic-20261019','c20836dcf9c6b72ab1c4a1125d37e56d7164e3dc9001977bed831cb94636b80c'),
 ('root-mfa31-terminal-sv-author-20261019','5d8220d6623bd585b50319de6afddaebb056bb3128e5cabdb9fa1cc3e66c6d6a'),
]
raw=set()
for prefix,digest in reviews:
    parent=ev/prefix;path=parent/'manifest.json';blob=path.read_bytes();assert sha(blob)==digest
    document=json.loads(blob);rows=document.get('files',document)
    if isinstance(rows,dict):rows=[{'path':name,**meta} for name,meta in rows.items()]
    for row in rows:
        assert ('sha256' in row)!=('SHA256' in row)
        path=parent/row.get('path',row.get('file',''));blob=path.read_bytes()
        assert path.resolve().is_relative_to(parent.resolve()) and sha(blob)==row.get('sha256',row.get('SHA256'))
        assert 'bytes' not in row or len(blob)==row['bytes']
        scan(blob,path.name);raw.add(path)
    assert (parent/'.gitattributes').read_text(encoding='ascii').strip()=='* -text'
    raw.update([parent/'manifest.json',parent/'.gitattributes'])
for prefix,digest in [
 ('expat-sec10-72c-native-candidate-20261019','11352bc3a4afd16e69ed52c92f10ed9786f85a1ae2caf54633e6f9189fb37ee7'),
 ('security-expat-72c-native-independent-20261019','8c8f6d2b0a8713520126ef63923b66c216f2ccadb9fbcc35f9ba3124431327e7')]:
    path=ev/prefix/'source.json';assert sha(path.read_bytes())==digest;scan(path.read_bytes(),path.name);raw.add(path)

prepared=ev/'prepared-wave124-20261019';assert not prepared.exists()
contents={'driver.py':Path(__file__).read_bytes()}
for prefix in ['metodobase-mfa31-runtime72-compose-20261019','metodobase-r25-router-mount-20261019']:
    for path in (tmp/prefix).iterdir():
        assert path.is_file();contents[prefix+'/'+path.name]=path.read_bytes()
for name in ['driver.py','manifest.json']:
    contents['runtime-context/'+name]=(tmp/'metodobase-mfa31-runtime72-context-20261019'/name).read_bytes()
wire=Path(r'F:\mb-r25-progress32-20261019\docs\implementation\20261018-evolution\evidence\backend-r25-progress32-20261019\wire-v1.json').read_bytes()
assert sha(wire)=='982c26596daaf6a315661151ab8ad76bb42a61290dcec7bc6833e3c5aa7533a0'
contents['R25/wire-v1.RAW.json']=wire
ui=Path(r'F:\mb-r25-progress-ui-20261019\docs\implementation\20261018-evolution\evidence\r25-ui\prepared-source.json').read_bytes()
assert sha(ui)=='955703b95fad0a09a8bf15b902054712f50c0dfa044870a1a5237c14436e1a8d'
contents['R25/ui-prepared-source.RAW.json']=ui
for name,blob in contents.items():scan(blob,name)
prepared.mkdir();(prepared/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in contents.items():
    path=prepared/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob);raw.add(path)
(prepared/'manifest.json').write_bytes((json.dumps({name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in contents.items()},indent=2)+'\n').encode())
raw.update([prepared/'manifest.json',prepared/'.gitattributes'])

row={'id':'SEC15','identificador_original':'SEC15',
 'fuente':'docs/implementation/20261018-evolution/evidence/root-mfa31-composed-serial-diagnostic-20261019/summary.STRUCTURAL.json',
 'seccion':'Hallazgo nuevo checkpoint124','problema':'MFA rechaza como identidad inválida la versión de sesión máxima que la recuperación de cuenta acepta legítimamente, bloqueando el nuevo login de ambas factories.',
 'criterio_exacto':'Mantener válida la identidad entera SV=2147483647 para acceso y verificación de factor sin emitir tokens antes de la prueba requerida; impedir con rechazo explícito y sin consumo de factor/proof/sesiones todo cambio que necesite incrementar ese contador. No envolver, decrementar ni reiniciar SV y conservar las pruebas originales de recuperación, límites y permisos.',
 'prioridad':'P2','responsable':'Backend y seguridad','tareas':['R19','R29','R32'],'dependencias':['R29','R32'],
 'estado':'en_revision','implementacion':'en_revision','validacion':'en_curso','despliegue':'no_desplegado','entorno':'local',
 'cambios':['Fix aislado6a75 acepta identidadMAX y aplica guard409 antes de enrollment/confirm/change y antes del incremento; UI añade sólo mensaje. Compuesto sólo en candidata aislada.'],
 'commits':['6a75d096ea3d63d9e78c76d33b7e243160b23364'],
 'pruebas':['Mismos14:before10fallos+4controles;after14verdes. Ocho casos nuevos, dos replays de borde y cuatro controles existentes; tres drivers Node mantenidos exit0.'],
 'evidencia':['evidence/root-mfa31-composed-serial-diagnostic-20261019/summary.STRUCTURAL.json','evidence/root-mfa31-terminal-sv-author-20261019/source.json'],
 'documentacion':['ESTADO.md','VALIDACION.md','DECISIONES.md'],'revisor':'Seguridad independiente pendiente','bloqueo':None,
 'observaciones':['Hallazgo de borde sintético; no se afirma incidencia real de producción. Nueva regresión serial en curso; n2 aún pendiente.']}
data['requisitos'].append(row)
notes={
 'R18':'72c target nativo aceptado sólo como diagnóstico por Ops y Seguridad:5argv registrados ligados a4ELF,base/new1export,31PSF,218base,libpq170011/OpenSSL3.5.7. SEC ejecutó16XML+19contratos una vez, sin nuevosgcc;recuentos87→97→135. Runtime completo c538(app809+native72) enbuild/diagnóstico, no54/startup/SCA acreditados.',
 'R19':'Fullserial809:3039=3036pass+2fail+1skipWindows,1213.125s sin claim temporal.10178fuentes89paquetes/Pythonquiet,pips0.2598IDsanteriores conservados;gatecobertura pasa. Dos fallos originales de recovery loginMAX sonSEC15; mismo14fix6a75green, peer pendiente. Nueva fullserial6a75 inició19:55UTC, n2 pendiente.',
 'R25':'Ramas32 en curso, no integradas. APIrouter montado porROOT en ambasfactories con inversas yRAWbefore; wire sintético v1SHA982c fijo. UIc7ee06d preparatoria52VM+2SSR ybefore2×404; API/MFA/R24 originales intactos enesa fase. Discovery/retiro propios accesibles aOWNER/usuario ambiguo sinperfil/medida/grant; UserOFF/ON mismo vínculo no extingue por sí solo consentimiento no retirado. Lector mismaConnection/SAVEPOINT requiereSEC. Resultados37SQLite+11PG deautor son fases preliminares, nofreeze32aceptado.',
 'R29':'Broad detectó loginNEW401 después del último reset elegible, en ambasfactories; nuevoSEC15. No se cambia ninguna assertion original. Fix6a75 con14autor verdes, peer/broad nuevos pendientes.',
 'R32':'SEC15 separa identidadMAXválida de capacidad de incrementarSV; nofactorbypass. Appcandidata6a75 con nueva serial; runtimec538 aúncontiene809 sinfix y se trata sólo como diagnóstico. Avisos/custodia/rotación/configreal/pérdidatotal siguen pendientes.',
 'OPS11':'HeaderClinic31 ya superó compilación72 y diagnóstico nativo independiente acotado; fullruntime/SCA aún pendientes.',
 'OPS12':'72c5argv registrados reales ligados a4objetosELF, aceptados acotadamente porSEC. Revisor no observó gcc nuevos; comprobó registros preservados y objetos de imagen. de69argvvacío permanece intacto.',
 'OPS13':'ParserELF propio yprobeSEC72 confirman base/new sóloPyInit_pyexpat,delta0;93DE69 preservados. No cierre globalSEC10 niimagen completa.',
 'SEC10':'72c nativo PASS_NATIVE_INDEPENDENT_DIAGNOSTIC_ONLY:16XML+19contratos,5argv/4obj/1export/31inputs/218base.43primarias y18outputs autenticados;sinrebuild enSEC. Fullruntime54/SCA71/imagencomún pendientes.',
}
refs={
 'R18':['expat-sec10-72c-native-candidate-20261019/source.json','security-expat-72c-native-independent-20261019/source.json'],
 'R19':row['evidencia'],'R29':row['evidencia'],'R32':row['evidencia'],
 'R25':['prepared-wave124-20261019/R25/wire-v1.RAW.json','prepared-wave124-20261019/R25/ui-prepared-source.RAW.json','prepared-wave124-20261019/metodobase-r25-router-mount-20261019/receipt.json'],
 'OPS11':['security-expat-72c-native-independent-20261019/source.json'],'OPS12':['security-expat-72c-native-independent-20261019/source.json'],
 'OPS13':['security-expat-72c-native-independent-20261019/source.json'],'SEC10':['security-expat-72c-native-independent-20261019/source.json'],
}
for item in data['requisitos']:
    ident=item['id']
    if ident in notes:item['observaciones'].append('Checkpoint124: '+notes[ident])
    for ref in refs.get(ident,[]):
        value=ref if ref.startswith('evidence/') else 'evidence/'+ref
        if value not in item['evidencia']:item['evidencia'].append(value)
assert len(criteria(data))==120 and {ident:criteria(data)[ident] for ident in before}==before
(run/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
paragraphs=(run/'ESTADO.md').read_text(encoding='utf8').split('\n\n')
def replace(prefix,value):
    indexes=[index for index,text in enumerate(paragraphs) if text.startswith(prefix)];assert len(indexes)==1,prefix
    paragraphs[indexes[0]]=value
replace('Checkpoint 123 local.', 'Checkpoint 124 local. El registro conserva120requisitos:92originales y28hallazgos añadidos. Los119criterios anteriores permanecen exactos; se añadeSEC15 por el login rechazado en la versión de sesión terminal. MAIN sigue en esquema30 y el workspace original permanece intacto. Free:diez clientes activos,un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push,PR,despliegue,cargos ni comunicaciones reales.')
replace('La candidata MFA31 está aislada', 'La candidata MFA31 está aislada en6a75d096ea3d63d9e78c76d33b7e243160b23364. La regresión completa anterior809 terminó3039casos:3036aprobados,dos fallos originales de recovery y un skipWindows conocido. Conservó los2598IDs anteriores y pasó la cobertura requerida;10178archivos,89paquetes yPython estables,pipcheck verde. Los dos fallos son loginNEW401 al llegar legítimamente aSVmáximo. Fix6a75 separa identidad válida de capacidad de incremento:el mismo14 pasó de10rojos+4controles a14verdes, sin cambiar asserts originales. Añade8casos nuevos; tres drivers Node mantenidos también pasan. Falta revisión independiente. Nueva regresión completa serial con cobertura iniciada19:55UTC; n2 pendiente. [Diagnóstico rojo](evidence/root-mfa31-composed-serial-diagnostic-20261019/summary.STRUCTURAL.json), [fix de autor](evidence/root-mfa31-terminal-sv-author-20261019/source.json).')
replace('Linux:', 'Linux:72c tiene aceptación nativa independiente sólo diagnóstica. Ops compiló el target y Seguridad ejecutó una vez16XML pequeños y19contratos en la misma imagen. Confirmó5argv registrados ligados a4objetosELF,único exportPyInit,31inputsPSF,218identidadesbase,libpq17.11 yOpenSSL3.5.7;recuentos87→97→135. Seguridad no observó nuevosgcc ni inventó una foto histórica propia. D60rojo,de69argvvacío/93exports ytodos sus contextos permanecen intactos. Root preparó c538 con app809 exacta+native72 y366Gitblobs de contexto18493440bytes; imagen runtime completa enbuild/diagnóstico. C538 aún no contiene el fixSV y no representa aceptación común. No runtime54,startup,SCA/OS71 ni cierreSEC10 acreditados. [Nativo propio](evidence/expat-sec10-72c-native-candidate-20261019/source.json), [independiente](evidence/security-expat-72c-native-independent-20261019/source.json).')
replace('R25 empezó', 'R25 sigue separado enbackend/UI32, sin integración ni aceptación final. RouterAPI montado enambasfactories; wirev1 sintético e inmutable982c fijaDTO/export8. UIpreparatoriac7ee06d tiene52VM+2SSR ybefore2×404. Retiro/listado mínimo propio sobreviven a vínculos ocultos y cambio de rol aOWNER, sin adoptarperfil/cartera ni habilitargrant. Un consentimiento retirado nunca revive; el OFF→ONde la misma cuenta y mismo vínculo no es por sí solo una retirada. Backend conserva fases preliminares37SQLite+11PostgreSQL verdes, bases propias cerradas sinFORCE; código posterior yrestore32 aún pendientes de congelar/revisar. Lector sólo sobre mismaConnection/SAVEPOINT, sinGUCfirma ni función pública de sujeto; requiereSEC. DDL32 sigue exclusivo. [Wire](evidence/prepared-wave124-20261019/R25/wire-v1.RAW.json).')
replace('Siguiente acción:', 'Siguiente acción: revisión independienteSEC15 y completar la nueva serial/n2; validar la imagen runtime y actualizar su fuente con el fix cuando proceda. Continuar R25,restauración32 y revisión del lector antes de integrar. [Registro](TRAZABILIDAD.md).')
(run/'ESTADO.md').write_text('\n\n'.join(paragraphs),encoding='utf8')
(run/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint124:120requisitos,92originales y119criterios anteriores exactos. MAIN permanece en esquema30. La candidata31aislada6a75 corrigeSEC15; autor14focales verdes, peer y nueva regresión serial pendientes; n2 no iniciado.

La serial809 roja se conserva:3036pass,2fallos recovery loginMAX y1skipWindows. Conserva2598IDs previos y cobertura requerida; no es aceptación completa.

Expat72 tiene aceptación nativa independiente sólo diagnóstica. Imagen runtimec538(app809+native72) en construcción/pruebas; aún sinfixSV ni aceptación común. R25backend/UI32 avanzan separados conwirev1 fijo y sinfreezeaceptado.

Free:diez clientes,un plan por cliente al día y diez totales por gimnasio al día. Desktop sigue soportado. Sin push,PR,despliegue,cargos ni comunicaciones reales. [Estado](ESTADO.md),[registro](TRAZABILIDAD.md),[validación](VALIDACION.md).
''',encoding='utf8')
for name,text in {
 'VALIDACION.md':'Serial809:3039=3036pass+2fail+1skipWindows;2598IDs preservados y cobertura pasa, fuente10178/89paquetes/Pythonquiet,pips0. SEC15mismo14before10rojos4controles→after14green,8nuevos y6replays;3NodeVMexit0. Peer y nueva fullserial6a75 en curso,n2 pendiente. Native72independiente16XML+19contratos verde, argv registrados ligados a objetos; no nuevosgcc ni falsa prephoto propia.',
 'CAMBIOS.md':'SEC15 añade identidadSVmáximo válida y guard409 de capacidad antes de cambiar factor, sin wrap/decremento ni assertions antiguas alteradas. MAIN sólo registra evidencia. Runtimec538 combinaapp809+native72;366Gitblobs contextoconSHA22fc3b52, sin secretos/DB/docs/tests/assetsreferencia. R25router montado ywirev1 fijo, sinproducto32 aceptado.',
 'DECISIONES.md':'No arreglar el fallo de recuperación cambiando suassert. Separar identidadválida de capacidad de incrementarSV. Conservar809rojo y repetir fullmatrix con fuente nueva y nombres distintos. Retiropropio es exclusión de permisos y admiteOWNERambiguo sólo sobre user_id persistido propio; no espacio personal ni cartera. Reactivación de vínculo revocado no adopta grants; togglecuenta sin retirar consentimiento no equivale a revocación.',
 'RIESGOS.md':'Pendientes peerSEC15,nueva fullserial/n2, imagen runtime ysourcefixposterior. Native72diagnóstico no cierra54/SCA71/SEC10. R25lector/restore32/freeze e integración pendientes. ConfiguraciónMFA,avisos,custodia,rotación,políticas,objetivos,pilotos ydictámenes siguen sin inventarse.',
}.items():
    with(run/name).open('ab') as handle:handle.write(('\n\n## Checkpoint124\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
assert {ident:criteria(json.loads((run/'TRAZABILIDAD.json').read_bytes()))[ident] for ident in before}==before
seal=ev/'checkpoint124-seal-receipt-20261019';assert not seal.exists();seal.mkdir()
(seal/'.gitattributes').write_bytes(b'* -text\n');(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
(seal/'receipt.json').write_bytes((json.dumps({'base':base,'registry':120,'previous_criteria_exact':119,'new_ids':['SEC15'],'main_product_changed':False,'authenticated_manifests':reviews,
 'files':{path.relative_to(root).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(raw)}},indent=2)+'\n').encode())
raw.update(path for path in seal.iterdir() if path.is_file());names=sorted(path.relative_to(root).as_posix() for path in raw)
docs=[(run/name).relative_to(root).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for start in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[start:start+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(root/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Record native diagnostic acceptance and preserve terminal-session regression repair'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':120,'previous_criteria_exact':119,'RAW_authenticated':len(names),'main_product_changed':False}))
