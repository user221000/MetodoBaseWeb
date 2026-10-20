"""Integrate exact CI33 ancestry and its reviewed R05v2 composition."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
C=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint133-20261020')
BASE='0cff974332a2527149acf3cff7b7462fd0f91e85'
REF='0edbaf47797b274c7fa5bb55a041c42abe8a9f47'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*a):return subprocess.run(['git',*a],cwd=R,capture_output=True,check=True)
def immutable(data):return {r['id']:{k:r[k] for k in ('fuente','seccion','problema','criterio_exacto')} for r in data['requisitos']}
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('status','--porcelain','-uno').stdout.strip()
assert not C.exists();C.mkdir()
data=json.loads((D/'TRAZABILIDAD.json').read_bytes());prior=immutable(data);assert len(prior)==128
untracked=git('ls-files','--others','--exclude-standard','-z').stdout.decode().split('\0')[:-1]
preserved={p:sha((R/p).read_bytes()) for p in untracked if (R/p).is_file()}
(C/'untracked-before.json').write_bytes(enc(preserved))
names=git('diff','--name-only',BASE,REF).stdout.decode().splitlines()
products=[p for p in names if not p.startswith('docs/')]
assert products and all(p.startswith('tests/') or p=='.github/workflows/ci.yml' for p in products)
expected={p:git('show',REF+':'+p).stdout for p in names if git('cat-file','-t',REF+':'+p).stdout.strip()==b'blob'}
merge=git('-c','core.autocrlf=false','merge','--ff-only',REF)
(C/'merge.stdout').write_bytes(merge.stdout);(C/'merge.stderr').write_bytes(merge.stderr)
assert all((R/p).read_bytes()==b and git('show','HEAD:'+p).stdout==b for p,b in expected.items())
assert immutable(json.loads((D/'TRAZABILIDAD.json').read_bytes()))==prior
with (C/'verify-only.stdout').open('xb') as out,(C/'verify-only.stderr').open('xb') as err:
    proc=subprocess.run([sys.executable,'-B','-X','utf8','tests/verify_google33_ci.py','--verify-only'],cwd=R,stdout=out,stderr=err)
assert proc.returncode==0
note=('CI33 integrado conservando la cadena completa de c86 ysu delta original de82 fuentes desdeCOMMON3587. '
    'La composición con MAIN132/R05v2 modifica sólo el verifier respecto a c86:pinLF del módulo,pinRAW del ZIPc5eb ybase d8 explícitos; '
    'el guard de producto separa docs yel gateR05 sigue escaneándolos completos. '
    'QA110R05/49críticos PASS,9binding ycontroles de documento/3rechazos de producto,lock,target; '
    'verificador final193canarios workflow y157bloquesBash PASS,también replay ROOT enMAIN. '
    'Conserva20reportes/240IDs actuales33,5reportes/38IDs históricos32 ylos oráculos110/49. '
    'Offline902 yPG240 anteriores corresponden a c86/R05v1; no se reatribuyen aesta composición. '
    'No broad actual,Actions,Chrome,imagen oLinux aceptados por esta fase;R05global sigueRED.')
for row in data['requisitos']:
    if row['id'] in {'R05','R19','QA-01','QA-02','QA-07','QA-08','QA-10','OPS07','QA-17'}:
        row['observaciones'].append('Checkpoint133: '+note)
        if REF not in row['commits']:row['commits'].append(REF)
        p='evidence/qa-ci33-main-r05v2-composition-20261020/phase-summary.json'
        if p not in row['evidencia']:row['evidencia'].append(p)
assert immutable(data)==prior
(D/'TRAZABILIDAD.json').write_bytes(enc(data))
(D/'ESTADO.md').write_bytes(('''# Estado de implementación

Checkpoint133 local: esquema33 y128 requisitos (92 originales y36 añadidos).
Todos los criterios anteriores se conservan exactos. Free:10 clientes activos,
1 plan por cliente al día y10 planes totales por gimnasio al día. Desktop sigue
soportado. Workspace de referencia intacto; sin push,PR,despliegue,cargos oenvíos.

Google33 ysu UI están integrados. QA-17 tiene corrección8a5e aceptada focalmente:
autor4casos y58regresiones; peer12SQLite y11PG PASS. La carrera HTTP canónica
conserva200+409 yuna cuenta,binding,perfil ycinco plantillas. Rollback incierto
sigue503,sin adopción oretry. Continuidad Google-only histórica,recuperación
total,alertas,custodia yvalidación externa siguen abiertas.

CI33 integrado desdec86 con composición explícitaR05v2. QA verificó193canarios
de workflow,157bloquesBash,110casosR05/49críticos ycontroles de binding/delta.
ROOT repitió verify-only enMAIN con exit0. Se conservan20reportes/240IDs33 y
5reportes/38IDs32. Los902offline y240PG verdes anteriores pertenecen ac86/v1;
52UUID propias quedaron ausentes y0sesiones comprobadas tras la pausa. Sus
testigos distinguen engine de negocio de sondeos auxiliares. Broad,Chrome,
Actions,Linux eimagen actual todavía requieren validación propia.
[Composición](evidence/qa-ci33-main-r05v2-composition-20261020/phase-summary.json).

R05v2 instalado:689archivos y45.910pins finitos,con ZIPv1 yalgoritmo conservados.
SEC revisó14.557ocurrencias nuevas/14.516pins y113controles; QA verificó el
binding separado. El escaneo real4f4ed7 sigueRED:44.433hallazgos brutos,
42.830clasificados y1.603bloqueantes nuevos. Su triage continúa; no hayPASSglobal.
Las evidencias añadidas después no se reatribuyen al árbol escaneado.

Backend34 yUI34 siguen aislados. QA-18 registra12canarias8PASS4RED originales;
la reparación41dc5 tiene replay de autor12PASS yespera revisión independiente.
Backend valida PG34 yrestore34 con lease55483; fallos de seed/harness se
conservan por separado. UI34 tiene72casos propios y15SSR/HTTP de autor verdes;
Chrome,accesibilidad yrevisión integrada están pendientes. No se infieren cobros,
renovaciones,contactos automáticos odictámenes clínicos.

R33 tiene precursor de dominio yguardas de ambos constructores con revisión
independiente;persistencia/API35 avanzan fuera deMAIN. PostgreSQL35,desktop y
UI nutricional siguen pendientes. R27,R31 yel resto del alcance continúan.
Retención/países,volumen/SLO,piloto yrevisión profesional necesitan datos o
participación real. VM yRedis6388 propios permanecen apagados.
[Registro](TRAZABILIDAD.md),[validación](VALIDACION.md).
''').encode())
(D/'ENTREGA.md').write_bytes(('''# Entrega candidata en curso

Checkpoint133 integraCI33 ysu composición revisada conR05v2.128requisitos,
todos sus criterios preservados. Verificador193workflow/157Bash PASS;902offline
y240PG se conservan atribuidos ac86/v1. MAIN sigue en esquema33. Backend/UI34,
QA-18,contrato35,R27/R31,broad,Chrome,imagen ydesktop final continúan abiertos.
R05global sigueRED1.603hallazgos. Free10clientes/1plancliente/día/10totalgym/día;
desktop soportado. Sin publicación odespliegue.
[Estado](ESTADO.md),[registro](TRAZABILIDAD.md).
''').encode())
append={'VALIDACION.md':note,'CAMBIOS.md':note,'DECISIONES.md':'Separar deriva de producto ydocumentación en el guardCI; escanear documentación completa conR05,sin excepción nueva por patrón. '+note}
for name,paragraph in append.items():
    p=D/name;raw=p.read_bytes();assert b'## Checkpoint133' not in raw
    p.write_bytes(raw.rstrip()+b'\n\n## Checkpoint133\n\n'+paragraph.encode()+b'\n')
proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=R,capture_output=True,check=True)
(C/'registry.stdout').write_bytes(proc.stdout);(C/'registry.stderr').write_bytes(proc.stderr)
assert all(sha((R/p).read_bytes())==h for p,h in preserved.items())
proof=D/'evidence/checkpoint133-closure-20261020';proof.mkdir();(proof/'.gitattributes').write_bytes(b'* -text\n')
receipt={'base':BASE,'source_import':REF,'registry':128,'previous_criteria_exact':128,'preexisting_untracked_preserved':len(preserved),'source_paths':products,'all_imported_paths_RAW_Git_exact':True,'ROOT_verify_only_exit':0,'CI33_PG240_reattributed':False,'global_R05_acceptance':False}
(proof/'receipt.json').write_bytes(enc(receipt));(proof/'driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',proof.relative_to(R).as_posix())
paths=[(D/p).relative_to(R).as_posix() for p in ['TRAZABILIDAD.json','TRAZABILIDAD.md','ESTADO.md','ENTREGA.md',*append]]
git('-c','core.autocrlf=true','add','--renormalize','--',*paths)
git('diff','--cached','--check')
git('commit','-m','Integrate current CI33 and bind its guards to reviewed R05v2')
assert immutable(json.loads((D/'TRAZABILIDAD.json').read_bytes()))==prior
assert not git('status','--porcelain','-uno').stdout.strip()
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),**receipt}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
