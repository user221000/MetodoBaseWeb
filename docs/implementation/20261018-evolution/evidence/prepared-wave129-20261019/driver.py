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

ROOT=Path('F:/MetodoBaseWeb-execution-20261018')
TMP=Path('C:/Users/Consu/AppData/Local/Temp')
RUN=ROOT/'docs/implementation/20261018-evolution'
EV=RUN/'evidence'
BASE='3587b3b3eee3a58367624472d7c0683baa8f10e0'
CONTROL=TMP/'metodobase-checkpoint129-20261019';CONTROL.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*args,check=True):return subprocess.run(['git','--no-replace-objects',*args],cwd=ROOT,capture_output=True,check=check)
def blob(ref,name):return git('show',ref+':'+name).stdout
def names(ref,prefix):return [n for n in git('ls-tree','-r','--name-only','-z',ref,'--',prefix).stdout.decode().split('\0') if n]
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain=v1','-uno').stdout.strip()
definition=next(n for n in ast.parse((TMP/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
pre='docs/implementation/20261018-evolution/'
imports={}
checks=[
 ('bfbfcefd9f970893af6c306438f654a6df65e9c0','evidence/backend-google-subject33-20261019','manifest.json','37bb5b36411306e8cb2884933522d2d916b5353f8fc34435d98082e84a1fa41e'),
 ('a02a9ac04e0c619f6754bc86d89680d1a6bf95a0','evidence/google-link-ui','proofs.json','7fc3681ee464091d0e46124b91371a4629154c80c561b446fdcee926feec097d'),
 ('d536130a9b90c8f4a6f5c8f07f15341d2e07f88e','evidence/security-gitleaks-triage-independent-20261019','manifest.json','f22d9976486bb5f240dfed10d04fde9da0f95cadb7d9fad1a6115786b0b69d0b'),
 ('a704f0706827d9e02392902737ed96ef4ce8d764','evidence/security-r05-registry-independent-20261019','manifest.json','1833fd858ab209de8922d709e7d7e0f4b15b877e101a692a1ffef787726c0e5e'),
 ('57a036568ac74b7480cca8d4b3af0f79863ba879','evidence/root-r05-finite-reviewed-author-20261019','manifest.json','de35fea1a57db5b85df2d88fde47e16a435f8d571204dd41e2cf85b1eda3b4ea'),
 ('5993a5e652655a319d277aeaa7165a1623146efb','evidence/qa-ci33-offline-preparation-20261019','manifest.json','fc2a4b66b5377cab894a8d9562c4b8f0ae82ce049defaa5bff4a9afe43ccb44d'),
 ('46ba41b5d9567be987c96e1130147ca97d61eb22','evidence/followup-tasks-ui','manifest.json','bf1521ddd40bd2b634615a23cfbb23ce5e0856f2615835abff2cd46a565ce7ca')]
for ref,prefix,manifest,digest in checks:
    assert sha(blob(ref,pre+prefix+'/'+manifest))==digest,(prefix,manifest)
    for name in names(ref,pre+prefix):
        assert name not in imports and not (ROOT/name).exists(),name
        imports[name]=(ref,blob(ref,name))
for ref,name in [('bfbfcefd9f970893af6c306438f654a6df65e9c0','GOOGLE_IDENTIDAD_ASOCIACION.md'),
    ('a02a9ac04e0c619f6754bc86d89680d1a6bf95a0','GOOGLE_VINCULO_UI.md'),
    ('46ba41b5d9567be987c96e1130147ca97d61eb22','SEGUIMIENTO_TAREAS_UI_PROPUESTA.md')]:
    name=pre+name;assert name not in imports and not (ROOT/name).exists();imports[name]=(ref,blob(ref,name))
for name,(ref,payload) in imports.items():scan(payload,name)
for name in sorted(imports,key=lambda n:(n.rsplit('/',1)[-1]!='.gitattributes',n)):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(imports[name][1])
prepared=EV/'prepared-wave129-20261019';assert not prepared.exists();prepared.mkdir();(prepared/'.gitattributes').write_bytes(b'* -text\n')
composition=TMP/'metodobase-google33-common-compose-20261019'
common=json.loads((composition/'frozen-common.json').read_bytes())
assert common['head']==BASE and common['source_counts']=={'imports':58,'exact_producer_Git_bytes':57,'one_test_EOF_only':1}
for row in common['sources']:
    assert (ROOT/row['path']).read_bytes()==blob(BASE,row['path'])
    assert sha((ROOT/row['path']).read_bytes())==row['composed_digest']
payloads={'source-equivalence.json':enc(common),'backend-wire34-proposal.json':Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r23-wire34-proposal-4kaosqhd/wire34-proposal.json').read_bytes()}
assert sha(payloads['backend-wire34-proposal.json'])=='844beab65ffb141c960bc51576f822e11ef3d49eed7fe9a1ec4330bf22fe9f38'
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(composition.iterdir()):
        if path.is_file():z.writestr(path.name,path.read_bytes())
payloads['composition-originals.zip']=buf.getvalue()
triage_phases=['metodobase-r05-current-fingerprint-triage-20261019','metodobase-r05-current-historical-triage-20261019',
    'metodobase-r05-current-artifact-triage-20261019','metodobase-r05-current-evidence-triage-v2-20261019',
    'metodobase-r05-current-objectid-triage-20261019']
buf=io.BytesIO();counts=[]
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
    for phase in triage_phases:
        directory=TMP/phase
        for path in sorted(directory.iterdir()):
            if path.is_file():z.writestr(phase+'/'+path.name,path.read_bytes())
        counts.append(json.loads((directory/'summary.json').read_bytes()))
    for pattern in ['metodobase-r05-current-*-derivation-20261019.json','metodobase-r05-current-*-prepare*-20261019.py']:
        for path in sorted(TMP.glob(pattern)):z.writestr('derivations/'+path.name,path.read_bytes())
payloads['current-r05-candidate-triage.zip']=buf.getvalue()
payloads['current-r05-candidate-summary.json']=enc({'report_digest':'f273556e34d1796de1f8a01e17d58842be82c7a6ab2173bdeabb1a2d91714f8d',
    'input_blocking':14557,'candidate_verified_checksum_locations':14479,'still_unclassified':78,
    'independent_new_review':False,'new_registry_entries':0,'global_acceptance':False,'phases':counts,
    'limit':'Candidate checksum proofs only, no automatic scanner exceptions. Historical LF-to-CRLF is derived, not reconstructed execution RAW. Absolute /usr paths remain blocking after literal-pathspec guard correction.'})
payloads['driver.py']=Path(__file__).read_bytes()
for name,payload in payloads.items():scan(payload,name);(prepared/name).write_bytes(payload)
manifest={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in prepared.iterdir() if p.is_file()}
(prepared/'manifest.json').write_bytes(enc(manifest))
data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda d:{r['id']:{f:r[f] for f in fields} for r in d['requisitos']}
before=criteria(data);assert len(before)==126
notes={
 'R02':'MAIN integra Google33 issuer/sub con alta vacía y enlace/desenlace explícitos; SEC17 revisa3587. No se adopta cuenta por correo. Google-only legacy desconocido/pérdida total de factores no se resuelven por esta asociación.',
 'R03':'Fuente33 integrada. Autor bfbf validó35ORM/36físicas/26FORCE,26funciones y12triggers firmados; los59paths Alembic previos de MAIN permanecen exactos. No se atribuye aMAIN una migración o runtime real aún no ejecutado.',
 'R05':'Clasificador finito v1 integrado:49nuevos+61previos=110PASS autor; peer171PASS y10escaneos reales+2rechazos previos. Registro31.394pins/534archivos de31.564ocurrencias antiguas revisadas. Full17c9 estable:42.830brutos/28.273clasificados/14.557bloqueantes; triage nuevo candidato14.479/78sinclasificar sin ampliarregistro ni declararPASSglobal. CI33 offline inactivo de5993:205históricos y26guardias propias verdes trasfallo de comparador retenido. QA actual33 en curso; de506 ancestroauténtico de3587.',
 'R18':'Locks web/test/desktop reciben únicamente dependencias de verificación Google del autor33:google-auth2.62.0,pyasn1 0.6.4 ypyasn1-modules0.4.2. Entorno propio92/WEB89 intacto. Dockerfile no cambia; imagen/SBOM/SCA final vigente pendientes, no se traslada artefacto31.',
 'R19':'Backend33 yUIGoogle49VM+8SSR+148regresiones autor integrados con origen acotado; revisión independiente SEC sobre3587 en curso y8canariosdeasociaciónverdes. Primerfocal80=78PASS+2REDexpectativaSSR404→200 porUI; safetyheaders no se debilitan,QAadaptaframing. Sin Chrome/HTTPintegrado33/broad33/imagen nuevos aprobados.',
 'R23':'Diseño de tareas durables yeventos aprobado técnicamente conUI77f179/backend844beab, sin backend34 ni consumidor34 integrados. Backend34 implementaenWTpropia desde3587: causa/próximo paso/responsable actual, CAS/idem/historia/métricasdeclaradas, sin cobroinferido ni contacto automático. Nutriasignadossinstatsglobal, sintexto salud libre, elegibilidadactualnuevocode/DDLrequiereQA/SEC.',
 'R31':'UI de asociación usa pruebas/intentos sóloRAM; no afirma resolver exposición legacy globaldeStorage,retención,borradoosoporte. Registrofinito no oculta secretos nuevos. NuevashistoriasR23requiereninventario/erasureR31posterior; no política legal inventada.',
 'R32':'Google33verificadorfirmaRSA/JWKSfijo yauth_time auténtico, asociaciónsubpersistida yprooflocal+factorexistente. LoginMFAlleno/grantsadministrativos se conservan. Configuraciónclaimreal,Google-onlylegacy/lostallfactor,alertas/custodia siguenpendientes; no fallbackiat/porcorreo.',
 'SEC17':'Implementación33+UI integrada localen3587; primeras pruebasindependientes de8criteriosoriginales verdescon transporteJWT/JWKSnormalizado yassertsASTexactos. Peer completoPG/ataques/Chrome/CIpendientes; no se declara cierreglobal.',
 'SEC18':'Cleanup227 permanecebyteexactoen3587 yMAIN. El nuevo33no rebaja ni reatribuye los79SQLite/30PG+8HTTP históricos de retiro; no se afirma universalcheckout0si tambiéninvalidatefallase antes de liberar.'}
refs={
 'R02':['backend-google-subject33-20261019/review.md','google-link-ui/source.json'],
 'R03':['backend-google-subject33-20261019/proofs/freeze.json','prepared-wave129-20261019/source-equivalence.json'],
 'R05':['root-r05-finite-reviewed-author-20261019/source.json','security-r05-registry-independent-20261019/source.json',
     'security-gitleaks-triage-independent-20261019/manifest.json','qa-ci33-offline-preparation-20261019/source.json','prepared-wave129-20261019/current-r05-candidate-summary.json'],
 'R19':['backend-google-subject33-20261019/review.md','google-link-ui/proofs.json'],
 'R23':['prepared-wave129-20261019/backend-wire34-proposal.json','followup-tasks-ui/manifest.json'],
 'SEC17':['backend-google-subject33-20261019/review.md','google-link-ui/source.json']}
for row in data['requisitos']:
    ident=row['id']
    if ident in notes:
        row['observaciones'].append('Checkpoint129: '+notes[ident])
        if BASE not in row['commits']:row['commits'].append(BASE)
    for ref in refs.get(ident,[]):
        assert (EV/ref).is_file(),ref
        if 'evidence/'+ref not in row['evidencia']:row['evidencia'].append('evidence/'+ref)
    if ident in {'R05','R23','SEC17'}:
        row['estado']='en_curso';row['implementacion']='en_curso' if ident=='R23' else 'en_revision';row['validacion']='en_curso'
assert criteria(data)==before
(RUN/'TRAZABILIDAD.json').write_bytes(enc(data))
(RUN/'ESTADO.md').write_bytes(('''# Estado de implementación

Checkpoint129 local: MAIN integra Google33, UI de asociación y clasificador finito
R05 desde3587b3b.126requisitos conservados,92originales+34nuevos,126criterios
exactos. Free10clientes activos/1plancliente/día/10totalgym/día; desktop soportado.
Workspace de referencia intacto. Sin push,PR,deploy,cargos ni mensajesreales.

58fuentes importadas:37backend33,17frontend y4R05.57coinciden conGitproducer;
untest sólo pierdeunEOF(AST/inversaexactos). MAINcoincide58/58conCOMMON3587,
preserva12.343entriesajenas/59pathsAlembicprevios/cleanup227/Dockerfile. Locks
cambian sólo por3dependenciasGoogle. de506/producerbranches son ancestros reales
mediante parentesco explícito conárbolpre/postidéntico trascomponerfuentes.
[Equivalencia](evidence/prepared-wave129-20261019/source-equivalence.json).

Google33: issuer/sub, alta nueva vacía, enlace/desenlaceexplicitos, JWT/JWKSfijo,
auth_time real yprooflocal+factor. Autor35ORM/36físicas/26FORCE/26funciones/
12triggers;31UUIDcerradas. UI49nuevosVM/8SSR/148regresionesautor verdes. Peer
SEC33yQAactualCI trabajan3587:8criteriosasociaciónverdes,2rojosframingSSR200
preservados; no aceptaciónPG/browser/broad/imagen33 completa. Googlelegacycon
subdesconocido/lostallfactorsyconfiguraciónrealclaimaúnpendientes.
[Backend](evidence/backend-google-subject33-20261019/review.md),
[UI](evidence/google-link-ui/source.json).

R05v1:110pruebasautor,171peer,10escaneosreales+2rechazos previos.31.394pins/
534archivos de31.564ocurrenciasantiguas revisadas, sin excepcionesgenéricas.
Full17c9estable12.367archivos:42.830brutos/28.273clasificados/14.557bloqueantes.
Nuevo triage candidato14.479checksum+78sinclasificar exigeotrarevisión; no cambia
dataset ni declaraPASSglobal. TrespreimágenesWIPausentes siguenlimitaciónexplícita.
[Autor](evidence/root-r05-finite-reviewed-author-20261019/source.json),
[peer](evidence/security-r05-registry-independent-20261019/source.json),
[candidatos](evidence/prepared-wave129-20261019/current-r05-candidate-summary.json).

CI33: borradorinactivo5993preserva205canarios31+26guardiaspropias verdes. QA
evolucionaactual33sobrefuentecomún yentorno92sinreescribircriterioshistóricos.
Broad31de506sigue3056PASS+1skipWindowspormodo/cobertura100%crítica; norepresenta33.
VM/Redis6388apagados;PG55483leasedaSEC33conUUIDpropias;sinprocesosajenosalterados.

R23:propuestastareas/eventosdurablesaprobadas,backend34enWTdesde3587,UI34pendiente
wirev1fijo. Responsableactualmisgym/CAS/idem/historia y métricasderevisión declarada;
noauto-task/contacto/cobro/retención. No nuevostablas/código34integrados.
R27,R31,R33yotroscriteriosobligatoriostécnicoscontinúan;no se recortaP2.

Siguiente:cerrarSEC/QA33,CIactual yQAHTTP/browsercomún;completarwire34+tareasUI,
triageindependientenuevoR05yrestopendientes. Artefacto final se generaráde fuente
estable posterior;no reejecutarimagen31niinventarfinal33antesdelresto.
[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).
''').encode())
(RUN/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint129integraGoogle33/UI/R05v1sobre3587con126criteriospreservados.
RevisiónindependienteGoogle/CI33en curso;R05globalcontinúarojo14.557ubicaciones,
con14.479checksumcandidatos/78pendientesnorevisados. R23backend34enimplementación
aislada,consumidorpendientewirefijo. Broads31ycoberturasólohistóricos;imagenfinal,
desktopvigenteyrestocriteriostécnicospendientes.Sinpublicaciónodespliegue.
Free10clientes/1plancliente/día/10totalgym/día;desktopsoportado.
[Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
sections={'CAMBIOS.md':notes['R02']+' '+notes['R18']+' '+notes['R23'],
 'VALIDACION.md':notes['R05']+' '+notes['R19']+' '+notes['R03'],
 'DECISIONES.md':'Componerfuentes33exactasantesdeQAintegrada;mantenerancestryde506paraCIfiel. AceptarclasificadorfinitoR05v1conpeerfocalsinllamarglobalverde. R23dos tablas/nuevopermisoNutriasignado/no nuevo step-up por tareasordinarias;MFAgeneral/grantsequipo/cobrointactos. Hashporcausanoasof/now;eligible:false no lookupprivadodeotrocontexto;historiaRESTRICTnoinventa retenciónlegal/purgaR31. Noejecutarartefactoobsoletoantesdefuenteestable.',
 'RIESGOS.md':notes['SEC17']+' '+notes['R31']+' GlobalR05siguebloqueante. Cifras/tablas34sonpropuesta,noobservación.Países/retención,SLO/volumen,entrevistasyparticipaciónprofesionalexternanoseinventan.'}
for name,text in sections.items():
    with (RUN/name).open('ab') as f:f.write(('\n\n## Checkpoint129\n\n'+text+'\n').encode())
render=subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,capture_output=True,check=True)
(CONTROL/'registry-render.stdout').write_bytes(render.stdout);(CONTROL/'registry-render.stderr').write_bytes(render.stderr)
assert criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))==before
all_new=sorted(imports)+[p.relative_to(ROOT).as_posix() for p in prepared.iterdir() if p.is_file()]
controls=[pre+n for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md','TRAZABILIDAD.json','TRAZABILIDAD.md']]
for offset in range(0,len(all_new),25):git('-c','core.autocrlf=false','add','-f','--',*all_new[offset:offset+25])
git('-c','core.autocrlf=true','add','--renormalize','--',*controls)
for name in all_new:assert blob('',':'+name) if False else git('show',':'+name).stdout==(ROOT/name).read_bytes(),name
assert set(git('diff','--cached','--name-only','-z').stdout.decode().split('\0')[:-1])==set(all_new+controls)
check=git('diff','--cached','--check','--',*controls,check=False)
(CONTROL/'whitespace.stdout').write_bytes(check.stdout);(CONTROL/'whitespace.stderr').write_bytes(check.stderr)
assert check.returncode==0
for row in common['sources']:assert (ROOT/row['path']).read_bytes()==blob(BASE,row['path'])
result={'base':BASE,'registry':126,'criteria_exact':126,'new_ids':[],'main_schema':33,
 'authenticated_new_files':len(all_new),'producer_imports':len(imports),'source_paths_exact_to_common':58,
 'new_file_digests':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':sha((ROOT/n).read_bytes())} for n in all_new},
 'control_files':controls,'status':'staged and validated; awaits final commit'}
(CONTROL/'prepared-result.json').write_bytes(enc(result))
print(json.dumps({k:v for k,v in result.items() if k not in {'new_file_digests','control_files'}}))
