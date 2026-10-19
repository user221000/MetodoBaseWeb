from pathlib import Path
import hashlib,json,subprocess
repo=Path(r'F:\MetodoBaseWeb-execution-20261018');root=Path(r'F:\mb-mfa31-compose-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-compose-prepare-20261019');out.mkdir(exist_ok=False)
base='eea8f773fba9b7f92241958139fcefa23b9ee1d4';incoming='56e810b3a0518231ba013cab29d68ee0aba0bacd';name='web/middleware/security_headers.py'
def run(cwd,*args):return subprocess.run(['git',*args],cwd=cwd,capture_output=True)
assert not root.exists()
result=run(repo,'worktree','add','-b','implementation/mfa31-compose-20261019',str(root),base);(out/'worktree.stdout.log').write_bytes(result.stdout);(out/'worktree.stderr.log').write_bytes(result.stderr);assert result.returncode==0
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
assert not git('status','--porcelain','--untracked-files=no')
preview=run(root,'merge-tree','--write-tree','--messages',base,incoming);(out/'preview.stdout.log').write_bytes(preview.stdout);(out/'preview.stderr.log').write_bytes(preview.stderr);assert preview.returncode==1
expected_tree=preview.stdout.decode().splitlines()[0]
result=run(root,'merge','--no-commit','--no-ff',incoming);(out/'merge.stdout.log').write_bytes(result.stdout);(out/'merge.stderr.log').write_bytes(result.stderr);assert result.returncode==1
conflicts=git('diff','--name-only','--diff-filter=U','-z').decode().split('\0')[:-1];assert conflicts==[name]
ours=git('show',':2:'+name);theirs=git('show',':3:'+name);ancestor=git('show',':1:'+name)
for label,blob in [('ours',ours),('theirs',theirs),('base',ancestor),('conflicted',(root/name).read_bytes())]:(out/(label+'.py.raw')).write_bytes(blob)
text=ours.decode();pairs=[
('                    and not diary_api):','                    and not diary_api\n                    and not request.url.path.startswith("/api/auth/mfa/")):'),
('if request.url.path in {"/auth/reset-password", "/auth/accept-client-link"}:','if request.url.path in {"/auth/reset-password", "/auth/accept-client-link"} or request.url.path.startswith("/api/auth/mfa/"):'),
('                or diary_api\n','                or diary_api\n                or request.url.path.startswith("/api/auth/mfa/")\n'),
('if is_member_link_private(request.url.path) or diary_api:','if is_member_link_private(request.url.path) or diary_api or request.url.path.startswith("/api/auth/mfa/"):')]
for before,after in pairs:assert text.count(before)==1,before;text=text.replace(before,after)
(root/name).write_bytes(text.encode());subprocess.run(['git','add','--',name],cwd=root,check=True,capture_output=True)
resolved_tree=git('write-tree').decode().strip();delta=git('diff','--name-only','-z',expected_tree,resolved_tree).decode().split('\0')[:-1];assert delta==[name]
tracked=git('diff','--cached','--name-only','-z').decode().split('\0')[:-1];sources=[n for n in tracked if not n.startswith('docs/')]
subprocess.run(['git','diff','--cached','--check','--',*sources],cwd=root,check=True,capture_output=True)
assert git('show',':web/database/schema_control.py')==git('show',incoming+':web/database/schema_control.py')
for p in sorted((repo/'web/database/alembic/schema_targets').glob('*.json')):
    relative=p.relative_to(repo).as_posix();assert git('show',':'+relative)==git('show',base+':'+relative),relative
c4='web/database/alembic/versions/c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py';assert git('show',':'+c4)==git('show',base+':'+c4)
result=run(root,'commit','-m','Compose isolated MFA31 candidate with accepted daily plan for integration review');(out/'commit.stdout.log').write_bytes(result.stdout);(out/'commit.stderr.log').write_bytes(result.stderr);assert result.returncode==0
head=git('rev-parse','HEAD').decode().strip();assert not git('status','--porcelain','--untracked-files=no')
receipt={'base':base,'incoming':incoming,'head':head,'root':str(root),'resolved_tree':resolved_tree,'sole_conflict':name,'resolution':'Ours accepted diary family plus all four MFA protection conditions exactly; root/slash semantics unchanged from each parent. Both privacy/fallback policies retained. Other files equal automatic merge-tree result.','resolved_source_Git_sha256':hashlib.sha256(git('show','HEAD:'+name)).hexdigest(),'source_changed_from_auto_merge':delta,'scope':'Isolated composition only, not accepted or integrated in MAIN. MFA alias refinement, full independent security/QA, UI/CI31 and composed regression remain pending. No services/PG/browser/dependency changes.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
