"""Record current integrated DOM repair and independently reviewed candidates."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('F:/MetodoBaseWeb-execution-20261018')
D = R/'docs/implementation/20261018-evolution'
O = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint142-20261020')
BASE = '4775eff5619b695266c63661d8cb0323100e3703'
sha = lambda raw:hashlib.sha256(raw).hexdigest()
encode = lambda obj:(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
git = lambda *args:subprocess.check_output(['git',*args],cwd=R)
assert git('rev-parse','HEAD').decode().strip() == BASE
assert not git('status','--porcelain','-uno').strip() and not O.exists()
O.mkdir()
data = json.loads((D/'TRAZABILIDAD.json').read_bytes())
criteria = lambda value:{row['id']:{key:row[key] for key in ['fuente','seccion','problema','criterio_exacto']} for row in value['requisitos']}
old = criteria(data)
assert len(old) == 144
untracked = {name:sha((R/name).read_bytes()) for name in git('ls-files','--others','--exclude-standard','-z').decode().split('\0') if name and (R/name).is_file()}
assert len(untracked) == 537
(O/'untracked-before.json').write_bytes(encode(untracked))
paths,imports = [],[]
for ref,prefix in [
    ('0dc034d3909fbf443f5f0e34b068c563c23d1253','qa-r31-dom-fix-offline-independent-20261020'),
    ('474af762b40c3c3321664ce667e7bb1805a3013f','qa-r31-dom-after-diagnostic-independent-20261020'),
    ('27bf2d4dd80e6f323383be0cf7fe40ef85c5603b','root-qa26-public-primary-author-20261020'),
    ('386b77666d4a605044d4154060ed67b9090ab5eb','root-qa25-historical-http-20261020'),
    ('77d4725ffa2d56de6e6d4abf109b87d83882aa58','backend-account-security37-sqlite-author-20261020'),
    ('5806e09231fbecd5925a01863eaa55b0398196fa','backend-account-security37-pg-author-20261020'),
    ('dc5ae82a','security-account37-sqlite-independent-20261020'),
    ('dc5ae82a','security-qa26-primary-independent-20261020'),
    ('3e2713444dab9c55daffea6175bc7f0a1d7d134c','root-r05-finite-v3-author-20261020'),
]:
    folder = 'docs/implementation/20261018-evolution/evidence/'+prefix
    names = git('ls-tree','-r','--name-only','-z',ref,'--',folder).decode().split('\0')[:-1]
    assert names,prefix
    entry = {'producer':git('rev-parse',ref).decode().strip(),'prefix':prefix,'files':len(names),'hashes':{},'product_imported':False}
    for name in names:
        raw = git('show',ref+':'+name)
        assert not (R/name).exists(),name
        (R/name).parent.mkdir(parents=True,exist_ok=True)
        (R/name).write_bytes(raw)
        paths.append(name)
        entry['hashes'][name] = sha(raw)
    imports.append(entry)
extra = []
for ref,names in [
    ('5806e09231fbecd5925a01863eaa55b0398196fa',['CUENTA_SEGURIDAD37_WIRE.json','CUENTA_SEGURIDAD37.md','CUENTA_SEGURIDAD37_PG_PLAN.json']),
    ('27bf2d4dd80e6f323383be0cf7fe40ef85c5603b',['NOTIFICACIONES_R27_COHERENCIA_MONETARIA36.md']),
]:
    for name in names:
        relative = 'docs/implementation/20261018-evolution/'+name
        assert not (R/relative).exists()
        (R/relative).write_bytes(git('show',ref+':'+relative))
        extra.append(relative)

paragraph = ('La rama principal local integra la reparación de invalidación del DOM de R31 y conserva el esquema35. Los cuatro archivos de producto coinciden con c822; API y backend no cambiaron. Sobre MAIN2709 pasan37 comprobaciones Node dirigidas. QA conserva las seis canarias RED originales y repite6/6 corregidas, seis controles propios y21 de exportación. El diagnóstico nativo separado pasa2/2 con pageErrors=[]; su observador contiene siete filas informativas y cero pageerror. El intento original de11 grupos rechazado y los cuatro grupos personales no ejecutados siguen preservados; QA prepara los15 grupos completos enPG35 y aún no hay aceptación de ese gate.\n\n'
    'Notificaciones36 y seguridad de cuenta37 siguen aislados. QA-26 pasa20 contratos deautor en36 y9 independientes, incluida la canaria literal de registro con Bearer ajeno; su corrección aún no está en MAIN35. Cuenta37 conserva130 casos pytest SQLite/R31 distintos y8VM del autor; seguridad independiente24/24, migracionesPG12/12 yHTTPPG35/35. Las14 bases37 cerraron normalmente con cero sesiones y ausencia fresca. UI27 continúa en composición y la UI autenticada37 está pendiente. No hubo correo real.\n\n'
    'R05 tiene un candidato finito v3:726 archivos y47513 pares ubicación/regla, con689 registros v2 intactos y37 archivos nuevos. ROOT recalculó las1603 ubicaciones propuestas;26 son checksums de un productor cuya fuente histórica original no está disponible y no se reconstruyó. El algoritmo permanece idéntico salvo tres literales de versión; se fija LF para la configuración cuyo Git blob no cambia. El gate deautor pasa125/125; revisión independiente del código y nuevo escaneo global pendientes. El resultado global conservado sigueRED1603 en4f4.\n\n'
    'Se conservan los144 criterios, incluidos los92 originales, y537 archivos untracked. Free mantiene10 clientes,1 plan por cliente al día y10 planes totales por gimnasio al día. Trabajo y entrega sólo del servicio web; desktop fuera del alcance actual. Sin push, PR, despliegue, cargos o envíos reales.')
for row in data['requisitos']:
    ident = row['id']
    if ident in {'QA-27','R31','R19','R13'}:
        row['observaciones'].append('Checkpoint142: cuatro deltasDOM c822 integrados en MAIN2709; ROOT37NodePASS. QA6RED→6PASS+6propios+21export; diagnósticoChrome2/2/pageErrors[] separado. Original15PG35 en preparación; anterior11rechazado/4personalesnoejecutados se conserva.')
        row['evidencia'].extend(['evidence/root-main-dom31-current-20261020/summary.json','evidence/qa-r31-dom-fix-offline-independent-20261020/phase-summary.json','evidence/qa-r31-dom-after-diagnostic-independent-20261020/phase-summary.json'])
        if ident == 'QA-27':
            row['estado'] = row['implementacion'] = row['validacion'] = 'en_revision'
            row['commits'].extend(['c822c06d1459a4cc34a4582b80b5db2528f9da8a',BASE,'474af762b40c3c3321664ce667e7bb1805a3013f'])
            row['revisor'] = 'QA independiente: reproducción previa yposterior,6controles propios y2escenariosChrome reales; sin modificarpageErrors oaserciones.'
            row['bloqueo'] = 'Quince grupos nativos completos aún pendientes; el diagnóstico2 no sustituye ese gate.'
    if ident == 'QA-26':
        row['estado'] = row['implementacion'] = row['validacion'] = 'en_revision'
        row['commits'].extend(['27bf2d4dd80e6f323383be0cf7fe40ef85c5603b',git('rev-parse','dc5ae82a').decode().strip()])
        row['pruebas'].append('Checkpoint142: autorfinal20/20PASS ypeer9/9PASS en36; canariaoriginal438b exacta2PASS. ControlGoogle JWTfirmado/JWKdoble,aliasesGymProfilepropio,18rechazosbrowser0SQL/0extract,6rutasprimarias/6vecinos yresetfinally. Primer14erroresfixture35en36 preservados; noalgoritmoauthfake.')
        row['evidencia'].extend(['evidence/root-qa26-public-primary-author-20261020/phases.json','evidence/security-qa26-primary-independent-20261020/result-projection.json'])
        row['revisor'] = 'Seguridad independiente dc5,9/9 en SQLite36; no37joint/PG/nativo.'
        row['bloqueo'] = 'Integración de la corrección en MAIN pendiente junto con36/UI27; MAIN35 aún conserva su tenant anterior.'
    if ident in {'R16','B19','UX-15'}:
        row['observaciones'].append('Checkpoint142: candidato37aislado5806:130pytestSQLite/R31 distintos+8VM; seguridad24/24sin hallazgo, PG12DDL+35HTTPambasfactoriesPASS,14UUIDnormalcerradas0sesiones/ausenciafresca. TargetPGdddb2944,22–36intactos; confirmacióncontactonocreaautoridadniMFA;passwordrevocaSV/todosrefreshypruebasenunatransacción. UIautenticada37,peerPG,restoreactual/proveedorrealpendientes.')
        row['evidencia'].extend(['evidence/backend-account-security37-pg-author-20261020/summary.json','evidence/security-account37-sqlite-independent-20261020/independent-final-result.json'])
    if ident in {'R05','QA-01','QA-07','OPS07'}:
        row['observaciones'].append('Checkpoint142: propuestaR05v3aislada3e271:726archivos47513pins,689oldexact+37nuevos;1603bindingsrecalculadosRoot(1545Git/32publicPGP/26produceroriginalbytesunavailable).125/125autor;3literalesloader/algoritmoASTigual/configGitigualLF. Peercódigo/nuevofullscanpendientes, resultadoR05globalhistóricoRED1603norescrito.')
        row['evidencia'].append('evidence/root-r05-finite-v3-author-20261020/summary.json')
    if ident == 'QA-25':
        row['evidencia'].append('evidence/root-qa25-historical-http-20261020/phases.json')
        row['observaciones'].append('Checkpoint142: AA108=104notificacionesPASS+4compilationFAILantesRPC; esperados113eraerrorconteo5DDLnocoleccionados. B27repite4/4MFAHTTPPASStrasnormalizaciónmemoria; RAWyexpectativaoriginalespreservados, noatribuciónalHEADactual.')
assert criteria(data) == old
(D/'TRAZABILIDAD.json').write_bytes(encode(data))
for name,content in {'VALIDACION.md':paragraph,'CAMBIOS.md':paragraph,'DECISIONES.md':'Separar diagnósticoChrome2 deaceptación15; conservar el rechazo previo. QA-26 ycuenta37 tienenpeer independiente SQLite, sinatribuirPGpeer ounaUIinexistente. V3delescáner amplíaúnicamenteubicaciones finitas yconservav2;26fuentesoriginalesnodisponiblesnoreconstruidas. NoDesktop nioperacioneslive.','RIESGOS.md':'Nativo15actual,peerPG37/restore,UI27/UI37,CI/broad/imagen/escaneoactualpendientes. MAINcontinúa35, porloquecorrecciónQA-26ycandidatos36/37aúnnoestánintegrados. Retención,países,SLOypilotoconservandecisionesexternaspendientes.'}.items():
    path = D/name
    assert b'## Checkpoint142' not in path.read_bytes()
    path.write_bytes(path.read_bytes().rstrip()+('\n\n## Checkpoint142\n\n'+content+'\n').encode())
state = (D/'ESTADO.md').read_text(encoding='utf8')
history = state[state.index('## Observaciones históricas'):]
(D/'ESTADO.md').write_bytes(('# Estado de implementación\n\nCheckpoint142 local: esquema35 y144 requisitos.\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n\n'+history+'\n## Checkpoint142\n\n'+paragraph+'\n').encode())
(D/'ENTREGA.md').write_bytes(('# Entrega candidata en curso\n\n'+paragraph+'\n\n[Registro](TRAZABILIDAD.md), [validación](VALIDACION.md).\n').encode())
proof = D/'evidence/checkpoint142-closure-20261020'
proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
(proof/'imports.json').write_bytes(encode(imports))
(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
checked = subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True)
(O/'registry.stdout').write_bytes(checked.stdout);(O/'registry.stderr').write_bytes(checked.stderr)
assert checked.returncode == 0
git('-c','core.autocrlf=false','add','-f','--',*paths,*extra,proof.relative_to(R).as_posix())
controls = ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','DECISIONES.md','RIESGOS.md']
git('-c','core.autocrlf=true','add','--renormalize','--',*[(D/name).relative_to(R).as_posix() for name in controls])
check = subprocess.run(['git','diff','--cached','--check'],cwd=R,capture_output=True)
(O/'whitespace-before.stdout').write_bytes(check.stdout)
cached,cr = {},set()
for line in check.stdout.decode().splitlines():
    match = re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
    if match:
        name,number = match.group(1),int(match.group(2))
        assert name in paths+extra,name
        if name not in cached:cached[name] = git('show',':'+name).split(b'\n')
        raw = cached[name][number-1]
        assert raw.endswith(b'\r') and not raw[:-1].endswith((b' ',b'\t'))
        cr.add(name)
attrs = git('show',':.gitattributes').replace(b'\r\n',b'\n').rstrip()+b'\n'
for name in sorted(cr):
    entry = (name+' whitespace=cr-at-eol\n').encode()
    if entry not in attrs:attrs += entry
(R/'.gitattributes').write_bytes(attrs)
git('-c','core.autocrlf=false','add','--','.gitattributes')
git('diff','--cached','--check')
assert all(sha((R/name).read_bytes()) == digest for name,digest in untracked.items())
assert all(git('show',':'+name) == (R/name).read_bytes() for name in paths+extra)
assert all(name.startswith('docs/') or name == '.gitattributes' for name in git('diff','--cached','--name-only').decode().splitlines())
receipt = {'base':BASE,'requirements':144,'previous_criteria_exact':144,'proof_files_imported':sum(row['files']for row in imports),'docs_imported':len(extra),'untracked_preserved':537,'product_imported':False,'MAIN_schema':35,'native_diagnostic_passed':2,'original_native_15_accepted':False,'global_acceptance':False,'CRLF_paths_preserved':sorted(cr)}
(proof/'receipt.json').write_bytes(encode(receipt))
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
git('diff','--cached','--check')
git('commit','-m','Record reviewed web DOM repair and isolated account PostgreSQL and finite scanner candidates')
assert not git('status','--porcelain','-uno').strip()
result = {'head':git('rev-parse','HEAD').decode().strip(),**receipt}
(O/'result.json').write_bytes(encode(result))
print(json.dumps(result))
