"""Integrate the independently reviewed finite R05 registry without global closure."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
T=Path('C:/Users/Consu/AppData/Local/Temp')
C=T/'metodobase-checkpoint131-20261020'
D=R/'docs/implementation/20261018-evolution'
BASE='e0da4c551f67ad3bff286041e77ab8b7c9be81f2'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*a,check=True):
    return subprocess.run(['git',*a],cwd=R,capture_output=True,check=check)
def immutable(data):
    return {r['id']:{k:r[k] for k in ('fuente','seccion','problema','criterio_exacto')} for r in data['requisitos']}
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
assert not C.exists();C.mkdir()
untracked=git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')[:-1]
preserved={p:sha((R/p).read_bytes()) for p in untracked if (R/p).is_file()}
(C/'untracked-before.json').write_bytes(enc(preserved))
data=json.loads((D/'TRAZABILIDAD.json').read_bytes())
prior=immutable(data);assert len(prior)==127
imports=[]
for i,(ref,prefix,ff) in enumerate([
    ('f4ba470f344517b33f7e0cecea6932fff06eafce','root-r05-reviewed-v2-author-20261019',True),
    ('f008fe99604978cc92f47e97e0113e0332fda256','security-r05-new-locations-independent-20261019',False),
]):
    folder='docs/implementation/20261018-evolution/evidence/'+prefix
    names=git('ls-tree','-r','--name-only','-z',ref,'--',folder).stdout.decode().split('\0')[:-1]
    assert names
    contents={p:git('show',ref+':'+p).stdout for p in names}
    proc=git('-c','core.autocrlf=false','merge','--ff-only' if ff else '--no-edit',ref)
    (C/f'{i}-merge.stdout').write_bytes(proc.stdout)
    (C/f'{i}-merge.stderr').write_bytes(proc.stderr)
    assert all((R/p).read_bytes()==b and git('show','HEAD:'+p).stdout==b for p,b in contents.items())
    imports.append({'ref':ref,'prefix':prefix,'files':len(names),'Git_and_RAW_exact':True})
assert immutable(json.loads((D/'TRAZABILIDAD.json').read_bytes()))==prior
changed=git('diff','--name-only',BASE,'HEAD').stdout.decode().splitlines()
products=[p for p in changed if not p.startswith('docs/')]
assert set(products)=={'scripts/reviewed_scan_locations.py','scripts/data/reviewed_scan_locations_v2.zip'}
assert all((R/p).read_bytes()==git('show','4f4ed767804f05f8763d32bce67a8e604acc3518:'+p).stdout for p in products)
assert sha((R/'scripts/data/reviewed_scan_locations_v1.zip').read_bytes())=='813f66c2f414065200aff734bffe96ebce6673bd0f20b46f68821686b55c604e'
assert sha((R/'scripts/data/reviewed_scan_locations_v2.zip').read_bytes())=='c5ebf029fad80a13b36fb27e5ffd676a1a8234208f25328c4c2c2246ca680d91'
note=('Registro finito R05v2 integrado desde4f4ed7:689archivos/45.910pins, unión disjunta de534/31.394 anteriores y155/14.516 nuevos. '
      'SECf008 verifica14.557ocurrencias nuevas y113controles; QA verifica separadamente el binding exacto de tres literales. '
      'Autor110casos mantenidos PASS, Ruff/pip0 yfuente quieta. ZIPv1 yalgoritmo conservados. '
      'Escaneo real sobre4f4ed7:12.793archivos,44.433hallazgos brutos,42.830clasificados y1.603bloqueantes; salida1, sin aceptación global. '
      'Los archivos de evidencia posteriores no se reatribuyen al árbol escaneado. CI33 c86 ysu PG240 conservanv1 hasta composición explícita.')
for row in data['requisitos']:
    if row['id'] in {'R05','QA-01','QA-07','QA-08','QA-10','OPS07'}:
        row['observaciones'].append('Checkpoint131: '+note)
        row['commits'].extend(x for x in ['4f4ed767804f05f8763d32bce67a8e604acc3518','f4ba470f344517b33f7e0cecea6932fff06eafce','f008fe99604978cc92f47e97e0113e0332fda256'] if x not in row['commits'])
        for ref in ['evidence/root-r05-reviewed-v2-author-20261019/review.md','evidence/security-r05-new-locations-independent-20261019/review.md']:
            if ref not in row['evidencia']:row['evidencia'].append(ref)
assert immutable(data)==prior
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
state=(D/'ESTADO.md').read_text(encoding='utf-8')
state=state.replace('Checkpoint130 local:','Checkpoint131 local:',1)
start=state.index('R05v1 instalado permanece intacto:')
end=state.index('\nR23backend34',start)
state=state[:start]+('R05v2 está integrado:689archivos y45.910pins finitos, conservando ZIPv1 yel\n'
    'algoritmo anterior. Los155archivos nuevos tienen revisión independienteSEC\n'
    'de14.557ocurrencias/14.516pins y113controles; QA revisa el binding separado.\n'
    'Autor110pruebas mantenidas PASS. El escaneo real sobre4f4ed7 sigue RED:\n'
    '44.433hallazgos brutos,42.830clasificados y1.603bloqueantes nuevos. Estos\n'
    'requieren su propio triage; no hay PASS global. Los archivos de evidencia\n'
    'añadidos después no se atribuyen al árbol escaneado. CI33/PG240 retienenv1\n'
    'hasta componer yverificar sus pins explícitamente.\n'
    '[Autorv2](evidence/root-r05-reviewed-v2-author-20261019/review.md),\n'
    '[peer nuevo](evidence/security-r05-new-locations-independent-20261019/review.md).\n')+state[end:]
(D/'ESTADO.md').write_bytes(state.encode())
(D/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint131 integra R05v2 con revisión independiente finita yconserva127
requisitos ytodos sus criterios. El escaneo4f4ed7 sigue bloqueado por1.603
hallazgos nuevos; no hay aceptación global. CI33/PG240 terminó con exit0 en
su fuente c86/v1 yQA audita IDs,testigos ycierre antes de integrarlo. Esquema
MAIN33;backend/UI34 ycontrato nutricional35 siguen aislados. Imagen,desktop
final ycriterios R27/R31/R33 pendientes. Free10clientes/1plancliente/día/
10totalgym/día;desktop soportado. Sin publicación odespliegue.
[Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
append={
    'VALIDACION.md':note,
    'CAMBIOS.md':'Sólo dos paths de producto R05: nuevo ZIPv2 ybinding de tres literales. Inversa RAW/AST exacta;sin nuevas excepciones de algoritmo. '+note,
    'DECISIONES.md':'Aceptar solamente ubicaciones con revisión independiente finita. El resto permanece bloqueante; no ampliar por patrón ni confiar en Match/Secret/Line. '+note,
    'RIESGOS.md':'Persisten1.603hallazgos del último escaneo real yse requiere scan final de artefacto estable. Ninguna ubicación nueva se presume falsa positiva. '
                   'El cierre de PG240 yla recuperación de agentes tras cuota se auditan antes de reutilizarPG55483; no se reejecuta a ciegas.',
}
for name,paragraph in append.items():
    p=D/name;raw=p.read_bytes();assert b'## Checkpoint131' not in raw
    p.write_bytes(raw.rstrip()+b'\n\n## Checkpoint131\n\n'+paragraph.encode()+b'\n')
proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(C/'registry.stdout').write_bytes(proc.stdout);(C/'registry.stderr').write_bytes(proc.stderr)
assert all(sha((R/p).read_bytes())==h for p,h in preserved.items())
proof=D/'evidence/checkpoint131-closure-20261020';proof.mkdir()
(proof/'.gitattributes').write_bytes(b'* -text\n')
receipt={'base':BASE,'product_source':'4f4ed767804f05f8763d32bce67a8e604acc3518','source_changes_only':products,'imports':imports,'previous_criteria_exact':127,'registry':127,'preexisting_untracked_files_preserved':len(preserved),'global_R05_acceptance':False,'current_full_scan_remaining':1603,'CI33_runtime_reattributed':False}
(proof/'receipt.json').write_bytes(enc(receipt));(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
controls=['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md',*append]
paths=[(D/p).relative_to(R).as_posix() for p in controls]
git('-c','core.autocrlf=true','add','--renormalize','--',*paths)
git('diff','--cached','--check')
assert set(git('diff','--cached','--name-only').stdout.decode().splitlines())==set(paths)|{p.relative_to(R).as_posix() for p in proof.iterdir()}
git('commit','-m','Integrate finite reviewed scan registry v2 and preserve blocking findings')
assert immutable(json.loads((D/'TRAZABILIDAD.json').read_bytes()))==prior
assert not git('status','--porcelain','-uno').stdout.strip()
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt,'tracked_quiet':True}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
