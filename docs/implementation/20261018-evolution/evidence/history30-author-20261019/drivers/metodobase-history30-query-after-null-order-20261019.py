"""Same query criteria after explicit matching id NULL order; no planner knobs."""
from pathlib import Path
import json
import sys

root=Path('F:/mb-hidx-20261019')
sys.path.insert(0,str(root))
from web.database.alembic.history_index_contract_v1 import expected_history_index
target=root/'web/database/alembic/schema_targets/20261019_personal_history_index_postgresql.json'
data=json.loads(target.read_bytes())
assert data['history_order_index']['indoption']==[0,0,1,3]
data['history_order_index']=expected_history_index('postgresql')
target.write_bytes((json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode())
original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history30-query-diagnostic-20261019.py')
source=original.read_text(encoding='utf-8')
source=source.replace("OUT=TEMP/'metodobase-history30-query-diagnostic-20261019'", "OUT=TEMP/'metodobase-history30-query-after-null-order-20261019'")
# The small diagnostic runner transforms its original runner text; change its
# replacement destination too, without changing criteria or subprocess args.
source=source.replace("\"OUT=TEMP/'metodobase-history30-query-diagnostic-20261019'\"", "\"OUT=TEMP/'metodobase-history30-query-after-null-order-20261019'\"")
exec(compile(source,str(original)+'::same-criterion-null-order-fix','exec'),globals())
