"""Integrate reviewed Google correction and preserve every previous criterion."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
T=Path('C:/Users/Consu/AppData/Local/Temp')
C=T/'metodobase-checkpoint130-20261019'
D=R/'docs/implementation/20261018-evolution'
BASE='707b32605c254466982f25a368b046a0445a3f71'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*a,check=True):return subprocess.run(['git',*a],cwd=R,capture_output=True,check=check)
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
assert not C.exists();C.mkdir()
untracked=git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')[:-1]
untracked_before={p:sha((R/p).read_bytes()) for p in untracked if (R/p).is_file()}
(C/'untracked-before.json').write_bytes(enc(untracked_before))
original=json.loads((D/'TRAZABILIDAD.json').read_bytes())
immutable=lambda x:{r['id']:{k:r[k] for k in ['fuente','seccion','problema','criterio_exacto']} for r in x['requisitos']}
criteria_before=immutable(original);assert len(criteria_before)==126 and 'QA-17' not in criteria_before
imports=[
 ('41d8c39cedc4fafcde22a5c75a2a333a21040960','root-google33-conflict-author-20261019',True),
 ('b792cbcec58dd1441167c328e78682dc435dfa17','security-google33-conflict-independent-20261019',False),
 ('0bf1d0a8c5a3470173faa36b094076843b76dd6f','security-google33-independent-20261019',False),
 ('8012dc7d5098ac9064cd87078bcec3ba88d86415','root-r05-new-locations-candidate-20261019',False),
]
import_receipts=[]
for i,(ref,prefix,ff) in enumerate(imports):
    proof_path='docs/implementation/20261018-evolution/evidence/'+prefix
    names=git('ls-tree','-r','--name-only','-z',ref,'--',proof_path).stdout.decode().split('\0')[:-1]
    assert names
    source={p:git('show',ref+':'+p).stdout for p in names}
    merge=git('-c','core.autocrlf=false','merge','--ff-only' if ff else '--no-edit',ref)
    (C/(str(i)+'-merge.stdout')).write_bytes(merge.stdout);(C/(str(i)+'-merge.stderr')).write_bytes(merge.stderr)
    for p,b in source.items():assert (R/p).read_bytes()==b and git('show','HEAD:'+p).stdout==b
    import_receipts.append({'ref':ref,'prefix':prefix,'files':len(source),'Git_and_RAW_exact':True})
assert immutable(json.loads((D/'TRAZABILIDAD.json').read_bytes()))==criteria_before
changed=git('diff','--name-only',BASE,'HEAD','--','.',' :(exclude)docs').stdout.decode().splitlines() if False else git('diff','--name-only',BASE,'HEAD').stdout.decode().splitlines()
source_changes=[p for p in changed if not p.startswith('docs/')]
assert set(source_changes)=={'web/services/google_link.py','tests/test_google33_conflict_window.py'}
for p in source_changes:assert (R/p).read_bytes()==git('show','8a5e5dc235e96a47488befb743fc02a24b491939:'+p).stdout
data=json.loads((D/'TRAZABILIDAD.json').read_bytes())
row={
 'id':'QA-17','identificador_original':'QA-17',
 'fuente':'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019/source.json',
 'seccion':'Hallazgo nuevo checkpoint130',
 'problema':'El alta Google de gimnasio puede producir 200+503 en una colisión concurrente de issuer/sub porque el flush del perfil queda fuera del manejo estrecho de IntegrityError. Confirm puede anticipar una colisión con autoflush=True. Se conserva una cuenta y no hay credenciales del perdedor; falla la clasificación pública del conflicto.',
 'criterio_exacto':'En ambas factories, dos procesos HTTP reales con sesiones propias, pool1 y autoflush=False que intenten alta gym para el mismo issuer/sub y contactos diferentes producen un único200 y un409 google_link_conflict, sin credenciales para el perdedor y con una sola cuenta, binding, perfil y cinco plantillas canónicas. Las colisiones de constraint previas al commit en alta y confirm, incluido autoflush=True al confirmar, requieren rollback confirmado antes del409; rollback incierto conserva503. Mantener atomicidad, ausencia de adopción o reintentos, restauración del contexto y cierre de sesiones propias. Repetir los mismos canarios y conservar verificación de identidad del proveedor.',
 'prioridad':'P2','responsable':'Coordinación, backend, seguridad y QA',
 'tareas':['R02','R19','R32'],'dependencias':['R02','R03','R32'],
 'estado':'en_revision','implementacion':'en_revision','validacion':'verificado','despliegue':'no_desplegado','entorno':'local',
 'cambios':['Frontera de IntegrityError sobre toda la escritura de alta/confirm; rollback confirmado409, incierto503, sin retry o adopción. Integración local de fuente8a5e y evidencias originales/fijas.'],
 'commits':['0bf1d0a8c5a3470173faa36b094076843b76dd6f','8a5e5dc235e96a47488befb743fc02a24b491939','41d8c39cedc4fafcde22a5c75a2a333a21040960','b792cbcec58dd1441167c328e78682dc435dfa17'],
 'pruebas':['Autor: baseline2FAIL+2PASS; mismos4casos4PASS,58regresionesPASS y replayframing4PASS (solapados). Peer:12SQLite+11PG PASS,0errors/skips;2HTTP canónicos200+409,4carrerasFalse+4True ycontrato33. Tres UUID del peer cerrados/ausentes con0sesiones yDROPnormal.'],
 'evidencia':['evidence/security-google33-independent-20261019/review.md','evidence/root-google33-conflict-author-20261019/source.json','evidence/security-google33-conflict-independent-20261019/review.md'],
 'documentacion':['ESTADO.md','VALIDACION.md','GOOGLE_IDENTIDAD_ASOCIACION.md','NUEVOS_HALLAZGOS.md'],
 'revisor':'Seguridad independiente del autor: replay exacto sobre8a5e',
 'bloqueo':None,'observaciones':['Aceptación focal local. Wiring de los canarios mantenidos y broad/CI actual siguen en curso; no se declara aceptación global Google33 ni despliegue.']}
data['requisitos'].append(row)
notes={
 'R02':'Google33: corrección8a5e integra QA-17 con peer12SQLite+11PG PASS. La carrera HTTP original mantiene200+409 y cuenta única. No cierra continuidad Google-only histórica ni recuperación total.',
 'R05':'Candidato8012 cubre14.557 ocurrencias/14.516pins únicos/155archivos del informe17c9, ahora sin ubicaciones pendientes de triage. Registrov1 instalado intacto; revisión independiente nueva en curso. No es escaneo nuevo ni PASS global. Los nueve digests de configuración prueban productor puro y recibos, sin reconstruir valores privados.',
 'R19':'QA-17 tiene replay independiente12SQLite/11PG verde. QA CI33 cerró708 comprobacionesoffline y prepara PG real y framing actual de frontend. Sus fallos Node originales se conservan; broad33, browser eimagen final no están aceptados.',
 'R23':'Backend34 integra el fix8a5e y avanza con mecanismos, HTTP y límites SQLite; router montado en ambas factories sólo enWT34. Wirev1 33bfe88f fijado con ACK técnico de coordinación; aún sin backend/UI34 integrados o PG34 ejecutado.',
 'SEC17':'Revisión completa de fuente3587 conservada, incluidos dos framingSSR rojos y carreraQA-17. El fix8a5e tiene replay propio independiente verde. Los canarios de adopción previos se preservan. Aceptación global33 y continuidad legacy aún abiertas.'}
for r in data['requisitos']:
    if r['id'] in notes:r['observaciones'].append('Checkpoint130: '+notes[r['id']])
assert {k:v for k,v in immutable(data).items() if k!='QA-17'}==criteria_before
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
state='''# Estado de implementación

Checkpoint130 local: esquema33 y127 requisitos (92 originales+35 añadidos).
Se conservan íntegros los126 criterios previos. Free:10 clientes activos,
1 plan por cliente al día y10 planes totales por gimnasio al día. Desktop sigue
soportado. El workspace de referencia permanece intacto. Sin push,PR,despliegue,
cargos ni comunicaciones reales.

Google33 ysu UI están integrados desde3587. La corrección8a5e deQA-17 amplía el
manejo de colisiones a los flush previos al commit. Rollback confirmado409;
incierto503. No añade retry ni adopta cuentas. Autor:4casos verdes tras2FAIL y
2PASS iniciales,58regresiones verdes. Peer sobre la fuente exacta:12SQLite y
11PostgreSQL PASS,0errores/skips. Los mismos dos canarios HTTP entre procesos
devuelven200+409; cuenta,binding,perfil ycinco plantillas únicos. Tres UUID
temporales cerrados y ausentes. Evidencia original RED yreplay preservados.
[Corrección](evidence/root-google33-conflict-author-20261019/review.md),
[peer](evidence/security-google33-conflict-independent-20261019/review.md).

La revisión33 anterior retiene sus fases ylimitaciones, sin sumar replays
solapados. El esquema tiene35tablasORM/36físicas/26familiasFORCE,26funciones y
12triggers. Su UI tiene evidencia de autor49VM,8SSR y148regresiones. QA actual
prepara PG/CI yframing frontend:708comprobacionesoffline verdes; los primeros
fallos Node siguen conservados. Broad actual,browser integrado eimagen final
siguen pendientes. No se reatribuye el broad31 o el artefacto31 aesta versión.
Google-only histórico sin sub conocido,pérdida total de factores,claim real,
alertas ycustodia siguen abiertos.
[Revisión33](evidence/security-google33-independent-20261019/review.md).

R05v1 instalado permanece intacto:31.394pins/534archivos;110pruebas del autor,
171delpeer. El último escaneo completo17c9 sigue RED:42.830hallazgos brutos,
28.273clasificados y14.557bloqueantes. Su triage nuevo tiene14.557ocurrencias
candidatas/14.516pins/155archivos,0ubicaciones pendientes de análisis. Esto
requiere revisión independiente antes de ampliar el registro. No es un escaneo
nuevo ni PASS global. Las derivaciones CRLF no son ejecuciónRAW reconstruida;
los digests de configuración prueban productor yrecibos sin revelar valores.
[Candidatos](evidence/root-r05-new-locations-candidate-20261019/review.md).

R23backend34 se desarrolla aislado conTask/Event durables,CAS,idempotencia,
responsables autorizados,historia ydeclaraciones de revisión. El wirev1 fijo
tiene ACK técnico de coordinación. Mecanismos,HTTP ylímite SQLite avanzan;
PG34,consumidor UI34 e integración siguen pendientes. No se infieren cobros,
contactos automáticos,renovaciones ni retención clínica. R27,R31,R33 ylos demás
criterios técnicos continúan. Retención/países,volumen/SLO,entrevistas yrevisión
profesional requieren datos oparticipación real.

VM yRedis6388 propios siguen apagados. PostgreSQL55483 quedó transferido de
seguridad aQA para validación actual con bases propias ycierres comprobados.
La imagen ydesktop final se prepararán desde la fuente estable posterior.
[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).
'''
(D/'ESTADO.md').write_bytes(state.encode())
(D/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint130 integra la correcciónGoogle8a5e ysu peer12SQLite/11PG verde.
127requisitos;126criterios previos exactos. CI/broad/browser actual siguen en
curso. R05 tiene14.557candidatos revisándose, sin ampliarv1 ni PASS global.
R23backend34 avanza aislado; faltan UI34,PG34 eintegración. Imagen ydesktop final,
R27,R31,R33 yotros criterios siguen pendientes. Free10clientes/1plancliente/día/
10totalgym/día;desktop soportado. Sin publicación ni despliegue.
[Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
append={
 'VALIDACION.md':notes['R19']+' '+notes['R05']+' La evidencia originalSEC33 ylos replaysFalse/True se conservan sin sumar conjuntos solapados.',
 'CAMBIOS.md':notes['R02']+' '+notes['R23'],
 'DECISIONES.md':'QA-17 es clasificación de conflicto concurrente, sin adopción de cuenta ni credenciales al perdedor. Ampliar el catch a toda la escritura; no convertir rollback incierto en409 ni añadir reintentos. El triageR05 nuevo requiere peer antes de instalarv2.',
 'RIESGOS.md':notes['R05']+' '+notes['SEC17'],
 'GOOGLE_IDENTIDAD_ASOCIACION.md':notes['R02']+' Cubre además confirm conautoflush=True. Servicio entero recuperable por inversa exacta; no cambiaDDL oDTO. Fuente8a5e,peerb792cb.',
 'NUEVOS_HALLAZGOS.md':'QA-17 (P2): '+row['problema']+' Criterio: '+row['criterio_exacto']+' Autor8a5e ypeerb792cb aceptados focalmente; wiring de CI actual en curso.'}
for name,paragraph in append.items():
    p=D/name;raw=p.read_bytes();assert b'## Checkpoint130' not in raw
    p.write_bytes(raw.rstrip()+b'\n\n## Checkpoint130\n\n'+paragraph.encode()+b'\n')
run=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(C/'registry.stdout').write_bytes(run.stdout);(C/'registry.stderr').write_bytes(run.stderr)
assert len(data['requisitos'])==127
assert all(sha((R/p).read_bytes())==d for p,d in untracked_before.items())
controls=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md',*append]
proof=D/'evidence/checkpoint130-closure-20261019';proof.mkdir();(proof/'.gitattributes').write_bytes(b'* -text\n')
receipt={'base':BASE,'product_source':'8a5e5dc235e96a47488befb743fc02a24b491939','source_changes_only':source_changes,'imports':import_receipts,'previous_criteria_exact':126,'registry':127,'new_id':'QA-17','preexisting_untracked_files_preserved':len(untracked_before),'global_R05_acceptance':False,'global33_acceptance':False}
(proof/'receipt.json').write_bytes(enc(receipt));(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
control_paths=[(D/p).relative_to(R).as_posix() for p in controls]
git('-c','core.autocrlf=true','add','--renormalize','--',*control_paths)
git('diff','--cached','--check')
expected=set(control_paths)|{p.relative_to(R).as_posix() for p in proof.iterdir()}
assert set(git('diff','--cached','--name-only').stdout.decode().splitlines())==expected
git('commit','-m','Record independent Google conflict closure and 127 requirement checkpoints')
assert not git('status','--porcelain','-uno').stdout.strip()
after=json.loads((D/'TRAZABILIDAD.json').read_bytes())
assert {k:v for k,v in immutable(after).items() if k!='QA-17'}==criteria_before
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt,'tracked_quiet':True}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
