"""Freeze bounded CI30 source and accurately scoped author evidence."""
from pathlib import Path
import ast,hashlib,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(r'F:\mb-r12-history30-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');RUN=ROOT/'docs/implementation/20261018-evolution';EV=RUN/'evidence/ci-history-index30-author-20261019'
BASE='5d8e2bcf35c367e73632418f9364fb4f6410d129'
git=lambda *args,**kw:subprocess.check_output(['git',*args],cwd=ROOT,**kw)
sha=lambda data:hashlib.sha256(data).hexdigest()
norm=lambda path:path.read_bytes().replace(b'\r\n',b'\n')
assert git('rev-parse','HEAD',text=True).strip()==BASE
source_names=['.github/workflows/ci.yml','tests/run_reviewed_ci29.py','tests/verify_history_index_ci.py','tests/check_history_index_reports.py','tests/test_history_index_ci_trust.py','tests/test_member_ci_trust.py','tests/ci_history_index30/ci29-before.yml','tests/ci_history_index30/baseline.json']
sources={name:{'raw_sha256':sha((ROOT/name).read_bytes()),'git_lf_sha256':sha(norm(ROOT/name))} for name in source_names}
original=git('show','fd636202045efa30b1430f4a9dd8ab287ec76357:tests/test_member_ci_trust.py')
assert norm(ROOT/'tests/test_member_ci_trust.py').replace(b'verify_history_index_ci as guard',b'verify_member_links_ci as guard')==original
for name in ['tests/verify_member_links_ci.py','tests/run_reviewed_ci28.py','tests/check_member_link_reports.py','tests/integration_client_link_restore.py']:
    assert norm(ROOT/name)==git('show','fd636202045efa30b1430f4a9dd8ab287ec76357:'+name),name
target_names=git('ls-tree','-r','--name-only','fd636202045efa30b1430f4a9dd8ab287ec76357','--','web/database/alembic/schema_targets').decode().splitlines()
assert target_names
for name in target_names:assert norm(ROOT/name)==git('show','fd636202045efa30b1430f4a9dd8ab287ec76357:'+name),name
pg=TEMP/'metodobase-ci30-current-pg-first-20261019';history=TEMP/'metodobase-ci30-archive29-first-20261019';full=TEMP/'metodobase-ci30-guard-full-second-20261019';quality=TEMP/'metodobase-ci30-closure-quality-20261019';final=TEMP/'metodobase-ci30-postquality-verify-20261019'
read=lambda path:json.loads(path.read_bytes())
assert read(pg/'before.json')==read(pg/'after.json') and read(history/'before.json')==read(history/'after.json')
assert all(row['exit']==0 for row in read(pg/'summary.json')['results'])
assert len(read(quality/'independent-four-UUID-absence.json'))==4 and all(row['count']==0 for row in read(quality/'independent-four-UUID-absence.json'))
review=read(full/'review.json');assert len(review['reports'])==28 and len(review['unauthorized_delta_canaries'])==27 and len(review['current_report_canaries'])==55 and len(review['index_report_canaries'])==24 and len(review['current_inert_fixture_cases'])==27
final_review=read(final/'review.json');assert len(final_review['reports'])==28 and final_review['current_index_PG_exact_cases']==9
EV.mkdir(exist_ok=False);(EV/'.gitattributes').write_bytes(b'* -text\n')
secret=re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+')
classification=[]
def publish(source,relative):
    data=source.read_bytes();matches=len(secret.findall(data));zip_matches=[]
    if source.suffix=='.zip':
        with zipfile.ZipFile(source) as archive:
            for item in archive.infolist():
                if not item.is_dir() and secret.search(archive.read(item.filename)):zip_matches.append(item.filename)
    public=matches==0 and not zip_matches
    classification.append({'file':str(source),'public_file':relative,'bytes':len(data),'sha256':sha(data),'credential_pattern_matches':matches,'zip_members_matching':zip_matches,'published':public})
    if public:
        target=EV/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
def copy_tree(directory,prefix):
    for path in sorted(directory.rglob('*')):
        relative=path.relative_to(directory)
        if path.is_file() and 'source' not in relative.parts and 'owned-probes' not in relative.parts:
            if relative.parts[0] in {'private-evidence','private-restore-evidence'} and path.suffix not in {'.json','.jsonl'}:continue
            publish(path,prefix+'/'+relative.as_posix())
