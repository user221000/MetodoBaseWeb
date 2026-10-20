from pathlib import Path
import ast,hashlib,json
R=Path(r'F:/mb-security-google33-peer-20261019');P=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-google33-peer-private-20261019');O=R/'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
path=R/'tests/test_security_google33_postgres_peer.py';before=path.read_bytes();assert before.count(b'Session(engine)')==4
with (P/'initial-race-autoflush-true.RAW.py').open('xb') as f:f.write(before)
after=before.replace(b'Session(engine)',b'Session(engine, autoflush=False)')
def assertions(raw):
    return {node.name:[ast.dump(n) for n in ast.walk(node) if isinstance(n,ast.Assert)] for node in ast.parse(raw).body if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}
assert assertions(before)==assertions(after)
path.write_bytes(after)
sha=lambda b:hashlib.sha256(b).hexdigest()
(O/'race-session-normalization.json').write_bytes((json.dumps({'before_sha256':sha(before),'after_sha256':sha(after),'original_source_retained_private':True,'changes':'Exactly four own race Session constructors explicitly set autoflush=False, matching engine.py:121. Original assertions are unchanged.','all_test_assertions_AST_exact':True,'initial_True_results_preserved':'Two real IntegrityError failures remain evidence of the generic-service robustness counterfactual; not reclassified as a signature/auth/DB exploit.','production_source_changed':False},indent=2)+'\n').encode())
print(json.dumps({'constructors_changed':4,'assertions_changed':False,'before_sha256':sha(before),'after_sha256':sha(after)}))
