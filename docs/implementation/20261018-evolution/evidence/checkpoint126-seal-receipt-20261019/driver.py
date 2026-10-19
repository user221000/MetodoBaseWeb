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

root=Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
run=root/'docs/implementation/20261018-evolution';ev=run/'evidence'
base='cac63688a2e677374518d0e0537f2a1ae617ee5c'
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
sha=lambda blob:hashlib.sha256(blob).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
receipt=json.loads((tmp/'metodobase-checkpoint126-import-result.json').read_bytes())
raw={root/name for name in receipt['files']}
for path in raw:
    meta=receipt['files'][path.relative_to(root).as_posix()];blob=path.read_bytes()
    assert len(blob)==meta['bytes'] and sha(blob)==meta['sha256'];scan(blob,path.name)
data=json.loads((run/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda value:{r['id']:{field:r[field] for field in fields} for r in value['requisitos']}
before=criteria(data);assert len(before)==124
notes={
 'R18':'Imagen f74 construida una vez:147.922s exit0, digestdc8fab52ffd440399baba71923aba008d54ebfbcf503d149b933b15f9ada62e3.54metadata/imports/355fuentes/USERreal999:999/218base/11XML/native0f618/5argv/1export medidos. Migración31,health200/ready200/Dockerhealthy/PID1sinMIGRATOR observados. Config.Env inicialsíconservaURL:dockerexec noheredaunsetdePID1. WorkerINCOMPLETO:2criteriosdelobservador eranmásampliosquecontrato (prefijomfa_ y19funcsuniversal;25FORCE/20funcsobservadas). Sin cambio producto ni replay; selloPARTIAL. SQL/Redis/appcerrados,UUID/2rolespropiosausentes/viejosintactos,VMownOFFporQMP.',
 'R25':'Restore32independiente sobre345aa7 PASS:1casomantenido60asserts,inversa58originalexacta,original31intacto. ControlesHTTPweb/apiMFAconpassword/recovery originalesrestaurados;progresocontrolesusanpasswordspreparadasdespuésdelrestore declarado,nocredencialesrestauradas.34físicas/26FORCE/rev32/4flagsfalse/nonowner/pool1.2UUIDleasesexclusivas/OID,cierrecero sesiones/DROPnormal/freshausencia;797fuentes89metadataPythonPGperfilinfraquiet,pip0/0. FlujopurposepadreOFFpassword+MFAenimplementación,wirecongeladoperoaúnnoaceptado;CI32/matrizcomúnpendientes.',
 'R31':'Retiroexcepcionalenimplementación conpasswordreal+factoractivo en cadaoperación/página,sinJWT/challenge/grant niDDL;Google-only/pérdidatotal noresueltos. ContratoGoogleestático separado:transportetokeninfofijoyaudverified,porlotantonobypassfirmademostrado; faltaasociaciónsubenGooglelogin/reauthporEmail requiereSECreviewdinámica. No cerrarderechosdeprivacidadporrestore.',
 'R32':'Investigaciónestática deGoogleasociaciónemail/sub pendiente de4canarios+4controlesindependientes. DocsGoogle recomiendansub ypruebaadicionalpara emailthirdpartyverifiedsinhd; nosuponerinvalideztokeninfo. RetiroparentOFFnuevo passwordonlyfailclosedGoogle,noalterarautogeneralaún. Alertas/custodia/rotación/proveedores/lostallfactorcontinúanpendientes.',
 'R02':'Posiblehallazgonuevo enlacedeidentidadGoogleestáenrevisión independiente; noeselcriteriopreviodetransformaciónderol. Rootregistrófuentes/docsoficiales sincredencialesniproveedorreal. Noautovincularsubniinferirbackfill aquí.',
 'R19':'Serialde506única con cobertura continúa;3057previstos y3047IDsanteriores requeridos. N2noiniciado. Restore32separadonoesregresiónamplia31. Sin nuevasbroads durantepresiónRAM:OpscerróVMpropia yQARestoreesperóguard1.8GiB antesCREATE.',
 'OPS14':'Logging474 observado ahora enCMDproducción:Migration completed and verified at revision20261019_mfa, seguido dearranque. No atestaciónworkercompletaporcriteriosharnesspropioserrados; noreescribirlos.',
 'SEC10':'ImagennuevausaELF0f618medido/54imports/355fuentes yOpenSSLsistema3.5.7frentecryptography4.0.3. Compilaciónnativareutilizócache72, noafirmarnuevoGCC. NocompletaSCA71niworker/producciónporprobehealth.',
}
refs={
 'R18':['runtime31-f74a-logging-partial-public-20261019/source.json'],
 'R25':['qa-progress32-populated-restore-independent-20261019/source.json'],
 'R31':['root-google-subject-contract-review-20261019/provider-contract.json'],
 'R32':['root-google-subject-contract-review-20261019/source.json'],
 'R02':['root-google-subject-contract-review-20261019/source.json'],
 'OPS14':['runtime31-f74a-logging-partial-public-20261019/source.json'],
 'SEC10':['runtime31-f74a-logging-partial-public-20261019/source.json'],
}
for row in data['requisitos']:
    if row['id'] in notes:row['observaciones'].append('Checkpoint126: '+notes[row['id']])
    for ref in refs.get(row['id'],[]):
        assert (ev/ref).is_file(),ref
        name='evidence/'+ref
        if name not in row['evidencia']:row['evidencia'].append(name)
assert criteria(data)==before
(run/'TRAZABILIDAD.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
state=(run/'ESTADO.md').read_text(encoding='utf8').split('\n\n')
def replace(prefix,text):
    positions=[i for i,value in enumerate(state) if value.startswith(prefix)];assert len(positions)==1,prefix
    state[positions[0]]=text
replace('Checkpoint 125 local.', 'Checkpoint 126 local. El registro conserva 124 requisitos y los 124 criterios anteriores exactos, incluidos los 92 IDs originales. MAIN sigue en esquema 30; candidatas 31 y 32 aisladas. Free: diez clientes activos, un plan por cliente al día y diez totales por gimnasio al día. Desktop continúa soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales.')
replace('El logging de Alembic', 'La imagen f74 se construyó una vez en147.922s: digest dc8fab52. Operación midió 54 paquetes/imports,355 fuentes,USER999:999,ELF0f618 y sus contratos nativos. El CMD exacto confirmó migración31 y logging474,health200,ready200 y Dockerhealthy; PID1 no conserva MIGRATOR_DATABASE_URL, aunque Config.Env inicial sí lo contiene. La atestación del worker quedó incompleta por dos criterios del harness demasiado amplios: prefijo mfa_ y conteo universal de19funciones. Se conservan los errores; no se modificó el producto ni se repitió el intento. App,Redis6388 y PG55486 cerraron; UUID y dos roles nuevos ausentes sin FORCE, objetos antiguos intactos. La VM29408 se apagó por QMP cooperativo, conservando imagen y discos. [Sello parcial](evidence/runtime31-f74a-logging-partial-public-20261019/source.json).')
replace('El retiro propio con autoridad parental', 'La restauración32 independiente pasó sobre345aa7:1caso mantenido/60asserts,inversa58 exacta y controlesHTTP propios en web/api. Los factores MFA se probaron con credenciales originales restauradas; las contraseñas de los actores de progreso se prepararon después y no se atribuyen al backup. Dos bases propias con lease exclusiva y OID cerraron sin sesiones ni FORCE;34tablas/26FORCE/revisión32/pool1 y797fuentes/89paquetes/Python/PG estables. El retiro con autoridad parental inactiva está en implementación separada, con primaria+factor nueva por cada consulta/retirada y sin sesión general; Google-only y pérdida total siguen pendientes. Su wire está congelado, no su aceptación. CI32 y matriz común siguen pendientes. [Restore](evidence/qa-progress32-populated-restore-independent-20261019/source.json), [diseño](evidence/security-progress32-reader-review-independent-20261019/retirement-design.md).')
replace('Siguiente acción:', 'Siguiente acción: completar serial de506 y n2; preparar un sucesor focal del observador worker con el contrato31 exacto, sin rebuild ni reescribir errores. Continuar retiro propio/API/UI, su revisión de Seguridad y QA, CI32 y posterior composición. Revisar la asociación Google por sub con canarios independientes antes de clasificar el hallazgo. [Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).')
(run/'ESTADO.md').write_text('\n\n'.join(state),encoding='utf8')
(run/'ENTREGA.md').write_text('''# Entrega candidata en curso

Checkpoint126:124 requisitos y124 criterios anteriores exactos,92 IDs originales. MAIN sigue en esquema30. La candidata31 de506 está en serial con cobertura; n2 pendiente. SEC15, ambos helpers MFA y logging tienen aceptación focal independiente; no sustituyen la regresión completa.

Imagen f74/digestdc8fab52: una build,54imports/metadatos,355fuentes,USER999,head31/health200/ready200/PID1sinMIGRATOR medidos. Worker incompleto por dos criterios del observador más amplios que el contrato. Errores conservados, sin replay ni modificación de políticas. Servicios propios cerrados; VM apagada y artefactos retenidos. [Sello parcial](evidence/runtime31-f74a-logging-partial-public-20261019/source.json).

32: lector/UI y reparaciones345 revisados acotadamente; restore independiente1caso/60asserts más controlesHTTP pasa. Retiro propio sinlogin general está en implementación, Google-only/lostfactors pendientes. CI32, matriz común y asociación Google por sub requieren revisión. [Restore](evidence/qa-progress32-populated-restore-independent-20261019/source.json).

Free:diez clientes activos,un plan por cliente al día y diez totales por gimnasio al día. Desktop soportado. Sin push, PR, despliegue, cargos ni comunicaciones reales. [Estado](ESTADO.md), [registro](TRAZABILIDAD.md), [validación](VALIDACION.md).
''',encoding='utf8')
for name,text in {
 'VALIDACION.md':notes['R18']+' '+notes['R25'],
 'CAMBIOS.md':'MAIN sólo registra pruebas y control. Runtimef74 app6a75/native72/logger474 medido con su USERreal y firststartup; noatribución32. Nuevo retiro API/UI permanece en WT independientes desde345 conwire5b6de9 congelado. Ningún cambio producto en este checkpoint.',
 'DECISIONES.md':'No ampliar RLS ni alterar funciones para satisfacer asserts impropios del observador. Usar verify_runtime_schema congelado y allowlist25FORCE en el futuro worker. Preservar primererror/continuaciónreadonly con prefijos distintos del futuro sucesor. Apagar sólo VM propia por QMP tras cierre de servicios y fotos de identidad. No considerar contraseñas preparadas postrestore como restauradas. ContratoGoogle: separar autoridad criptográfica tokeninfo de asociaciónlocalpor email; no usar mocks imposibles como exploit real.',
 'RIESGOS.md':'Worker31 todavía sin atestación completa; source/image parcial no habilita despliegue. Serial/n2 y matrizcomún32 pendientes. Retiroexcepcional yGoogle-only requieren pruebas; asociaciónsub nuevaDDL/backfillnoautorizada por inferencia ni implementada todavía. VMOFF liberóRAM después de presión observada; QA esperó1.8GiB antesCREATE, no se tocó proceso ajeno. Las dependencias de políticas, países, retención, SLO, pilotos y especialista permanecen abiertas.',
}.items():
    with(run/name).open('ab')as handle:handle.write(('\n\n## Checkpoint126\n\n'+text+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=root,check=True,capture_output=True)
assert criteria(json.loads((run/'TRAZABILIDAD.json').read_bytes()))==before
seal=ev/'checkpoint126-seal-receipt-20261019';assert not seal.exists();seal.mkdir()
(seal/'.gitattributes').write_bytes(b'* -text\n');(seal/'driver.py').write_bytes(Path(__file__).read_bytes())
(seal/'receipt.json').write_bytes((json.dumps({'base':base,'registry':124,'previous_criteria_exact':124,'new_ids':[],
 'main_product_changed':False,'files':{path.relative_to(root).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(raw)}},indent=2)+'\n').encode())
raw.update(path for path in seal.iterdir() if path.is_file());names=sorted(path.relative_to(root).as_posix() for path in raw)
docs=[(run/name).relative_to(root).as_posix() for name in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for offset in range(0,len(names),25):subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[offset:offset+25]],cwd=root,check=True,capture_output=True)
subprocess.run(['git','add','--',*docs],cwd=root,check=True,capture_output=True)
for name in names:assert git('show',':'+name)==(root/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+docs)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=root,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Preserve partial production smoke and independent populated schema32 restore'],cwd=root,check=True,capture_output=True)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'head':git('rev-parse','HEAD').decode().strip(),'registry':124,'criteria_exact':124,'RAW_authenticated':len(names),'main_product_changed':False}))
