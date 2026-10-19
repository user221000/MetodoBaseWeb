from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path('F:/MetodoBaseWeb-execution-20261018')
TMP=Path('C:/Users/Consu/AppData/Local/Temp')
RUN=ROOT/'docs/implementation/20261018-evolution'
CONTROL=TMP/'metodobase-checkpoint129-20261019'
BASE='3587b3b3eee3a58367624472d7c0683baa8f10e0'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*args):return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True)
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
prepared=json.loads((CONTROL/'prepared-result.json').read_bytes())
for name,meta in prepared['new_file_digests'].items():
    value=(ROOT/name).read_bytes();assert sha(value)==meta['sha256'] and len(value)==meta['bytes']
data=json.loads((RUN/'TRAZABILIDAD.json').read_bytes())
fields=['fuente','seccion','problema','criterio_exacto']
criteria=lambda d:{r['id']:{f:r[f] for f in fields} for r in d['requisitos']}
original=json.loads(git('show',BASE+':docs/implementation/20261018-evolution/TRAZABILIDAD.json').stdout)
assert criteria(data)==criteria(original) and len(data['requisitos'])==126
notes={
 'R02':'MAIN integra Google33 por issuer/sub, alta nueva vacía y enlace/desenlace explícitos. SEC17 revisa la composición3587. La coincidencia de correo no adopta una cuenta existente. La continuidad Google-only con sub histórico desconocido y la pérdida total de factores siguen pendientes.',
 'R03':'Se integró la fuente33. El autor bfbf validó35 tablas ORM,36 físicas,26 familias FORCE,26 funciones y12 triggers firmados. La composición conserva59 rutas Alembic previas. Esto no atribuye aMAIN una migración o runtime que aún no ejecutó.',
 'R05':'Clasificador finito v1:110 pruebas del autor (49 nuevas+61 anteriores) y171 del peer;10 escaneos reales y2 rechazos previos. Registro de31.394 pins únicos/534 archivos para31.564 ocurrencias antiguas revisadas. Último escaneo completo, fuente17c9:42.830 hallazgos brutos,28.273 clasificados y14.557 bloqueantes. Triage nuevo candidato:14.479 checksums/78 pendientes, sin ampliar el registro ni aceptar el gate global. El árbol33 actual requiere un nuevo escaneo completo. Borrador CI33 inactivo5993:205 canarios históricos y26 guardias propias verdes; QA actual33 continúa. de506 es ancestro auténtico de3587.',
 'R18':'Los locks web/test/desktop incorporan las tres dependencias de verificación Google del autor33:google-auth2.62.0,pyasn1 0.6.4 ypyasn1-modules0.4.2. Entorno propio92; WEB89 permanece intacto. Dockerfile no cambia. Imagen,SBOM ySCA final vigentes siguen pendientes; el artefacto31 no se reatribuye.',
 'R19':'Se integran backend33 yUI Google con evidencia acotada del autor:49 casos VM nuevos,8SSR y148 regresiones. SEC revisa3587; sus8 criterios de asociación pasan. El primer focal80 conserva78PASS+2RED por expectativa SSR anterior404 frente a página200. QA adapta sólo ese framing y conserva las comprobaciones de privacidad. HTTP/browser integrado,broad33 eimagen todavía no están aceptados.',
 'R23':'Diseño aprobado con propuestas UI77f179 ybackend844beab. No hay backend34 ni consumidor34 integrados. Backend implementa enWT propia desde3587: tareas/eventos durables,causa,próximo paso,responsable actual,CAS,idempotencia,historia y métricas de declaraciones guardadas. Nutri sólo accede a sus asignadas sin stats globales. Sin cobro inferido,contacto automático ni texto sanitario libre. El código yDDL34 requieren QA/SEC.',
 'R31':'Las pruebas e intentos de la nueva UI Google se mantienen enRAM. Esto no resuelve la exposición legacy global deStorage,retención,borrado o acceso de soporte. El clasificador finito no acepta secretos nuevos. La historia de tareas prevista exige inventario ypurga bajoR31; no se inventa una política legal de conservación.',
 'R32':'Google33 verifica firmaRSA conJWKS fijo yauth_time auténtico,asociaciónsub persistida yprueba local con factor existente. Conserva loginMFA completo ygrants administrativos. Configuración real delclaim,continuidad Google-only histórica,recuperación total,alertas ycustodia siguen pendientes. No hay fallback aiat o correo.',
 'SEC17':'Implementación33 yUI integradas localmente en3587. Los8 criterios originales del primer peer pasan con transporteJWT/JWKS normalizado yasserts AST exactos. PeerPG,ataques,QAHTTP/browser yCI siguen en curso; no se declara cierre global.',
 'SEC18':'Cleanup227 sigue byte a byte exacto en3587 yMAIN.33 no rebaja ni reatribuye los79SQLite/30PG y8HTTP históricos del retiro. No se promete checkout0 si también invalidate falla antes de liberar.'}
