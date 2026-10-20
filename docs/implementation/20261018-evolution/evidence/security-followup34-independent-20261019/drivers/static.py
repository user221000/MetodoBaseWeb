from pathlib import Path
import ast,hashlib,json,re,subprocess
R=Path(r'F:/mb-security-google33-conflict-peer-20261019')
O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-independent-20261019'
BASE='80b9a44adf4daae160673b4d86a58cb06f809071';COMMON='3587b3b3eee3a58367624472d7c0683baa8f10e0'
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=R)
sha=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(O/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==BASE
stem='web/database/alembic/schema_targets'
old=[n for n in git('ls-tree','-r','--name-only','-z',COMMON,'--',stem).decode().split('\0') if n]
assert len(old)==26
assert all(git('show',COMMON+':'+n)==(R/n).read_bytes() for n in old)
changed=[n for n in git('diff','--name-only',COMMON,BASE,'--',stem).decode().splitlines()]
assert changed==[stem+'/20261019_followup_tasks_sqlite.json']
assert not (R/stem/'20261019_followup_tasks_postgresql.json').exists()
receipt=json.loads((R/'docs/implementation/20261018-evolution/evidence/backend-followup34-author-20261019/restore33-preservation.json').read_bytes())
original=(R/'tests/integration_google33_restore.py').read_bytes();new=(R/'tests/integration_followup34_restore.py').read_bytes()
assert original==git('show',COMMON+':tests/integration_google33_restore.py')
oldtext=original.decode().replace('\r\n','\n');newtext=new.decode().replace('\r\n','\n')
pattern=r'(?m)^[ \t]*# BEGIN FOLLOWUP34 WITNESS\n[\s\S]*?^[ \t]*# END FOLLOWUP34 WITNESS\n'
assert len(re.findall(pattern,newtext))==4
inverse=re.sub(pattern,'',newtext)
for before,after in receipt['declared_changes']:
    assert before in inverse
    inverse=inverse.replace(before,after)
assert inverse==oldtext and ast.dump(ast.parse(inverse))==ast.dump(ast.parse(oldtext))
assert sum(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(original)))==67
save('historical-and-restore-static-binding.json',{'old_target_files':len(old),'all26_byteexact_to_COMMON33':True,
    'only_new_target':changed,'PostgreSQL34_target_absent':True,'restore_original33_Git_blob_SHA256':sha(original),
    'restore34_checkout_SHA256':sha(new),'extension_blocks':4,'original_assertions':67,
    'full_inverse_LF_source_exact':True,'full_inverse_AST_exact':True,
    'scope':'Static preservation only; restore34 PostgreSQL has not run.'})
policy=(R/'web/database/followup_policy.py').read_bytes();tree=ast.parse(policy)
closed={name:[] for name in ['_source','_qualifies','_immutable','_transition','_projection']}
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in closed:
        assert all(isinstance(a,ast.Constant) and isinstance(a.value,str) for a in node.args)
        closed[node.func.id].append([a.value for a in node.args])
schema=ast.parse((R/'web/database/followup_schema_v1.py').read_bytes())
snapshot=next(n.value for n in schema.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='SNAPSHOT')
columns=ast.literal_eval(snapshot);assert len(columns)==22 and all(re.fullmatch('[a-z_]+',c) for c in columns)
save('DDL-trust-boundary-static.json',{'policy_RAW_SHA256':sha(policy),'closed_operator_call_arguments':closed,
    'SNAPSHOT_literal_column_names':columns,'no_request_imports_in_policy':True,
    'analysis':'Seven reported B608 MEDIUM/LOW diagnostics correspond to invoker-trigger/RLS DDL assembled from fixed local helpers, operators, literal table names and the frozen SNAPSHOT tuple. HTTP data remains ORM-bound; no request string feeds these DDL fragments. No Bandit suppression or baseline change made.',
    'PG_counts_runtime_unproved':{'anticipated_FORCE':28,'anticipated_functions':29,'anticipated_triggers':15},
    'GUC_not_authenticated_actor_signature':True,'SECURITY_INVOKER_not_definer':True})
save('pending-PG-peer-plan.json',{'executed':False,'PostgreSQL_profile_read':False,'lease_owner_now':'QA33, then author34 before peer',
    'requires':'New explicit handoff, later frozen PostgreSQL34 target, own UUID exclusive receipt before CREATE, OID/birth, restricted app4false/nonowner/FORCE/pool1; zero sessions/DROPnormal/fresh absence at close.',
    'prepared_own_cases':['Unassigned NutriB cannot distinguish foreign task assignedC through a held UsuarioC lock versus missing task; both404 expected.',
        'Held Cliente row must abort as NOWAIT409, not become statement-timeout503; statement_timeout changed/restored only on own pool1 connection.'],
    'status':'Static hypotheses pending actual PG; no confirmed data or authorization bypass claimed.',
    'prepared_file':'prepared/test_security_followup34_postgres_peer.prepared.py',
    'author22PG_not_attributed_to_peer':True})
print(json.dumps({'old_targets_byteexact':26,'restore_inverse_asserts':67,'DDL_closed_inputs':True,'PG_executed':False}))
