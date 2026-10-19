"""Freeze CI30 follow-up source and honest author evidence with exact RAW blobs."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,xml.etree.ElementTree as ET
ROOT=Path(r'F:\mb-r23-history30-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');RUN=ROOT/'docs/implementation/20261018-evolution';DEST=RUN/'evidence/r23-ci30-author-20261019'
BASE='ee361d5f173ca0e5b748b34be1bff2e8672042e1'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a,**k:subprocess.check_output(['git',*a],cwd=ROOT,**k)
assert git('rev-parse','HEAD',text=True).strip()==BASE
DEST.mkdir(exist_ok=True);assert not (DEST/'manifest.json').exists();(DEST/'.gitattributes').write_bytes(b'* -text\n')
secret=re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+')
classification=[]
def copy(source,target):
    blob=source.read_bytes();count=len(secret.findall(blob))
    classification.append({'source':str(source),'target':target.relative_to(DEST).as_posix(),'bytes':len(blob),'sha256':sha(blob),'credential_pattern_matches':count,'published':not count})
    if not count:
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==blob,target
        else:target.write_bytes(blob)
def tree(source,target):
    for directory,dirs,files in os.walk(source):
        dirs[:]=[d for d in dirs if d!='source']
        for name in files:
            path=Path(directory)/name;copy(path,target/path.relative_to(source))
for stem,label in [('metodobase-r23-ci-full-second-20261019','full'),('metodobase-r23-ci-first-20261019','initial-selector-error'),('metodobase-r23-ci-node-first-20261019','node-before-block-fix'),('metodobase-r23-ci-node-second-20261019','node-before-cli-fix'),('metodobase-r23-ci-node-third-20261019','node-final')]:tree(TEMP/stem,DEST/label)
for name in ['metodobase-r23-ci-prepare.py','metodobase-r23-ci-workflow-recover.py','metodobase-r23-ci-finish-workflow.py','metodobase-r23-ci-normalize-wire.py','metodobase-r23-ci-focus-wire.py','metodobase-r23-ci-node-run.py','metodobase-r23-ci-node-replay.py','metodobase-r23-ci-node-replay-prepare.py','metodobase-r23-ci-node-third.py','metodobase-r23-ci-node-third-prepare.py','metodobase-r23-ci-candidate-failed.yml','metodobase-r23-ci-initial-diff.json']:
    copy(TEMP/name,DEST/'preparation'/name)
for name,count in [('metodobase-r23-ci-focused-20261019.xml',82),('metodobase-r23-ci-process-first-20261019.xml',5)]:
    path=TEMP/name;root=ET.fromstring(path.read_bytes());cases=root.findall('.//testcase');assert len(cases)==count and not any(root.findall('.//'+tag) for tag in ['failure','error','skipped']);copy(path,DEST/name)
sources=['.github/workflows/ci.yml','tests/verify_history_index_ci.py','tests/e2e/dashboard_followup_browser.cjs','scripts/check_followup_fixture.py','tests/check_followup_reports.py','tests/e2e/normalize_followup_report.py','tests/e2e/session_expiry_security.cjs','tests/test_followup_ci_process.py','tests/test_followup_ci_trust.py','docs/implementation/20261018-evolution/CI_R23_COMPOSICION30.md']
read=lambda p:json.loads(p.read_bytes())
full=read(DEST/'full/review.json');nodes=read(DEST/'node-final/summary.json')
assert full['historical_exit']==0 and len(full['reports'])==29 and len(full['unauthorized_delta_canaries'])==33 and len(full['current_report_canaries'])==55 and len(full['index_report_canaries'])==24 and len(full['followup_report_canaries'])==12 and len(full['current_inert_fixture_cases'])==27
assert nodes['sources_packages_stable'] and nodes['pip_exit']==0 and sum(r['Node_invocations'] for r in nodes['results'])==23 and all(r['exit']==0 for r in nodes['results'])
freeze={'base':BASE,'source_representation':'RAW plus GitLF; GitLF removes CRLF only','source_files':{name:{'bytes':len((ROOT/name).read_bytes()),'raw_sha256':sha((ROOT/name).read_bytes()),'git_lf_sha256':sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))} for name in sources},'source_scope_unchanged_during_Node':nodes['source_files'],'packages':89,'actual_Node_modules':23,'actual_Node_execution_minimum':348,'unit_runs':[82,5],'full_gate':{'PG_reports':29,'workflow_canaries':33,'parser_cases':[55,24,12],'old_inert_Bash':27},'scope':'Author local checks. Unit process seams are inert, Node modules real VM/controlled DOM. No new Chrome/PG, Actions or image. Existing QA8/16/768 source scopes remain separate; CI requires independent review.'}
def write(p,v):p.write_bytes((json.dumps(v,indent=2)+'\n').encode())
write(DEST/'source-freeze.json',freeze);write(DEST/'publication-classification.json',classification)
copy(Path(__file__),DEST/'seal-driver.py')
manifest={p.relative_to(DEST).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(DEST.rglob('*')) if p.is_file()}
write(DEST/'manifest.json',{'files':manifest});(DEST/'manifest.sha256').write_bytes((sha((DEST/'manifest.json').read_bytes())+'  manifest.json\n').encode())
proofs=sorted(p.relative_to(ROOT).as_posix() for p in DEST.rglob('*') if p.is_file())
for i in range(0,len(proofs),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*proofs[i:i+25]],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*proofs[i:i+25]],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=true','add','--',*sources],cwd=ROOT,check=True,capture_output=True)
for name in sources:assert git('show',':'+name)==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name
buffer=git('cat-file','--batch',input=''.join(':'+n+'\n' for n in proofs).encode());cursor=0
for name in proofs:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1
    assert buffer[cursor:cursor+size]==(ROOT/name).read_bytes(),name;cursor+=size+1
assert cursor==len(buffer)
changed=set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]);assert changed==set(sources+proofs)
subprocess.run(['git','diff','--cached','--check','--',*sources],cwd=ROOT,check=True,capture_output=True)
subprocess.run(['git','commit','-m','Require current followup facts and session fences in reviewed CI30'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW':len(proofs),'source_files':len(sources),'source_freeze_sha256':sha((DEST/'source-freeze.json').read_bytes()),'manifest_sha256':sha((DEST/'manifest.json').read_bytes())}))
