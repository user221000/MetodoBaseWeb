"""Commit exact source plus preserved VM proofs for the control-ownership fix."""
import hashlib,json,shutil,subprocess
from pathlib import Path
root=Path('F:/mb-r12-ui-fix29-20261019')
temp=Path('C:/Users/Consu/AppData/Local/Temp')
run=root/'docs/implementation/20261018-evolution';proof=run/'evidence/r12-controls-author-20261019'
parent='93975691e02daac966b871e218db76e4a3dd0114'
def git(*args,**kw):return subprocess.check_output(['git',*args],cwd=root,**kw)
sha=lambda value:hashlib.sha256(value).hexdigest()
assert git('rev-parse','HEAD',text=True).strip()==parent
proof.mkdir(exist_ok=False);(proof/'.gitattributes').write_bytes(b'* -text\n')
source=temp/'metodobase-r12-controls-author-v3-20261019'
for path in sorted(source.iterdir()):
    assert path.is_file();shutil.copyfile(path,proof/path.name)
for name in ['metodobase-r12-controls-author.py','metodobase-r12-controls-author-v2.py','metodobase-r12-controls-author-v3.py','metodobase-r12-controls-author-executed-v2.py','metodobase-r12-controls-author-executed-v3.py','metodobase-r12-controls-source-diagnose.py']:
    shutil.copyfile(temp/name,proof/name)
qa=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-r12-composition29-independent-20261019/final939')
for name in ['control_scope_review_v2.cjs','control-scope-v2-before-receipt.json','control-scope-before-v2.raw.json']:
    shutil.copyfile(qa/name,proof/('independent-'+name))
paths=['web/static/js/vinculos-ui.js','web/static/js/vinculos-profesional.js','web/static/js/vinculos-lectura.js','web/static/js/vinculos-invitacion.js','tests/e2e/member_link_consumers.cjs','tests/e2e/member_link_controls.cjs']
doc=run/'R12_CONTROLES_INDEPENDIENTES.md'
doc.write_bytes(('''# Controles de vínculos y exportación independientes

En9397569, una operación de vínculos capturaba y restauraba el estado disabled de todos los botones, inputs y selects del documento. La exportación se inicializa en paralelo dentro del mismo main y habilita su botón al verificar la cuenta. Restaurar el estado anterior de ese botón ajeno podía dejarlo deshabilitado. QA reprodujo el fallo en PostgreSQL real y Chrome: los primeros siete criterios pasaron; exportación, criterio8, falló;9–16 no se alcanzaron.

VinculosUI.setup exige ahora ownedControls, una función que devuelve los controles del consumidor. Consulta, bloqueo temporal, restauración e invalidación sólo actúan sobre esa colección. Los tres consumidores enumeran sus controles estáticos y los descendientes de su lista propia; la exportación conserva su ciclo de vida. No se usa el main como límite porque contiene ambos consumidores. Autorización, fences de sesión, borrado de vistas, BlobURLs y acciones explícitas mantienen sus reglas.

El mismo driver independiente reproduce dos fallos y un control verde antes; las tres aserciones pasan después. Las16 regresiones existentes pasan con sus aserciones intactas. El adaptador mínimo de DOM incorpora selectores nativos por etiqueta para recorrer los controles dinámicos. Node comprueba la sintaxis de los seis archivos. Estos son controles VM; la aceptación de navegador posterior sigue pendiente en este commit.

Las fuentes4934 permanecieron estables durante el ensayo. El checkout raíz previo eraLF, mientras el checkout de QA eraCRLF: sus hashesRAW son distintos y se autentica la igualdad del contenidoGitLF. Dos preparaciones del autor compararon inicialmente esas representaciones de manera incorrecta y se detuvieron antes de ejecutar pruebas; scripts originales conservados. [Pruebas y fuente](evidence/r12-controls-author-20261019/freeze.json).
''').encode())
freeze={'parent':parent,'product_files':paths[:4],'test_files':paths[4:],'source':{name:{'RAW_sha256':sha((root/name).read_bytes()),'LF_sha256':sha((root/name).read_bytes().replace(b'\r\n',b'\n'))} for name in paths},
        'QA_before_LF_equivalence':'QA b582e61f is CRLF representation of Git/root fe109ac1. Both authentic originals retained; no claim of equal RAW bytes.',
        'author_focal':'same3:before2red/1green,after3green;existing16green;syntax6green;4934filesstable',
        'independent_driver_SHA256':'51f9a1bc7a3b7a90d906017920ece2c5c54f37275aa2d9ed9728ba6c4f374c1d',
        'independent_browser_acceptance':'pending; original939 remains rejected at criterion8/16'}
(proof/'freeze.json').write_bytes((json.dumps(freeze,indent=2)+'\n').encode())
shutil.copyfile(__file__,proof/'package-driver.py')
raw=sorted(path for path in proof.rglob('*') if path.is_file())
(proof/'evidence-manifest.json').write_bytes((json.dumps({'file_count':len(raw),'files':{p.relative_to(proof).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in raw}},indent=2)+'\n').encode())
raw.append(proof/'evidence-manifest.json')
ordinary=paths+[doc.relative_to(root).as_posix()]
subprocess.run(['git','-c','core.autocrlf=true','add','--',*ordinary],cwd=root,check=True,capture_output=True)
names=[p.relative_to(root).as_posix() for p in raw]
for index in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[index:index+25]],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[index:index+25]],cwd=root,check=True,capture_output=True)
assert not git('diff','--cached','--check','--',*ordinary,stderr=subprocess.STDOUT)
staged=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names+ordinary).encode())
cursor=0;normal=[]
for name in names+ordinary:
    end=staged.index(b'\n',cursor);header=staged[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1
    blob=staged[cursor:cursor+size];working=(root/name).read_bytes()
    if name in names:assert blob==working,name
    else:
        assert blob==working.replace(b'\r\n',b'\n'),name
        if blob!=working:normal.append(name)
    cursor+=size+1
assert cursor==len(staged)
assert set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+ordinary)
subprocess.run(['git','commit','-m','Scope member link controls to their own consumers'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_proof_blobs_exact':len(names),'source_LF_normalization_only':normal,'freeze_sha256':sha((proof/'freeze.json').read_bytes())}))
