"""Seal real MAIN30 regression and bounded independent R23 composition/focus proofs."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence';TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
BASE='6d4e8b411a3f55dde0df250225b506e35f1f57e9'
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_bytes())
git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=ROOT,**k)
def write(p,s):p.write_bytes(s.encode('utf8'))
assert git('rev-parse','HEAD',text=True).strip()==BASE and not git('status','--porcelain','--untracked-files=no')
raw=set()
def authenticate(directory,manifest,digest):
    p=EV/directory/manifest;assert sha(p.read_bytes())==digest,p
    for row in read(p)['files']:
        target=p.parent/row['path'];assert target.resolve().is_relative_to(p.parent.resolve())
        blob=target.read_bytes();assert sha(blob)==row['sha256'] and len(blob)==row['bytes'],target;raw.add(target)
    assert (p.parent/'.gitattributes').read_bytes()==b'* -text\n';raw.add(p)
authenticate('qa-r23-composition30-independent-20261019','partial-manifest.json','76eceb4053df86d4ef41b6f45dceeddf8232c0f52c8709c7ec23b5d9d7012650')
authenticate('qa-r23-focus-independent-20261019','manifest.json','43d78445c7a90cae3b997aa4dc63c648eef3f1f7b877d7ea196fb71a9bf69880')
reg=TEMP/'metodobase-main30-regression-first-20261019';summary=read(reg/'summary.private.json')
assert summary['head']==BASE and summary['coverage_exit']==summary['pip_exit']==0 and summary['sources_packages_stable']
assert summary['sources']==7381 and summary['packages']==89 and len(summary['results'])==2
for row in summary['results']:
    assert row['exit']==0 and row['cases']==2492 and not row['failures'] and len(row['skips'])==1
    assert row['skips'][0]['case']=='test_symlink_cannot_redirect_a_private_document'
dest=EV/'main30-regression-20261019';dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
secret=re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+')
names=['before.json','after.json','before-pip.log','after-pip.log','serial.xml','shuffle.xml','serial-summary.json','shuffle-summary.json','coverage.xml','coverage.json','coverage-check.stdout.log','coverage-check.stderr.log','serial.stdout.private.log','serial.stderr.private.log','shuffle.stdout.private.log','shuffle.stderr.private.log']
classification=[]
for name in names:
    p=reg/name;blob=p.read_bytes();count=len(secret.findall(blob))
    classification.append({'file':name,'sha256':sha(blob),'bytes':len(blob),'credential_pattern_matches':count,'published':not count})
    if not count:shutil.copyfile(p,dest/name.replace('.private',''))
write(dest/'summary.json',json.dumps(summary,indent=2)+'\n');write(dest/'publication-classification.json',json.dumps(classification,indent=2)+'\n')
shutil.copyfile(TEMP/'metodobase-main30-regression.py',dest/'driver.py')
write(dest/'manifest.json',json.dumps({'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.iterdir())}},indent=2)+'\n');raw.update(dest.iterdir())
data=read(RUN/'TRAZABILIDAD.json');keys=['fuente','seccion','problema','criterio_exacto'];criteria={r['id']:{k:r[k] for k in keys} for r in data['requisitos']};assert len(criteria)==107
notes={
 'R05':('MAIN30 mismo6d4e8b4:2491pass+1skip Windows conocido en serie/cobertura y n2/shuffle;7381fuentes/89paquetes quietos,pip0,cobertura0. Sin PG/Linux/Actions por este gate.',['main30-regression-20261019/summary.json']),
 'R12':('Regresión amplia30 integrada verde2491+1 por modo. Composición aislada R23/expiry sobre30:QA50unit+16freshR12+fixture0 y preservación perfiles/CAS/revocación; no se atribuye a MAIN antes de merge.',['main30-regression-20261019/summary.json','qa-r23-composition30-independent-20261019/partial-summary.json']),
 'QA11':('Amplia actual30 verde en ambos modos. CI adicional R23 todavía aislado en preparación, sin Actions ni imagen nueva.',['main30-regression-20261019/summary.json']),
 'R13':('QA composición30 aislada:118Node,8freshR23+16freshR12. Control propio768 halló pérdida de foco pese a activación correcta; ee361d5 corrige continuidad respetando cambio voluntario de foco. Mismo addon después3/3+30Node independientes. Rojo previo intacto; no dictamen WCAG global.',['qa-r23-composition30-independent-20261019/partial-summary.json','qa-r23-focus-independent-20261019/final-summary.json']),
 'R23':('Aceptación parcial aislada:53HTTP+50R12unit+2PG ambasfactories+4HTTPpropios+118Node+8freshR23+16freshR12.768 foco antes1/3, después3/3 y30Node; reflow/axe sección0errores observados. Faltan responsables persistidos/eventos atribuibles y resultados; no cerrar por pantalla.',['qa-r23-composition30-independent-20261019/partial-summary.json','qa-r23-focus-independent-20261019/final-summary.json']),
 'R31':('Composición R23/expiry aislada revisada en30 sin nuevos datos sensibles, sólo consulta. No acredita política de conservación ni cierre privacidad general; cinco UUID originales+focal cerrados según recibos independientes.',['qa-r23-composition30-independent-20261019/partial-summary.json','qa-r23-focus-independent-20261019/final-summary.json'])}
for row in data['requisitos']:
    if row['id'] in notes:
        note,files=notes[row['id']];row['observaciones'].append('Checkpoint113: '+note)
        for name in files:
            if 'evidence/'+name not in row['evidencia']:row['evidencia'].append('evidence/'+name)
write(RUN/'TRAZABILIDAD.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
state=(RUN/'ESTADO.md').read_text(encoding='utf8').replace('Checkpoint112 local:107 registros','Checkpoint113 local:107 registros')
state=state.replace('Nuevo gate amplio sobre MAIN30 pendiente.','Regresión amplia sobre MAIN30 verde:2491pass+1 omisión Windows conocida en serie/cobertura y n2/shuffle;7381fuentes/89paquetes estables,pip0,cobertura0. [Amplia30](evidence/main30-regression-20261019/summary.json).')
state=state.replace('Emisor e8+fix9eb aceptados focalmente por Seguridad102/102, todavía aislados.','Emisor e8+fix9eb aceptados focalmente por Seguridad102/102, todavía aislados. QA composición30:53HTTP+50R12unit+2PG+4propios+118Node+8freshR23+16freshR12. Control768 halló pérdida de foco; correcciónee361d5 pasa el mismo addon3/3+30Node propios/mantenidos. Se conserva el rojo y se acota axe a la sección. CI adicional R23 en preparación, no integrado aún.')
state=state.replace('Siguiente: regresión amplia30; componer R23/expiración y reconstruir Linux.','Siguiente: cerrar CI y componer R23/expiración; preparar reparación Expat con revisión independiente y reconstruir Linux.')
write(RUN/'ESTADO.md',state)
delivery=(RUN/'ENTREGA.md').read_text(encoding='utf8').replace('Checkpoint112:107 registros','Checkpoint113:107 registros').replace('regresión amplia30 pendiente.','regresión amplia30 verde2491+1 por modo serial/cobertura y n2/shuffle;7381fuentes/89paquetes estables,pip0.')
write(RUN/'ENTREGA.md',delivery)
for name,note in {
 'VALIDACION.md':'MAIN30 6d4e8b4:2491pass+1skip Windows conocido en serie/cobertura731.093s y n2/shuffle277.25s. Gate cobertura0,7381fuentes/89paquetes quietos,pip0. QA R23 aislado53HTTP/50R12unit/2PG/4propios/118Node/8R23real/16R12real; addon768 antes1/3 por foco, después mismo3/3 y30Node. Recursos propios cerrados, evidencias exactas por scope; sin Actions/imagen/SLO.',
 'CAMBIOS.md':'Se sella regresión amplia del esquema30 integrado. Se autentican147+manifest de composición R23 y42+manifest de corrección de foco; ambos aislados, sin presentar CI adicional como integrado.107 criterios exactos preservados.',
 'RIESGOS.md':'R23 sigue parcial por responsables/eventos no persistidos. El foco768 fue corregido y revisado sólo en fuente aislada; no declaración global de accesibilidad. MFA31 y R24 tienen hallazgos funcionales/concurrencia en corrección; no aceptados. Expat requiere reparar componente cargado y artefacto real; Linux y71OS siguen abiertos.',
 'DECISIONES.md':'No repetir amplia30 ya verde sin cambios de fuente relevantes. Conservar el control768 rojo y validar corrección con addon idéntico. Registro de consumo evita doble escritura antes de await y conserva CAS real; contratos R24/MFA31 aún en validación, sin nuevas políticas comerciales o de retención.'}.items():
    with (RUN/name).open('ab') as f:f.write(('\n\n## Checkpoint 113\n\n'+note+'\n').encode())
subprocess.run([sys.executable,'-X','utf8','scripts/implementation_registry.py','--render','--check'],cwd=ROOT,check=True)
assert {r['id']:{k:r[k] for k in keys} for r in read(RUN/'TRAZABILIDAD.json')['requisitos']}==criteria
driver=EV/'checkpoint113-driver.py';receipt=EV/'checkpoint113-review.json';assert not driver.exists() and not receipt.exists();shutil.copyfile(__file__,driver);raw.add(driver)
write(receipt,json.dumps({'base':BASE,'registry_count':107,'criteria_exact':True,'product_code_changed':False,'raw_files':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(raw)}},indent=2)+'\n');raw.add(receipt)
docs=[(RUN/n).relative_to(ROOT).as_posix() for n in ['ESTADO.md','ENTREGA.md','VALIDACION.md','CAMBIOS.md','RIESGOS.md','DECISIONES.md','TRAZABILIDAD.json','TRAZABILIDAD.md']];names=sorted(p.relative_to(ROOT).as_posix() for p in raw)
for i in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[i:i+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[i:i+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*docs],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','diff','--cached','--check','--',*docs],cwd=ROOT,check=True,capture_output=True)
buffer=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in names).encode());cursor=0
for name in names:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name;cursor+=size+1
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert cursor==len(buffer) and changed.issubset(set(names+docs)) and set(docs).issubset(changed)
subprocess.run(['git','commit','-m','Seal current schema30 regression and independent followup focus review'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_authenticated':len(names),'registry':107,'broad_per_mode':2491,'known_skip':1}))
