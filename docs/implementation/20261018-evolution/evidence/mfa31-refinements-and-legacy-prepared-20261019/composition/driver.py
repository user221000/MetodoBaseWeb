from pathlib import Path
import ast,hashlib,json,subprocess
root=Path(r'F:\mb-mfa31-compose-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-compose-refinements-20261019');out.mkdir(exist_ok=False)
base='46dc908dd82edaa369f4d095df5abe7703a60de1';incoming='440e7c78d3cb7e1f9734ac9e08141c2d7f5556ae';ui='dbce653';name='web/middleware/security_headers.py'
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
ours=git('show',base+':'+name);resolved=git('show',ui+':'+name)
class RemovePrimary(ast.NodeTransformer):
    def visit_Assign(self,node):
        if any(isinstance(t,ast.Name) and t.id in {'primary_api','_PRIMARY_API_PATHS'} for t in node.targets):return None
        return self.generic_visit(node)
    def visit_BoolOp(self,node):
        node=self.generic_visit(node)
        def primary(value):return (isinstance(value,ast.Name) and value.id=='primary_api') or (isinstance(value,ast.UnaryOp) and isinstance(value.op,ast.Not) and isinstance(value.operand,ast.Name) and value.operand.id=='primary_api')
        node.values=[value for value in node.values if not primary(value)]
        return node.values[0] if len(node.values)==1 else node
inverse=RemovePrimary().visit(ast.parse(resolved));assert ast.dump(inverse,include_attributes=False)==ast.dump(ast.parse(ours),include_attributes=False)
constant=lambda blob:next(n.value for n in ast.parse(blob).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_PRIMARY_API_PATHS' for t in n.targets))
assert ast.dump(constant(resolved),include_attributes=False)==ast.dump(constant(git('show',incoming+':'+name)),include_attributes=False)
preview=subprocess.run(['git','merge-tree','--write-tree','--messages',base,incoming],cwd=root,capture_output=True);(out/'preview.stdout.log').write_bytes(preview.stdout);(out/'preview.stderr.log').write_bytes(preview.stderr);assert preview.returncode==1
expected=preview.stdout.decode().splitlines()[0]
result=subprocess.run(['git','merge','--no-commit','--no-ff',incoming],cwd=root,capture_output=True);(out/'merge.stdout.log').write_bytes(result.stdout);(out/'merge.stderr.log').write_bytes(result.stderr);assert result.returncode==1
assert git('diff','--name-only','--diff-filter=U','-z').decode().split('\0')[:-1]==[name]
(out/'ours.py.raw').write_bytes(ours);(out/'primary-union-frontend.py.raw').write_bytes(resolved);(out/'conflicted.py.raw').write_bytes((root/name).read_bytes())
(root/name).write_bytes(resolved);subprocess.run(['git','add','--',name],cwd=root,check=True,capture_output=True)
tree=git('write-tree').decode().strip();assert git('diff','--name-only','-z',expected,tree).decode().split('\0')[:-1]==[name]
for path in ['api/routes/pagos.py','web/services/mfa_service.py','web/services/mfa_actions.py','web/database/schema_control.py']:
    assert git('show',':'+path)==git('show',incoming+':'+path),path
for path in sorted((root/'web/database/alembic/schema_targets').glob('*.json')):
    relative=path.relative_to(root).as_posix();assert git('show',':'+relative)==git('show',base+':'+relative)
sources=[n for n in git('diff','--cached','--name-only','-z').decode().split('\0')[:-1] if not n.startswith('docs/')]
subprocess.run(['git','diff','--cached','--check','--',*sources],cwd=root,check=True,capture_output=True)
result=subprocess.run(['git','commit','-m','Compose isolated MFA alias, primary privacy and canonical actor refinements'],cwd=root,capture_output=True);(out/'commit.stdout.log').write_bytes(result.stdout);(out/'commit.stderr.log').write_bytes(result.stderr);assert result.returncode==0
assert not git('status','--porcelain','--untracked-files=no')
receipt={'before':base,'incoming':incoming,'head':git('rev-parse','HEAD').decode().strip(),'source_header_sha256':hashlib.sha256(resolved).hexdigest(),'sole_manual_conflict':name,'resolution_from_frontend':git('rev-parse',ui).decode().strip(),'primary_constant_exact_incoming':True,'inverse_AST_removes_only_primary_equals_accepted_diary_MFA':True,'other_files_exact_automatic_merge':True,'critical3sources_Git_exact_incoming':True,'all_schema_targets_preserved':True,'scope':'Isolated composition, not MAIN acceptance. No tests/services/PG/browser run by this driver. Full peer review, UI/QA/CI31 still pending; prior94+8 belonged to46dc before this primary policy change.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
