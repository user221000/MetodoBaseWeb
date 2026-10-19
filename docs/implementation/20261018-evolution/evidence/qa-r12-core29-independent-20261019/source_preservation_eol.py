"""RAW freeze, immutable historical contracts and narrow existing-model deltas."""
import ast
import copy
import zipfile
from qa_core_support import *

assert sha(RAW.read_bytes())=='a1ea7f6e011fa571354f2dc865d8689b039e186a7542720a64c664ebf96ecc8a'
freeze_name='docs/implementation/20261018-evolution/evidence/backend-r12-canonical29-freeze.json'
entries={}
with zipfile.ZipFile(RAW) as archive:
    rawfreeze=archive.read(freeze_name)
    assert sha(rawfreeze)=='72b2bce34fba31d74e24aaa2d06d910d47d0f27308855b9f75b689d367a7acc6'
    freeze=json.loads(rawfreeze)
    for name,digest in freeze['sources_after_tests_sha256'].items():
        raw=archive.read(name);assert sha(raw)==digest
        blob=git('show',HEAD+':'+name)
        current=(ROOT/name).read_bytes()
        assert raw.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n')==current.replace(b'\r\n',b'\n')
        entries[name]={'raw_sha256':digest,'git_sha256':sha(blob),'worktree_sha256':sha(current),
                       'only_possible_byte_difference':'CRLF versus LF; normalized contents identical'}
oldnames=git('ls-tree','-r','--name-only',BASE,'web/database/alembic/schema_targets').decode().splitlines()
assert oldnames
for name in oldnames:
    assert git('show',BASE+':'+name)==git('show',HEAD+':'+name)
    assert git('show',HEAD+':'+name).replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
historical=['web/database/alembic/schema_contract_v1.py','web/database/alembic/security_contract_v1.py',
            'web/database/tenant_policy.py','tests/integration_client_link_mechanics_postgres.py']
for name in historical:
    # Prototype is an evidence-era addition after product BASE; its own freeze is checked separately below.
    if name.endswith('mechanics_postgres.py'):continue
    assert git('show',BASE+':'+name)==git('show',HEAD+':'+name)
    assert git('show',HEAD+':'+name).replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
old=ast.parse(git('show',BASE+':web/database/models.py'))
current=ast.parse((ROOT/'web/database/models.py').read_bytes())
added={'ClientAccountLink','ClientLinkInvitation','ClientPlanPublication'}
restored=copy.deepcopy(current);restored.body=[node for node in restored.body if not isinstance(node,ast.ClassDef) or node.name not in added]
removed=[]
for node in ast.walk(restored):
    if isinstance(node,ast.Tuple):
        kept=[]
        for value in node.elts:
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Name) and value.func.id=='UniqueConstraint' and any(key.arg=='name' and isinstance(key.value,ast.Constant) and key.value.value in {'uq_client_account_owner','uq_member_plan_source_owner'} for key in value.keywords):
                removed.append(ast.dump(value))
            else:kept.append(value)
        node.elts=kept
assert len(removed)==2 and ast.dump(old)==ast.dump(restored)
old_tenant=ast.parse(git('show',BASE+':web/database/tenant_context.py'))
tenant=ast.parse((ROOT/'web/database/tenant_context.py').read_bytes())
begin=next(node for node in tenant.body if isinstance(node,ast.FunctionDef) and node.name=='_on_engine_begin')
clears=[node for node in begin.body if isinstance(node,ast.Expr) and 'app.client_invitation_digest' in ast.dump(node)]
assert len(clears)==1;begin.body.remove(clears[0]);assert ast.dump(tenant)==ast.dump(old_tenant)
contract=ROOT/'docs/implementation/20261018-evolution/evidence/backend-r12-contract-v2.md'
review=MAIN/'docs/implementation/20261018-evolution/evidence/r12-contract-security-review-20261019/source.json'
assert sha(contract.read_bytes().replace(b'\r\n',b'\n'))=='3c28ccd2b784cbc028492ad5cb0ea427d74c3f488c241e7f57a24ecb14ff7a03'
assert sha(review.read_bytes()).startswith('620a')
save('source-preservation.json',{'head':HEAD,'base':BASE,'raw_archive_sha256':sha(RAW.read_bytes()),
    'raw_freeze_sha256':sha(rawfreeze),'freeze23_normalized_against_git_and_owned_worktree':entries,
    'historical_schema_target_files_unchanged':oldnames,'historical_v1_and_tenant_policy_unchanged':historical[:3],
    'original_model_ast_exact_except_three_added_classes_and_two_unique_constraints':True,
    'original_tenant_context_ast_exact_except_one_digest_clear':True,'contract_worktree_raw_sha256':sha(contract.read_bytes()),'contract_authenticated_lf_sha256':sha(contract.read_bytes().replace(b'\r\n',b'\n')),
    'security_review_source_sha256':sha(review.read_bytes()),'scope':'No API/HTTP/restore/broad acceptance; no historical fixture retarget or product edits.'})
print(json.dumps({'raw_sources':len(entries),'historical_targets':len(oldnames),'model_and_hook_preserved':True}))
