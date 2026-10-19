"""Close CI29 wiring sources and scoped author evidence; no runtime change."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
root=Path('F:/mb-r12-ci29-20261019');temp=Path('C:/Users/Consu/AppData/Local/Temp')
run=root/'docs/implementation/20261018-evolution';proof=run/'evidence/ci-member-links29-author-20261019'
parent='93975691e02daac966b871e218db76e4a3dd0114'
sha=lambda value:hashlib.sha256(value).hexdigest()
def git(*args,**kw):return subprocess.check_output(['git',*args],cwd=root,**kw)
assert git('rev-parse','HEAD',text=True).strip()==parent
proof.mkdir(exist_ok=False);(proof/'.gitattributes').write_bytes(b'* -text\n')
phases={
 'format-first':temp/'metodobase-ci29-report-format-20261019',
 'format-after':temp/'metodobase-ci29-report-format-v2-20261019',
 'inert-before':temp/'metodobase-ci29-inert-before-20261019',
 'fixture-trust':temp/'metodobase-ci29-fixture-trust-20261019',
 'quality':temp/'metodobase-ci29-quality-20261019',
 'restore-preflight':temp/'metodobase-ci29-restore-preflight-20261019',
 'restore-before':temp/'metodobase-ci29-historical-restore-v2-20261019',
 'restore-after':temp/'metodobase-ci29-historical-restore-v3-20261019',
 'guard-after':temp/'metodobase-ci29-guard-author-after-20261019',
 'current-trust-final':temp/'metodobase-ci29-current-trust-final-20261019',
}
for label,directory in phases.items():
    assert directory.is_dir(),label
    for path in sorted(directory.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(directory)
        # Original Git archives are authenticated by their receipt; do not
        # duplicate entire old source trees or all extracted inert probes.
        if any(part in {'source','owned-probes','owned-shadow'} for part in relative.parts):continue
        target=proof/label/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
helpers=['metodobase-ci29-prepare.py','metodobase-ci29-report-format.py','metodobase-ci29-report-format-v2.py',
 'metodobase-ci29-inert-before.py','metodobase-ci29-historical-restore.py','metodobase-ci29-historical-restore-v2.py',
 'metodobase-ci29-historical-restore-v3.py','metodobase-ci29-historical-restore-executed-v2.py',
 'metodobase-ci29-historical-restore-executed-v3.py','metodobase-ci29-restore-diagnose.py','metodobase-ci29-restore-resources.py',
 'metodobase-ci29-quality.py','metodobase-ci29-fixture-trust.py','metodobase-ci29-restore-preflight.py']
for name in helpers:shutil.copyfile(temp/name,proof/name)
errata={'initial_full_inert_failure':'Missing browser_evidence assignment in inert-only prefix; exact first case replay retained before repair. The first failed temporary full probe directory was removed by its context manager; no claim of retained original XMLs from that attempt. Later verifier retains all owned probes including failures.',
 'restore_preparation1':'Python encoding spelling utf8-sig rejected before DB work; original helper retained. Corrected to utf-8-sig.',
 'restore_preparation2':'Missing documented evidence directory caused one setup error; original2case XML retained, backup/restore namespaces confirmed empty. Correct configuration then2/2green.',
 'VM_interface':'Canonical row key repaired first, then distinct Storage event labels; every assertion byte unchanged.',
 'final_guard_scope':'Full20+55+27 ran before only BASELINE_SHA expanded to three pinned unchanged fixture sources. Seven trust probes and final CLI verify-only then passed. Restore preflight added afterwards and5pure probes passed. No assertion/body/actualworkflow change after full27.'}
(proof/'preparation-errata.json').write_bytes((json.dumps(errata,indent=2)+'\n').encode())
paths=['.github/workflows/ci.yml','tests/run_reviewed_ci28.py','tests/check_member_link_reports.py','tests/verify_member_links_ci.py',
 'tests/ci_member_links29/ci28-before.yml','tests/ci_member_links29/baseline.json',
 'tests/e2e/member_link_context.cjs','tests/e2e/member_link_fragment.cjs','tests/e2e/member_link_api.cjs','tests/e2e/member_link_consumers.cjs']
freeze={'parent':parent,'runtime_product_changes':False,
 'source':{name:{'RAW_sha256':sha((root/name).read_bytes()),'LF_sha256':sha((root/name).read_bytes().replace(b'\r\n',b'\n'))} for name in paths},
 'historical_pin':'66d9dec0e15dd873038bd248d3883daeeb27d4ca','baseline_sha256':'fddb39ddbf9dc59460464192b44a2833a9546625ad492f49c1e7cab1f4f5198c',
 'author_checks':{'workflow_mutants':20,'report_cases':55,'inert_process_cases':27,'fixture_trust_cases':7,'restore_preflight_cases':5,'changed_VM_assertions_green':80,'unchanged_historical_real_restores_green':2,'quality_syntax_sources':502,'new_Bandit_findings':0},
 'not_claimed':['One complete broad execution','Current29 restore execution by this CI runner','R12 browserCI','Actions','Corrected image or providers'],
 'independent_review':'Pending; separate author source/evidence freeze'}
(proof/'freeze.json').write_bytes((json.dumps(freeze,indent=2)+'\n').encode())
shutil.copyfile(__file__,proof/'package-driver.py')
raw=sorted(path for path in proof.rglob('*') if path.is_file())
# Public command logs contain only synthetic assertion labels/results; withhold
# any unexpected complete session proof instead of silently rewriting RAW.
for path in raw:
    if path.suffix in {'.json','.xml','.log'}:
        assert not re.search(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])',path.read_bytes()),path
(proof/'evidence-manifest.json').write_bytes((json.dumps({'file_count':len(raw),'files':{p.relative_to(proof).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in raw}},indent=2)+'\n').encode());raw.append(proof/'evidence-manifest.json')
ordinary=paths+[(run/'R12_CI29.md').relative_to(root).as_posix()]
subprocess.run(['git','-c','core.autocrlf=true','add','--',*ordinary],cwd=root,check=True,capture_output=True)
names=[path.relative_to(root).as_posix() for path in raw]
for index in range(0,len(names),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*names[index:index+25]],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*names[index:index+25]],cwd=root,check=True,capture_output=True)
assert not git('diff','--cached','--check','--',*ordinary,stderr=subprocess.STDOUT)
buffer=git('cat-file','--batch',input=''.join(':'+name+'\n' for name in names+ordinary).encode());cursor=0
for name in names+ordinary:
    end=buffer.index(b'\n',cursor);header=buffer[cursor:end].split();assert header[1]==b'blob';size=int(header[2]);cursor=end+1
    expected=(root/name).read_bytes();expected=expected if name in names else expected.replace(b'\r\n',b'\n')
    assert buffer[cursor:cursor+size]==expected,name;cursor+=size+1
assert cursor==len(buffer) and set(git('diff','--cached','--name-only','-z').decode().split('\0')[:-1])==set(names+ordinary)
subprocess.run(['git','commit','-m','Add bounded CI29 reports and exact historical source execution'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not git('status','--porcelain','--untracked-files=no')
print(json.dumps({'commit':git('rev-parse','HEAD',text=True).strip(),'RAW_proof_blobs_byte_exact':len(names),'source_and_doc_files':len(ordinary),'freeze_sha256':sha((proof/'freeze.json').read_bytes())}))