for directory,prefix in [(history,'historical29'),(pg,'current30'),(full,'full-before-quality'),(quality,'closure-quality'),(final,'postquality-verify'),(TEMP/'metodobase-ci30-guard-first-20261019','initial-ambiguous-probe'),(TEMP/'metodobase-ci30-guard-full-first-20261019','second-ambiguous-probe')]:copy_tree(directory,prefix)
for name in ['metodobase-ci30-prepare.py','metodobase-ci30-current-pg-run.py','metodobase-ci30-recover-and-quality.py','metodobase-ci30-archive29-prepare.py','metodobase-ci30-archive29-run.py','metodobase-ci30-archive29-preparation-20261019.json','metodobase-ci30-postquality-trust-20261019.xml','metodobase-ci30-first-units-20261019.xml','metodobase-ci30-correct-units-20261019.xml']:
    source=TEMP/name
    if source.exists():publish(source,'drivers-and-focals/'+name)
publish(Path(__file__),'drivers-and-focals/seal.py')
with zipfile.ZipFile(quality/'before-quality-source-exact.zip') as archive:
    previous=archive.read('tests/verify_history_index_ci.py').replace(b'\r\n',b'\n').decode()
    initial=previous.replace("('ignore-startup-failure', 'image', '--revision ' + REVISION + ' 2>/dev/null; then ready=1; break; fi', '--revision ' + REVISION + ' 2>/dev/null; then ready=1; break; fi; ready=1')","('ignore-startup-failure', 'image', 'then ready=1; break; fi', 'then ready=1; break; fi; ready=1')")
    initial=initial.replace("('weaken-VM-controls', 'frontend-contracts', '--minimum 3\\n', '--minimum 0\\n')","('weaken-VM-controls', 'frontend-contracts', '--minimum 3', '--minimum 0')")
    assert sha(initial.encode())=='112d4b4bda1b883752bf9d1881b6f76d595bfd5faa3e0459b5b6264ebf008908'
    (EV/'initial-ambiguous-probe-source.py').write_bytes(initial.encode())
    assert sha(previous.encode())==read(pg/'before.json')['files']['tests/verify_history_index_ci.py']
note={'initial_guard_failures':'The first two launches rejected an ambiguous mutation selector matching two image steps. No product/gate was weakened. Original source reproduced byte-exact from the before-quality ZIP and initial SHA; historical subrun evidence is retained. Outer trace is recorded in tool transcript, not represented as a captured RAW file.',
      'initial_unit_selector':'An initial invocation referenced non-existent tests/test_member_link_browser_runner.py and ran zero tests. Corrected actual file tests/test_member_browser_gate.py;74 maintained/new focused units pass. Not a product regression.',
      'full_gate_source':'Full79 report canaries+27 workflow mutants+27 inert probes ran before import sorting/explicit check=False/changed helper pins and diagnostic metadata. The exact full source is retained in before-quality-source-exact.zip and matches PG before/after. Final source passes Ruff,10 affected trust tests and verify-only historical guard27 mutations. No full-canary rerun claimed after these explicit equivalent changes; independent acceptance remains pending.',
      'wrapper_reporting_error':'All four subprocess modes passed; wrapper exit1 came from the wrong closure evidence filename. Original empty closure/summary retained; independent read-only exact4UUID absence recovery is separately recorded.'}
