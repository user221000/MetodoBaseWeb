"""Read-only post-error resource check; never remove unattributed resources."""
import json
from pathlib import Path
import psycopg2
configuration=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as db,db.cursor() as cursor:
    cursor.execute("SELECT datname FROM pg_database WHERE datname LIKE 'metodobase_test_backup_%' OR datname LIKE 'metodobase_test_restore_%' ORDER BY datname")
    names=[row[0] for row in cursor.fetchall()]
result={'matching_backup_or_restore_databases_remaining':names,'count':len(names),'scope':'Read-only stronger namespace absence check after historical fixture setup error; no exact UUID witness was emitted before its missing evidence-dir failure. No resource deletion or other-database mutation.'}
Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore-v2-20261019/resource-check-after.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({'remaining_backup_restore_count':len(names),'read_only':True}))
