from pathlib import Path
import hashlib,json,subprocess,sys
r=Path(__file__).parent;a=Path('F:/MetodoBaseWeb-recovery-20261019');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
historical=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/recovery-security-independent-20261019')
old=json.loads((historical/'sources-after.json').read_text());old_manifest_sha=sha(historical/'source.json');assert old_manifest_sha=='2bd7f953fbca1385f17034f9e30d91d932185523e5e3ada9527826abc858c380'
assert len(old['sources'])==87
current={n:sha(a/n) for n in old['sources']}
changed=[n for n in current if current[n]!=old['sources'][n]];assert changed==['web/middleware/security_headers.py'],changed
for name,digest in old['proofs'].items():assert sha(a/'docs/implementation/20261018-evolution/evidence'/name)==digest
assert subprocess.run(['git','rev-parse','HEAD'],cwd=a,capture_output=True,check=True,text=True).stdout.strip()=='890a435e757a671310b8b89c6e3dc934db862b5f'
assert not subprocess.run(['git','status','--porcelain'],cwd=a,capture_output=True,check=True,text=True).stdout
current['tests/test_recovery_method_headers.py']=sha(a/'tests/test_recovery_method_headers.py')
driver='test_recovery_headers_semantic_security.py';assert sha(r/driver)=='5f47b04b387770499232c68418342304defbc67aec3c4e3095e3fcf1dc49b23a'
record={'author_commit':'890a435e757a671310b8b89c6e3dc934db862b5f','baseline_author_commit':old['commit'],'baseline_review_manifest_sha256':old_manifest_sha,'baseline_source_count':87,'baseline_delta':changed,'sources':current,'source_count':88,'author_checkout_clean':True,'semantic_driver_sha256':sha(r/driver),'common_fixture_sha256':sha(r/'test_recovery_security.py')}
(r/('sources-'+sys.argv[1]+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8');print(json.dumps({'phase':sys.argv[1],'baseline_sources':87,'expected_changed':changed,'current_monitored_sources':88,'clean':True}))