(EV/'honest-orchestration-notes.json').write_text(json.dumps(note,indent=2)+'\n',encoding='utf8')
(EV/'publication-classification.json').write_text(json.dumps(classification,indent=2)+'\n',encoding='utf8')
scope={'source_base':BASE,'historical29_pin':'fd636202045efa30b1430f4a9dd8ab287ec76357','historical28_pin':'66d9dec0e15dd873038bd248d3883daeeb27d4ca','historical_targets_unchanged':len(target_names),'source_files':sources,'old_member_trust_inverse_import_exact':True,'four_materialization_function_ASTs_equal':'verified by maintained new trust regression','actual_PG_index_cases':8,'actual_PG_restore30_cases':1,'actual_unchanged_PG_restore29_cases':1,'unit_cases_before_quality':74,'affected_trust_after_quality':10,'full_canaries_before_quality':{'workflow':27,'member_report':55,'index_report':24,'inert':27},'final_verify_only_passed':True,'owned_four_UUIDs_absent':True,'no_Actions_image_browser_SLO_claim':True,'independent_acceptance':'pending'}
(EV/'review.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf8')
doc=RUN/'CI_HISTORICO30.md'
doc.write_text('''# CI30 y aceptación histórica

Composición local aislada; no ejecución de Actions ni aceptación independiente por este informe. CI30 conserva los26 informes de29 y añade dos informes: ocho casos PostgreSQL de migración/consulta ordenada y el restore poblado30. El parser nuevo exige los nueve IDs exactos, sin duplicados, omisiones, sustituciones, skips o fallos. El checker anterior de cinco informes permanece idéntico.

El restore29 inmutable se ejecuta con tests/run_reviewed_ci29.py desde el commit real fd636202045efa30b1430f4a9dd8ab287ec76357. Su guard ejecuta a su vez el histórico28 desde66d9dec0e15dd873038bd248d3883daeeb27d4ca. Se autentica árbol/blobs/modos y se rechaza replace-ref/atributos/links/rutas no canónicas. No se cambia una assertion29 para que acepte30. Los cuatro métodos de extracción coinciden por AST con el runner endurecido28.

Evidencia autor: ocho PG de índice, un restore30 y un restore29 reales.74 unit focales antes del ajuste de imports/check=False; después pasan10 trust afectados y verify-only27 mutaciones con histórico real. El full anterior pasó55 canarios del checker29,24 del nuevo,27 mutaciones de workflow y27 probes Bash inertes. Cada alcance conserva su fuente; no se atribuye el full anterior a una repetición posterior. Ruff final verde. Cuatro UUID ausentes por consulta exacta independiente. [Detalles y errores preservados](evidence/ci-history-index30-author-20261019/review.json).

Se mantienen18 módulos Node/300 ejecuciones/279 criterios; CI30 no añade aserciones al recorrido16 de R12. El fixture actual usa30 real,29 tablas de negocio y30 físicas con alembic_version. Sus markers y witness de índice deben coincidir antes de readiness. Fuente/prosa Git LF y evidencia RAW con atributos -text se autentican por separado. Navegador real independiente y CI30 independiente siguen siendo gates de integración separados.
''',encoding='utf8')
sources[doc.relative_to(ROOT).as_posix()]={'raw_sha256':sha(doc.read_bytes()),'git_lf_sha256':sha(norm(doc))}
files={p.relative_to(EV).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(EV.rglob('*')) if p.is_file()}
freeze={'base':BASE,'sources':sources,'files':files,'files_count':len(files),'raw_attributes':'* -text','scope':scope};(EV/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf8')
raw=[p.relative_to(ROOT).as_posix() for p in sorted(EV.rglob('*')) if p.is_file()]
for i in range(0,len(raw),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*raw[i:i+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*raw[i:i+25]],cwd=ROOT,check=True,capture_output=True)
source_names.append(doc.relative_to(ROOT).as_posix())
subprocess.run(['git','-c','core.autocrlf=true','add','--',*source_names],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','diff','--cached','--check','--',*source_names],cwd=ROOT,check=True,capture_output=True)
batch=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in raw+source_names).encode());cursor=0
for name in raw+source_names:
    end=batch.index(b'\n',cursor);head=batch[cursor:end].split();assert head[1]==b'blob';size=int(head[2]);cursor=end+1
    expected=(ROOT/name).read_bytes() if name in raw else norm(ROOT/name)
    assert batch[cursor:cursor+size]==expected,name;cursor+=size+1
assert cursor==len(batch)
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert changed==set(raw+source_names)
subprocess.run(['git','commit','-m','Retain exact CI29 and gate current physical history index and restore30'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'source_files':len(source_names),'raw_evidence_files':len(raw),'freeze_sha256':sha((EV/'freeze.json').read_bytes()),'old_target_files_unchanged':len(target_names)}))
