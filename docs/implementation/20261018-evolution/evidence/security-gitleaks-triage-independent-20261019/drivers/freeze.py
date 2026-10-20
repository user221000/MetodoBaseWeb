from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-gitleaks-peer-private-20261019'
R=Path(r'F:/mb-security-gitleaks-triage-peer-20261019');PREFIX='docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019';O=R/PREFIX
BASE='de216543a2eec05584168cdb888f627901b0e0b1';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('diff','--name-only') and not git('diff','--cached','--name-only')
(O/'drivers/freeze.py').write_bytes(Path(__file__).read_bytes())
for path in sorted(O.rglob('*')):
    if path.is_file():git('-c','core.autocrlf=false','add','-f','--',path.relative_to(R).as_posix())
check_cmd=['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check']
with (P/'git-whitespace-check.raw.log').open('wb') as log:check=subprocess.run(check_cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT)
assert check.returncode==0
save('freeze-validation.json',{'index_RAW_bytes_verified':True,'only_evidence_prefix_staged':True,'git_whitespace_check':{'argv':check_cmd,'exit':check.returncode,'CR_at_EOL_allowed_without_changing_RAW':True,'private_log_sha256':sha((P/'git-whitespace-check.raw.log').read_bytes())},'source_and_manifest_content_digests_do_not_include_commit_ID':True})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='manifest.json'})
for name in ['freeze-validation.json','manifest.json']:git('-c','core.autocrlf=false','add','-f','--',PREFIX+'/'+name)
staged=git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]
assert staged and all(name.startswith(PREFIX+'/') for name in staged)
for name in staged:assert git('show',':'+name)==(R/name).read_bytes()
node=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
assert sha(ast.dump(node).encode())=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath)
exec(compile(ast.Module(body=[node],type_ignores=[]),'unchanged-checkpoint119','exec'),ns)
for name in staged:ns['scan']((R/name).read_bytes(),name)
result=git('commit','-m','docs: seal independent fixed-report secret triage')
head=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==BASE
changed=git('diff-tree','--no-commit-id','--name-only','-r','-z',head).decode().split('\0')[:-1]
assert set(changed)==set(staged) and not git('status','--porcelain','--untracked-files=no')
for name in changed:assert git('show',head+':'+name)==(R/name).read_bytes()
receipt={'commit':head,'base':BASE,'proof_files':len(changed),'source_sha256':sha((O/'source.json').read_bytes()),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'ledger_sha256':sha((O/'finite-reviewed-location-ledger.json').read_bytes()),'ledger_zip_sha256':sha((O/'finite-reviewed-location-ledger.zip').read_bytes()),'index_and_HEAD_RAW_exact':True,'tracked_worktree_clean':True,'only_evidence_prefix_changed':True,'scanner119':'PASS'}
(T/'metodobase-sec-gitleaks-peer-freeze-receipt-20261019.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
