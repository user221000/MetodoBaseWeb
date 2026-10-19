from pathlib import Path
import hashlib,json,re,shutil
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');root=Path(r'F:\MetodoBaseWeb-execution-20261018');dest=root/'docs/implementation/20261018-evolution/evidence/mfa31-composition-prepared-20261019'
def sensitive(blob):
    for m in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=m.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob))
dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n')
for folder in ['metodobase-mfa31-compose-prepare-20261019','metodobase-mfa31-composed-header-check-20261019','metodobase-mfa31-header-probe-causality-20261019','metodobase-mfa31-header-own-replay-20261019','metodobase-mfa31-header-own-v3-20261019']:
    for path in (tmp/folder).rglob('*'):
        if not path.is_file():continue
        blob=path.read_bytes();assert not sensitive(blob),path
        target=dest/folder/path.relative_to(tmp/folder);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
names=['metodobase-mfa31-compose-prepare.py','metodobase-mfa31-composed-header-check.py','metodobase-mfa31-header-probe-refine.py','metodobase-mfa31-header-own-replay.py','metodobase-mfa31-header-v3-prepare.py','metodobase-mfa31-header-own-v3.py','metodobase-mfa31-header-v3-causality.json','test_metodobase_mfa_diary_composed_headers.py','test_metodobase_mfa_diary_composed_headers_v2.py','test_metodobase_mfa_diary_composed_headers_v3.py',Path(__file__).name]
for name in names:
    blob=(tmp/name).read_bytes();assert not sensitive(blob),name;(dest/name).write_bytes(blob)
record={'composition':'46dc908dd82edaa369f4d095df5abe7703a60de1','base_MAIN30':'eea8f773fba9b7f92241958139fcefa23b9ee1d4','incoming31':'56e810b3a0518231ba013cab29d68ee0aba0bacd','only_manual_resolution':'security_headers.py; both parent policies retained','first102':'94maintained passed and7own passed;1additional history test had an incorrect fixture assumption reproduced in both parents','second8':'7own passed,1exact cache literal mismatch with default API max-age0; actual history handler setsno-store explicitly','final8':'8own pass with10original assert ASTs unchanged and fixture matching actual history handler; no product change','source_full_guard_first':'9777tracked/89packages unchanged','final_guard':'middleware/isolation/runner+89packages unchanged','inert_hash_guard':'Initial causality script had an inert conditional assertion; separate real digest and AST assertions in own replay/v3 verify original and refined source. Preserved, not used as evidence of validation.','scope':'Isolated preparation, not a fresh102pass, not full MFA or MAIN acceptance. No services/PG/browser/provider/dependency changes; alias/header refinements/full QA/security/UI/CI31 remain pending.'}
(dest/'summary.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
manifest={'files':{p.relative_to(dest).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(dest.rglob('*')) if p.is_file()}}
(dest/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode());print(json.dumps({'manifest_sha256':hashlib.sha256((dest/'manifest.json').read_bytes()).hexdigest(),'files':len(manifest['files'])+1,'scope':'Untracked safe prefix only; MAIN tracked source remains frozen for running broad gate.'}))
