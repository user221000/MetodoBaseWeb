from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(r'F:\mb-retirement32-cleanup-qa-20261019');OLD=Path(r'F:\mb-retirement32-public-qa-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
EV=ROOT/'docs/implementation/20261018-evolution/evidence';HEAD='2273616eb218adfdd30680e111da50a4599a8c53';PREVIOUS='2b1a2e275abb26c291fb02a7a3e8f5a2e58ce2f5';SHA=lambda raw:hashlib.sha256(raw).hexdigest()
tree=ast.parse((TEMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scan');exec(compile(ast.Module(body=[fn],type_ignores=[]),'<reviewed-token-scanner>','exec'))
def write(path,raw):
    scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
def dump(path,value):write(path,(json.dumps(value,indent=2)+'\n').encode())
phase=TEMP/'metodobase-retirement32-qa-cleanup-http-20261019';out=EV/'qa-retirement32-cleanup-http-independent-20261019'
before=json.loads((phase/'before.private.json').read_bytes());after=json.loads((phase/'after.private.json').read_bytes());assert before==after and before['head']==HEAD and before['pip_check']==0 and before['runtime_RAW_equals_index_GitLF']
summary=json.loads((out/'summary.json').read_bytes());assert summary['exit']==0 and len(summary['HTTP_SSR_cases'])==8 and all(not(c['failed'] or c['error'] or c['skipped']) for c in summary['HTTP_SSR_cases'])
write(out/'source-environment-before.json',(phase/'before.private.json').read_bytes())
dump(out/'quiet.json',{'source_head':HEAD,'before_SHA256':SHA((phase/'before.private.json').read_bytes()),'after_SHA256':SHA((phase/'after.private.json').read_bytes()),'exact_equal':True,'runtime_sources':len(before['runtime_raw_sha256']),'runtime_RAW_equals_index_GitLF':True,'distribution_metadata':len(before['packages']),'pip_check_before':0,'pip_check_after':0,
    'scope':'344 runtime RAW hashes,89 installed distribution name/version metadata, Python/Node/Chrome binaries and exact own test quiet. No Chrome execution here, no every-distribution-byte claim.'})
write(out/'canary-source-preservation.json',(TEMP/'metodobase-retirement32-qa-cleanup-preservation.json').read_bytes())
prior=json.loads((TEMP/'metodobase-retirement32-qa-http-v2-20261019/before.private.json').read_bytes())
assert set(prior['runtime_raw_sha256'])==set(before['runtime_raw_sha256'])
changed=[name for name in prior['runtime_raw_sha256'] if prior['runtime_raw_sha256'][name]!=before['runtime_raw_sha256'][name]]
assert changed==['web/routes/progress_retirement.py']
assert prior['owned_test_SHA256']==before['owned_test_SHA256']
dump(out/'runtime-delta.json',{'source_before':prior['head'],'source_after':HEAD,'runtime_paths':len(before['runtime_raw_sha256']),'other_runtime_RAW_exact':343,'changed_paths':changed,'test_RAW_SHA256_both':before['owned_test_SHA256'],
    'scope':'Both factories replay the same8 semantic criteria and entire test RAW file. _execute cleanup is the sole runtime source delta; AST outside that function is exact. No browser re-attribution; SEC adversarial cleanup peer remains separate.'})
archive=TEMP/(phase.name+'-originals-private.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
    for item in phase.iterdir():
        if item.is_file():bundle.write(item,item.name)
dump(out/'private-originals.json',{'archive_name':archive.name,'bytes':archive.stat().st_size,'SHA256':SHA(archive.read_bytes()),'uploaded':False,'contents':'RAW stdout/stderr/JUnit and before/after source/pkg/bin/test photographs; synthetic private account proof context remains private.'})
files=[]
for item in sorted(out.iterdir()):
    if item.is_file():raw=item.read_bytes();scan(raw,item.name);files.append({'path':item.name,'bytes':len(raw),'SHA256':SHA(raw)})
dump(out/'manifest.json',{'source_head':HEAD,'files':files});manifest_sha=SHA((out/'manifest.json').read_bytes())
review=EV/'qa-retirement32-review227-20261019';review.mkdir(exist_ok=False);write(review/'.gitattributes',b'* -text\n')
for name in ('metodobase-retirement32-qa-cleanup-prepare.py','metodobase-retirement32-qa-cleanup-preservation.json'):
    write(review/name,(TEMP/name).read_bytes())
old_path='docs/implementation/20261018-evolution/evidence/qa-retirement32-review219-20261019/manifest.json'
old_raw=(OLD/old_path).read_bytes();assert subprocess.check_output(['git','show',PREVIOUS+':'+old_path],cwd=OLD)==old_raw
dump(review/'review.json',{'source_head':HEAD,'status':'PASS_SCOPED_FUNCTIONAL_REPLAY_ONLY','own_HTTP':'Same8 HTTP cases remain8/8 after cleanup repair, both actual factories. Entire test RAW unchanged from219 v2;4 business test ASTs also unchanged from initial helper-diagnostic phase.',
    'source':'344 runtime RAW/indexGitLF verified and quiet before/after,89 distribution name/version metadata+Python/Node/Chrome binary hashes+own test quiet; pip0. Exactly343 runtime RAW paths equal219; only _execute file differs, module AST outside_execute exact.',
    'browser':'No Chrome run on227. The13 real groups/9 scoped axe screenshots and process closure belong exclusively219 and retain that source attribution. No UI/header/contract/schema/auth policy source changed in227.',
    'limits':'SEC18 retained-Session failure-tuple adversarial acceptance is separate. No PG, VM, Redis/provider, global MFA/privacy/R25, clinical/production/SLO acceptance. Own functional COMMIT-ACK-only seam still uses real rollback/close.',
    'before_evidence':{'commit':PREVIOUS,'prefix':'qa-retirement32-review219-20261019','manifest_SHA256':SHA(old_raw)},
    'after_evidence':{'prefix':out.name,'manifest_SHA256':manifest_sha,'files':len(files)}})
write(review/'seal-driver.py',Path(__file__).read_bytes())
entries=[{'path':item.name,'bytes':item.stat().st_size,'SHA256':SHA(item.read_bytes())} for item in sorted(review.iterdir()) if item.is_file()]
dump(review/'manifest.json',{'source_head':HEAD,'files':entries})
print(json.dumps({'source_head':HEAD,'http_manifest_SHA256':manifest_sha,'review_manifest_SHA256':SHA((review/'manifest.json').read_bytes()),'HTTP_cases':8,'runtime_other_RAW_exact':343}))
