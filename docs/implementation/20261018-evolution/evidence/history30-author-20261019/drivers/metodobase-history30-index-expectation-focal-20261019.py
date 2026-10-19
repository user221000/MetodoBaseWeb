"""Retarget the index assertion to revision30; keep readonly/limit/field checks."""
import ast
import hashlib
import json
from pathlib import Path

root=Path('F:/mb-hidx-20261019')
before=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-pagination-before-index-expectation-20261019.py')
after=root/'tests/test_personal_history_pagination.py'
text=after.read_text(encoding='utf-8')
added="    assert not any('USE TEMP B-TREE FOR ORDER BY' in str(row) for row in explain), explain\n"
assert text.count(added)==1
restored=text.replace(added,'').replace("assert any('ix_planes_gym_cliente_history' in str(row) for row in explain), explain", "assert any('ix_planes_gym_fecha' in str(row) for row in explain), explain")
assert ast.dump(ast.parse(restored),include_attributes=False)==ast.dump(ast.parse(before.read_text(encoding='utf-8')),include_attributes=False)
receipt={'before_sha256':hashlib.sha256(before.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(after.read_bytes()).hexdigest(),'only_AST_delta':'One expected index name changed to revision30 plus stricter no temporary ORDER BY B-tree assertion. All existing readonly,limit+1,no COUNT/JSON,HTTP/headers and other assertions unchanged.'}
path=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-index-expectation-proof-20261019.json')
assert not path.exists();path.write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-final-base-test-20261019.py')
source=original.read_text(encoding='utf-8')
start=source.index('directory=ROOT/');end=source.index('paths=subprocess.check_output',start)
source=source[:start]+source[end:]
source=source.replace("OUT=TEMP/'metodobase-history30-final-base-test-20261019'", "OUT=TEMP/'metodobase-history30-index-expectation-focal-20261019'")
needle="'tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py',"
assert source.count(needle)==1
source=source.replace(needle,"'tests/test_personal_history_pagination.py','-k','query_is_readonly_limit_plus_one',")
exec(compile(source,str(original)+'::two-old-index-expectations','exec'),globals())
