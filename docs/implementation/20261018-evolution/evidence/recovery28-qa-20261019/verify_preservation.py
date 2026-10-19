"""Independent structural preservation audit; no historical source is edited."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(r'F:\MetodoBaseWeb-recovery-compose-20261019')
OUT=Path(__file__).resolve().parent
BASE='5c9e097'


def frozen(path):
    return subprocess.run(['git','show',BASE+':'+path],cwd=ROOT,capture_output=True,check=True).stdout.decode('utf8')


def node_dump(node):return ast.dump(node,include_attributes=False)


def functions(text):return {node.name:node for node in ast.parse(text).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}


def normalized(value):return value.replace('\r\n','\n')


proposal=json.loads((ROOT/'docs/implementation/20261018-evolution/evidence/backend-recovery-preservation-proof.json').read_text())
historical=[]
for path in proposal['historical_contracts_unchanged']:
    before=frozen(path);after=(ROOT/path).read_text(encoding='utf8')
    assert normalized(before)==normalized(after),path
    historical.append({'path':path,'current_sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'same_frozen_content':True})
assert len(historical)==28
changed={
    'tests/integration_personal_diary_migrations.py':'test_empty_and_populated26_upgrade_preserve_old_rows_and_repeat',
    'tests/integration_provider_subjects.py':'seed_legacy',
    'tests/integration_schema_migrations.py':'test_parallel_onboarding_uses_five_templates',
}
test_proofs=[]
for path,allowed in changed.items():
    old,new=functions(frozen(path)),functions((ROOT/path).read_text(encoding='utf8'))
    assert set(old)==set(new)
    actual=[name for name in old if node_dump(old[name])!=node_dump(new[name])]
    assert actual==[allowed],(path,actual)
    old_asserts=[node_dump(node) for node in ast.walk(old[allowed]) if isinstance(node,ast.Assert)]
    new_asserts=[node_dump(node) for node in ast.walk(new[allowed]) if isinstance(node,ast.Assert)]
    assert old_asserts==new_asserts
    if path.endswith('integration_personal_diary_migrations.py'):
        class RemoveExplicitTarget(ast.NodeTransformer):
            def visit_Call(self,node):
                self.generic_visit(node)
                if isinstance(node.func,ast.Name) and node.func.id=='verify_runtime_schema':
                    node.keywords=[key for key in node.keywords if not (key.arg=='expected_revision' and isinstance(key.value,ast.Name) and key.value.id=='REVISION')]
                return node
        assert node_dump(old[allowed])==node_dump(RemoveExplicitTarget().visit(copy.deepcopy(new[allowed])))
    test_proofs.append({'path':path,'only_changed_function':allowed,'assertions_identical':True,'assertions':len(old_asserts)})
email_path='web/services/email_service.py'
old_email,new_email=functions(frozen(email_path)),functions((ROOT/email_path).read_text(encoding='utf8'))
assert all(node_dump(node)==node_dump(new_email[name]) for name,node in old_email.items())
scripts=[]
for path in ['web/templates/login_gym.html','web/templates/login_usuario.html']:
    before=re.findall(r'<script\b[^>]*>.*?</script>',frozen(path),flags=re.S|re.I)
    after=re.findall(r'<script\b[^>]*>.*?</script>',(ROOT/path).read_text(encoding='utf8'),flags=re.S|re.I)
    assert before==after,path
    scripts.append({'path':path,'scripts_unchanged':True,'blocks':len(before)})
restore_path='tests/integration_diary_restore_review.py'
assert normalized(frozen(restore_path))==normalized((ROOT/restore_path).read_text(encoding='utf8'))
proof={'base_commit':BASE,'frozen_historical_contracts':historical,'three_allowed_test_deltas':test_proofs,
       'old_email_functions_unchanged':sorted(old_email),'login_scripts':scripts,
       'restore27_entire_source_unchanged':True,'restore27_current_sha256':hashlib.sha256((ROOT/restore_path).read_bytes()).hexdigest(),
       'scope':'Independent AST/assertion and exact historical SQL/target comparisons; semantic seed equivalence4 remains separately attributed author evidence.'}
with (OUT/'recovery28-qa-independent-preservation.json').open('x',encoding='utf8') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
print(json.dumps({'historical_contracts':28,'allowed_test_deltas':3,'old_email_functions':len(old_email),'restore27_unchanged':True}))