for row in data['requisitos']:
    if row['id'] in notes:
        assert row['observaciones'][-1].startswith('Checkpoint129: ')
        row['observaciones'][-1]='Checkpoint129: '+notes[row['id']]
(RUN/'TRAZABILIDAD.json').write_bytes(enc(data))
(RUN/'ESTADO.md').write_bytes(('''# Estado de implementación

Checkpoint129 local: MAIN integra Google33, su UI y el clasificador finito R05
desde3587b3b. Se conservan126 requisitos (92 originales+34 nuevos) y sus126
criterios exactos. Free:10 clientes activos,1 plan por cliente al día y10 planes
totales por gimnasio al día. Desktop sigue soportado. El workspace de referencia
permanece intacto. Sin push,PR,despliegue,cargos ni comunicaciones reales.

La composición importó58 fuentes:37 del backend,17 del frontend y4 deR05.
57 coinciden conGit de sus autores; un test sólo pierde una línea vacía final
(AST e inversa exactos). MAIN coincide58/58 conCOMMON3587. La composición conservó
12.343 entradas ajenas,59 rutas Alembic previas,cleanup227 yDockerfile. Este
checkpoint añade evidencia yactualiza los archivos de control. Los locks cambian
por tres dependencias Google. de506 ylas ramas productoras son ancestros reales:
la unión de parentesco posterior conservó el árbol compuesto byte a byte.
[Equivalencia](evidence/prepared-wave129-20261019/source-equivalence.json).

Google33 asocia issuer/sub,crea cuentas nuevas vacías yofrece enlace/desenlace
explícitos. VerificaJWT conJWKS fijo yauth_time real; exige prueba local yfactor
existente al vincular. El autor validó35 tablasORM/36 físicas/26FORCE,26 funciones
y12 triggers; cerró31 UUID propias. La UI pasó49 casosVM nuevos,8SSR y148
regresiones del autor. SEC yQA revisan3587:8 criterios de asociación verdes;
2 rojos de framingSSR200 conservados. PG,HTTP/browser integrado,broad eimagen33
no tienen aceptación completa. Google-only histórico desconocido,pérdida total
de factores yconfiguración real delclaim siguen pendientes.
[Backend](evidence/backend-google-subject33-20261019/review.md),
[UI](evidence/google-link-ui/source.json).

R05v1 pasó110 pruebas del autor y171 del peer,10 escaneos reales y2 rechazos
previos. El registro fija31.394 ubicaciones/reglas únicas en534 archivos de un
informe anterior con31.564 ocurrencias revisadas. No añade excepciones genéricas.
El último escaneo completo (17c9,12.367 archivos) quedó estable yrojo:42.830
hallazgos brutos,28.273 clasificados y14.557 bloqueantes. El nuevo triage propone
14.479 checksums ydeja78 ubicaciones sin clasificar; exige revisión independiente
antes de ampliar el registro. El árbol33 actual necesita otro escaneo completo.
Las tres preimágenesWIP ausentes conservan su limitación de procedencia.
[Autor](evidence/root-r05-finite-reviewed-author-20261019/source.json),
[peer](evidence/security-r05-registry-independent-20261019/source.json),
[candidatos](evidence/prepared-wave129-20261019/current-r05-candidate-summary.json).

CI33 tiene un borrador inactivo5993 con205 canarios históricos y26 guardias propias
verdes. QA evoluciona la suite actual sobreCOMMON yentorno92,con criterios y
fixtures históricos conservados. Los broads31 de506 (3056PASS+1skipWindows por
modo,cobertura crítica100%) son históricos. VM yRedis6388 siguen apagados.
PG55483 está reservado aSEC33 con UUID propias; no se alteran procesos ajenos.

R23 tiene diseños de tareas/eventos durables aprobados. Backend34 se implementa
enWT desde3587; la UI espera elwirev1 fijo. Se registrarán responsable actual del
mismo gym,CAS,idempotencia,historia ydeclaraciones de revisión. No se crean tareas
ni contactos automáticamente,ni se infieren cobros o retención. No hay código o
tablas34 integrados. R27,R31,R33 ylos demás criterios técnicos continúan.

Siguiente: cerrar revisiónSEC/QA33,CI actual yQAHTTP/browser; conectarwire34 yUI;
revisar el nuevo triageR05 ycontinuar el resto del alcance. El artefacto se
generará desde la fuente estable posterior. No reejecutar la imagen31 ni tratar
33 como versión final antes de completar el trabajo restante.
[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).
''').encode())
(RUN/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint129 integra Google33,suUI yR05v1 sobre3587,con126 criterios exactos
conservados. SEC/QA yCI33 siguen en curso. El último escaneo completo17c9 dejó
14.557 bloqueantes; los14.479 candidatos nuevos y78 pendientes no amplían el
registro. Falta escanear el árbol33 actual.

R23backend34 se desarrolla aislado; suUI espera elwire fijo. Broad31 ycobertura
siguen siendo históricos. Imagen,desktop vigente yotros criterios técnicos
quedan pendientes. Free10clientes/1plancliente/día/10totalgym/día;desktop soportado.
Sin publicación ni despliegue. [Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
sections={
 'CAMBIOS.md':notes['R02']+' '+notes['R18']+' '+notes['R23'],
 'VALIDACION.md':notes['R05']+' '+notes['R19']+' '+notes['R03'],
 'DECISIONES.md':'Componer fuentes33 antes deQA integrada yconservar el ancestry real de506 paraCI histórica. Aceptar R05v1 sólo en su alcance focal; el gate global sigue abierto. ParaR23 se aprueban dos tablas,permiso dedicado deNutri asignado yningún step-up nuevo para tareas ordinarias; loginMFA ygrants deequipo/cobro permanecen. El hash por causa excluye now/as_of. Un responsable no elegible no provoca lookup decontacto privado deotro contexto. La historiaRESTRICT no define retención legal ni cierra purgaR31. La imagen final espera fuente estable.',
 'RIESGOS.md':notes['SEC17']+' '+notes['R31']+' El gate globalR05 sigue abierto yel árbol33 no tiene un escaneo completo nuevo. Las cifras de tablas34 son previsión,no observación. Países/retención,volumen/SLO,entrevistas yvalidación profesional requieren datos oparticipación real.'}
for name,text in sections.items():
    path=RUN/name;raw=path.read_bytes();marker=b'\n\n## Checkpoint129\n\n';assert raw.count(marker)==1
    path.write_bytes(raw.split(marker)[0]+marker+text.encode()+b'\n')
render=subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,capture_output=True,check=True)
(CONTROL/'final-registry.stdout').write_bytes(render.stdout);(CONTROL/'final-registry.stderr').write_bytes(render.stderr)
assert criteria(json.loads((RUN/'TRAZABILIDAD.json').read_bytes()))==criteria(original)
closure=RUN/'evidence/checkpoint129-closure-20261019';assert not closure.exists();closure.mkdir();(closure/'.gitattributes').write_bytes(b'* -text\n')
(closure/'finish-driver.py').write_bytes(Path(__file__).read_bytes())
(closure/'receipt.json').write_bytes(enc({'base':BASE,'registry':126,'criteria_exact':126,'new_ids':[],
    'main_schema':33,'authenticated_new_files_before_closure':270,'source_paths_exact_to_common':58,
    'global_R05_acceptance':False,'main33_broad_acceptance':False,
    'scope':'Evidence import and current control update; source58 unchanged from COMMON3587. Final prose edit does not alter immutable criteria or closed producer bytes.'}))
new_closure=[p.relative_to(ROOT).as_posix() for p in closure.iterdir() if p.is_file()]
git('-c','core.autocrlf=false','add','-f','--',*new_closure)
git('-c','core.autocrlf=true','add','--renormalize','--',*prepared['control_files'])
git('diff','--cached','--check','--',*prepared['control_files'],*new_closure)
for name,meta in prepared['new_file_digests'].items():
    assert sha((ROOT/name).read_bytes())==meta['sha256'] and git('show',':'+name).stdout==(ROOT/name).read_bytes()
expected=set(prepared['new_file_digests'])|set(prepared['control_files'])|set(new_closure)
assert set(git('diff','--cached','--name-only','-z').stdout.decode().split('\0')[:-1])==expected
common=json.loads((RUN/'evidence/prepared-wave129-20261019/source-equivalence.json').read_bytes())
for row in common['sources']:assert (ROOT/row['path']).read_bytes()==git('show',BASE+':'+row['path']).stdout
commit=git('commit','-m','Record Google33 composition, finite scan review and current roadmap work')
(CONTROL/'commit.stdout').write_bytes(commit.stdout);(CONTROL/'commit.stderr').write_bytes(commit.stderr)
assert not git('status','--porcelain=v1','-uno').stdout.strip()
final=subprocess.run([sys.executable,'-X','utf8','-B','scripts/implementation_registry.py','--check'],cwd=ROOT,capture_output=True,check=True)
(CONTROL/'postcommit-registry.stdout').write_bytes(final.stdout)
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),'registry':126,'criteria_exact':126,
    'main_schema':33,'authenticated_new_files':273,'source_paths_exact_to_common':58,'working_tree_clean':True,
    'global_R05_acceptance':False,'main33_broad_acceptance':False}
(CONTROL/'result.json').write_bytes(enc(result));print(json.dumps(result))
