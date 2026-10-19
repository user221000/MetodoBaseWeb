from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-r05-classifier-peer-private-20261019'
R=Path(r'F:/mb-security-r05-classifier-peer-20261019');PREFIX='docs/implementation/20261018-evolution/evidence/security-r05-registry-independent-20261019';O=R/PREFIX
BASE='f7b12a71a89de2e35b0035ccef147a673ad50d29';sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('diff','--name-only') and not git('diff','--cached','--name-only')
(O/'drivers/freeze.py').write_bytes(Path(__file__).read_bytes())
for path in sorted(O.rglob('*')):
    if path.is_file():git('-c','core.autocrlf=false','add','-f','--',path.relative_to(R).as_posix())
cmd=['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check']
with (P/'git-whitespace-check.raw.log').open('wb') as log:check=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT)
assert check.returncode==0
save('freeze-validation.json',{'only_evidence_prefix_staged':True,'index_and_HEAD_RAW_verified':True,'git_whitespace_check_argv':cmd,'git_whitespace_exit':0,'raw_CRLF_not_normalized':True,'private_check_output_sha256':sha((P/'git-whitespace-check.raw.log').read_bytes())})
save('manifest.json',{p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='manifest.json'})
for name in ['freeze-validation.json','manifest.json']:git('-c','core.autocrlf=false','add','-f','--',PREFIX+'/'+name)
names=git('diff','--cached','--name-only','-z').decode().split('\0')[:-1];assert names and all(n.startswith(PREFIX+'/') for n in names)
node=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
assert sha(ast.dump(node).encode())=='de7b3ab300984a2e66686fea8e81b3cf1b48d9b2a055ab9f9fd620007d55cf3f'
ns=dict(io=io,json=json,re=re,tarfile=tarfile,zipfile=zipfile,PurePosixPath=PurePosixPath);exec(compile(ast.Module(body=[node],type_ignores=[]),'unchanged-checkpoint119','exec'),ns)
for name in names:
    payload=(R/name).read_bytes();assert git('show',':'+name)==payload;ns['scan'](payload,name)
git('commit','-m','docs: seal independent finite scanner registry review')
head=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==BASE
changed=git('diff-tree','--no-commit-id','--name-only','-r','-z',head).decode().split('\0')[:-1];assert set(changed)==set(names)
for name in changed:assert git('show',head+':'+name)==(R/name).read_bytes()
assert not git('status','--porcelain','--untracked-files=no')
receipt={'commit':head,'reviewed_commit':BASE,'proof_files':len(changed),'source_sha256':sha((O/'source.json').read_bytes()),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'scanner119':'PASS','index_and_HEAD_RAW_exact':True,'tracked_worktree_clean':True,'only_evidence_prefix_changed':True,'verdict':'focal_acceptance_no_global_R05'}
(T/'metodobase-sec-r05-classifier-peer-freeze-receipt-20261019.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
