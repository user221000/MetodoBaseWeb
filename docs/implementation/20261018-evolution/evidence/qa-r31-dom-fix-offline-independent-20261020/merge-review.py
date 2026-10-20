from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('F:/mb-qa-browser31-20261020');TASK=Path(__file__).resolve().parent
OLD='be778fecfcea65f9dd8f50a45e847177b0a01ac1';FIX='c822c06d1459a4cc34a4582b80b5db2528f9da8a';BASE='8144cf6a261e4506207f4f824e2300686d8f805e'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def sha(raw):return hashlib.sha256(raw).hexdigest()
changed=git('diff','--name-only',BASE,FIX).decode().splitlines()
staged=git('diff','--name-only',OLD,'HEAD').decode().splitlines()
assert set(changed)<=set(staged)
rows=[]
for name in changed:
    raw=git('show','HEAD:'+name);expected=git('show',FIX+':'+name)
    assert raw==expected,name
    rows.append({'path':name,'staged_Git_LF_sha256':sha(raw),'equals_candidate_blob':True})
products=[n for n in staged if n.startswith(('web/','api/','core/','config/','src/'))]
assert len(products)==4
for name in ['web/static/js/session-shell.js','web/static/js/api.js','tests/e2e/session_shell31.cjs','tests/e2e/browser_compat31.cjs','tests/e2e/browser_native_compat31.cjs']:
    assert git('show',OLD+':'+name)==git('show','HEAD:'+name),name
extra=[n for n in staged if n not in changed]
assert all(n.startswith('docs/') or n in {'.gitattributes','tests/e2e/security_browser31_ui_peer.cjs'} for n in extra),extra
assert git('show','HEAD:tests/e2e/security_browser31_ui_peer.cjs')==git('show',BASE+':tests/e2e/security_browser31_ui_peer.cjs')
for name in ['.gitattributes','docs/implementation/20261018-evolution/evidence/.gitattributes']:
    lines=set(git('show','HEAD:'+name).decode().splitlines())
    assert set(git('show',OLD+':'+name).decode().splitlines())<=lines,name
    assert set(git('show',FIX+':'+name).decode().splitlines())<=lines,name
report={'old_head':OLD,'merged_head':git('rev-parse','HEAD').decode().strip(),'candidate':FIX,'candidate_base':BASE,'exact_candidate_paths':rows,'product_paths':products,'inherited_base_docs_attributes_and_security_test':extra,'merge_conflicts':False,'attribute_resolution':'No conflict; finite existing attributes from both histories retained.','unchanged_api_shell_common_and_native_helpers':True,'review':'Owned DOM references and idempotent branding invalidation; explicit session event listener; catches and continuations fenced after awaits. No API, backend, session-shell, capability or assertion changes.'}
(TASK/'merge-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
check=subprocess.run(['git','-C',str(ROOT),'-c','core.whitespace=cr-at-eol','diff',OLD,'HEAD','--check'],capture_output=True)
(TASK/'private/merge-diffcheck.stdout').write_bytes(check.stdout);(TASK/'private/merge-diffcheck.stderr').write_bytes(check.stderr)
assert check.returncode==0
print(json.dumps({'exact_paths':len(rows),'products':len(products),'conflicts':0,'diffcheck':0}))
