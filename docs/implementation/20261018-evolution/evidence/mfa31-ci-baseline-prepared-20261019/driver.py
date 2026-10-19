from pathlib import Path,PurePosixPath
import ast,hashlib,json,re,subprocess
root=Path(r'F:\MetodoBaseWeb-execution-20261018');dest=root/'docs/implementation/20261018-evolution/evidence/mfa31-ci-baseline-prepared-20261019';revision='eea8f773fba9b7f92241958139fcefa23b9ee1d4'
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse',revision+'^{commit}').decode().strip()==revision
workflow=git('show',revision+':.github/workflows/ci.yml');verifier=git('show',revision+':tests/verify_history_index_ci.py')
tree=ast.parse(verifier);assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_CURRENT_GATES' for t in n.targets));pins=ast.literal_eval(assignment.value);assert len(pins)==22
helpers={}
for name,digest in {**pins,'tests/verify_history_index_ci.py':hashlib.sha256(verifier).hexdigest()}.items():
    blob=git('show',revision+':'+name);assert hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()==digest,name
    helpers[name]={'Git_sha256':hashlib.sha256(blob).hexdigest(),'normalized_sha256':digest}
listing=git('ls-tree','-r','-z','--long',revision);rows={};seen=set()
for entry in listing[:-1].split(b'\0'):
    meta,separator,raw=entry.partition(b'\t');assert separator
    match=re.fullmatch(rb'(100644|100755) blob ([0-9a-f]{40}) +([0-9]+)',meta);assert match
    name=raw.decode();path=PurePosixPath(name);assert name==path.as_posix() and not path.is_absolute() and '..' not in path.parts and '\\' not in name and ':' not in name
    assert name.casefold() not in seen;seen.add(name.casefold());rows[name]={'mode':match[1].decode(),'object_id':match[2].decode(),'bytes':int(match[3])}
dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
(dest/'ci30-before.yml').write_bytes(workflow)
(dest/'tree-index.json').write_bytes((json.dumps(rows,indent=2)+'\n').encode())
contract={'status':'Prepared design/trust boundary only; no new CI runner, workflow mutation, service, archive extraction or gate execution','historical30_commit':revision,'tree':git('rev-parse',revision+'^{tree}').decode().strip(),'historical30_workflow_sha256':hashlib.sha256(workflow).hexdigest(),'tree_files':len(rows),'tree_regular_bytes':sum(row['bytes'] for row in rows.values()),'helpers_preserved':helpers,'model_physical_contracts':{'historical30':{'model_tables':29,'actual_tables':30,'revision':'20261019_personal_history_index'},'new31':{'model_tables':32,'actual_tables':33,'revision':'20261019_mfa','index30':'same exact physical index; targets22–30 immutable'}},'required_next':[
'New runner materializes authentic ancestor eea8 with actual Git tree/object/mode/size/byte verification and no replace/export attribute trust. Preserve original runners28/29 and helpers unchanged; no invented old metadata from current31models.',
'Historical CI30 wiring/29reports/33workflowcanaries/55+24+12parsercanaries/27inert/23VM contracts must run with exact source30. New31 current migrations5PG/services12PG/restore1 have separate reports with exact full testcase identities, no skips/errors/duplicates/substitutions.',
'Current31 must also execute adapted meaningful R12/R24/followup/export/worker/RLS/restore contracts with true31schema. Historical30 execution alone is insufficient for current integration.',
'Fresh current31 browser fixtures prove actual33physical/32model/revision31/nonowner/FORCERLS/index30; do not merely relabel30fixtures or replace selected cases. Preserve session/UI and real MFA enrollment/challenge/recovery/stepup, no env bypass.',
'Current image startup/readiness requires true31 schema; earlier image scripts run archived30 source only where explicitly historical. No Linux/image/browser/Actions acceptance from static workflow proof.',
'Retain broad serial/cov and n2shuffle tests; changes needed for intentional privileged MFA behavior must use legitimate enrollment/grants while preserving original business assertions and before/after scope. No primary-only bypass for tests.',
'Owned Bash fixtures/finalizers/sourceguards and upload allowlists tested with missing/stale/bad reports and failures. Secrets, OTP seeds, recovery/grants/CSRF, provider bodies, private config and serverlogs remain private; artifact publication checks expanded compressed entries.'
],'scope':'Current MAIN product source remains frozen for running broad gate; this new untracked prefix reserves no new DDL and implements no CI or acceptance.'}
(dest/'contract.json').write_bytes((json.dumps(contract,indent=2)+'\n').encode());(dest/'driver.py').write_bytes(Path(__file__).read_bytes())
manifest={'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dest.rglob('*')) if p.is_file()}}
(dest/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode());print(json.dumps({'manifest_sha256':hashlib.sha256((dest/'manifest.json').read_bytes()).hexdigest(),'historical_source':revision,'files':len(rows),'helpers':len(helpers),'regular_bytes':contract['tree_regular_bytes'],'scope':contract['status']}))
