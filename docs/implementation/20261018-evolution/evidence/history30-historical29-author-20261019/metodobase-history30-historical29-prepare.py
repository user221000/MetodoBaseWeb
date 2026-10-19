"""Pin only explicit historical29 runtime checks; retain default-head rejection."""
import ast,hashlib,json
from pathlib import Path
root=Path(r'F:\mb-r12-history30-20261019');path=root/'tests/integration_client_link_migrations.py'
before=path.read_bytes().replace(b'\r\n',b'\n');snapshot=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-history30-historical29-before-20261019/original.py').read_bytes().replace(b'\r\n',b'\n');assert before==snapshot
direct=b'    verify_runtime_schema(engine)\n';assert before.count(direct)==2
guard=b"with pytest.raises(RuntimeError,match='guards'):verify_runtime_schema(engine)";assert before.count(guard)==1
after=before.replace(direct,b'    verify_runtime_schema(engine,expected_revision=REVISION)\n').replace(guard,b"with pytest.raises(RuntimeError,match='guards'):verify_runtime_schema(engine,expected_revision=REVISION)")
old_rejection=b"with pytest.raises(RuntimeError,match='revision'):verify_runtime_schema(engine)";assert before.count(old_rejection)==after.count(old_rejection)==1
tree=ast.parse(after);count=0
for call in ast.walk(tree):
    if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='verify_runtime_schema':
        additions=[item for item in call.keywords if item.arg=='expected_revision' and isinstance(item.value,ast.Name) and item.value.id=='REVISION']
        if additions:call.keywords=[item for item in call.keywords if item not in additions];count+=len(additions)
assert count==3 and ast.dump(tree,include_attributes=False)==ast.dump(ast.parse(before),include_attributes=False)
path.write_bytes(after)
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-history30-historical29-target-proof-20261019.json');assert not out.exists()
out.write_text(json.dumps({'before_LF_sha256':hashlib.sha256(before).hexdigest(),'after_LF_sha256':hashlib.sha256(after).hexdigest(),'only_AST_delta':'Three expected_revision=REVISION29 keywords on post29 positive/guard checks','AST_inverse_exact':True,'default28_rejection_byte_exact':True,'original_targets_and_criteria_unchanged':True},indent=2)+'\n',encoding='utf8')
print(json.dumps({'AST_inverse_exact':True,'only_keywords_added':3,'default28_rejection_preserved':True}))
