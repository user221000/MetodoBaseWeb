from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

ROOT=Path(r'F:\mb-security-terminal-sv-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-terminal-sv-peer-independent-20261019'
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-sec15-peer-private-20261019')
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
head='6a75d096ea3d63d9e78c76d33b7e243160b23364'
base='809eab28c40c112cb6e3c9d8caceebae28683abd'
assert git('rev-parse','HEAD').decode().strip()==head
assert (OUT/'.gitattributes').read_bytes()==b'* -text\n'
summary=json.loads((OUT/'summary.json').read_bytes())
assert summary['outcomes']=={'passed':41,'failure':0,'error':0,'skipped':0}
author=Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\root-mfa31-terminal-sv-author-20261019')
ours=json.loads((OUT/'cases.STRUCTURAL.json').read_bytes())
prior=json.loads((author/'after/cases.STRUCTURAL.json').read_bytes())
def ids(items):return {c['case'] if 'case' in c else c['classname']+'::'+c['name'] for c in items}
assert len(prior)==14 and ids(prior)<=ids(ours) and len(ours)==len(ids(ours))==41
changed=git('diff','--name-only',base,head).decode().splitlines()
assert changed==['tests/test_mfa31_terminal_session_version.py','web/services/mfa_service.py','web/static/js/mfa-ui.js']
for n in ['tests/test_recovery28_review.py','tests/test_mfa31_http.py']:
    assert git('show',base+':'+n)==git('show',head+':'+n)

(OUT/'seal-driver.py').write_bytes(Path(__file__).read_bytes())
review='''Independent SEC15 review — PASS_FOCAL_INDEPENDENT

Reviewed source6a75d096ea3d63d9e78c76d33b7e243160b23364 against parent809eab28c40c112cb6e3c9d8caceebae28683abd. The three-path delta admits the already-valid terminal integer version during identity validation. It does not change token verification, primary authentication, account/parent eligibility, factor verification, grant binding, schema or catalog. The two historical recovery/MFA test modules are Git-byte identical to the parent; all14 exact author case IDs were replayed.

Factor-changing paths reject insufficient capacity after reloading/locking the persisted actor and before creating/looking up a credential, consuming a proof, checking/consuming factor evidence, publishing a new seed or changing pending state. _revoke_sessions repeats the guard immediately before incrementing. No decrement, wrap, reset or alternate bypass was added. The terminal identity still completes a real password challenge and one-use second factor before receiving an access/refresh pair. Security changes that require another session-version increment remain unavailable at the terminal value; operational recovery for that exceptional state is not implemented or claimed here.

Independent first run:41/41 passed, zero failed/errored/skipped. This includes the14 exact author cases plus27 own canaries:17 persisted/in-memory synthetic corruption and canonical-parent checks, and10 actual HTTP cases over both real factories. The latter cover terminal revocation and factor replacement without SQL-state consumption, the last valid increment during enrollment confirmation and recovery-code regeneration, invalidation of previous sessions, continued factor challenge atMAX, and rejection of an older challenge without consuming recovery evidence. Invalid version types are deliberately in-memory corruption states, not claimed reachable via a legitimate write API. No assertion was weakened after a failure; the own suite passed on its first execution.

All10180 observed source files (10179 tracked source/evidence files plus the own test),89 installed distribution name/version records and the Python executable SHA remained identical across the test interval. pipcheck returned0 before and after. These package records do not hash every installed byte. The43 author primary files and their declared manifest/source hashes were independently authenticated before the run.

Scope: focal SQLite/SQL/HTTP acceptance only. The fixture uses its existing metadata-created SQLite schema; this is not migration, PostgreSQL, browser, VM, external-provider, production or full-suite acceptance. Positive HTTP requests in own cases discard fixture bearers and use actual password and factor endpoints. No product file was changed in this review worktree. Raw JUnit/stdout/stderr remain private; the public case projection contains only IDs and outcomes.
'''
(OUT/'review.md').write_bytes(review.encode('utf8'))
source={'source_head':head,'parent':base,'verdict':'PASS_FOCAL_INDEPENDENT',
    'changed_paths':changed,'same_author_case_ids':14,'independent_case_ids':27,'cases':41,
    'author_manifest_sha256':sha((author/'manifest.json').read_bytes()),
    'author_source_sha256':sha((author/'source.json').read_bytes()),
    'own_test_sha256':sha((ROOT/'tests/test_security_terminal_sv_peer.py').read_bytes()),
    'scope':'Independent focal SQLite HTTP/SQL review only; no full-suite, migration, PG, browser, VM or production acceptance.'}
(OUT/'source.json').write_bytes((json.dumps(source,indent=2)+'\n').encode())
tree=ast.parse(Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<maintained-public-scanner>','exec'))
for p in OUT.rglob('*'):
    if p.is_file():scan(p.read_bytes(),p.relative_to(OUT).as_posix())
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in {'.gitattributes','manifest.json'}}
(OUT/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
paths=[p.relative_to(ROOT).as_posix() for p in sorted(OUT.rglob('*')) if p.is_file()]
subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*paths],cwd=ROOT,check=True,capture_output=True)
for path in paths:assert git('show',':'+path)==(ROOT/path).read_bytes(),path
subprocess.run(['git','commit','-m','Record independent terminal-session MFA security review'],cwd=ROOT,check=True,capture_output=True)
print(json.dumps({'commit':git('rev-parse','HEAD').decode().strip(),'files':len(paths),
    'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'source_sha256':sha((OUT/'source.json').read_bytes())}))
