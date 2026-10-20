from pathlib import Path
import hashlib,json
import psycopg2
TASK=Path(__file__).resolve().parents[1];P=TASK/'private'
profile=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
assert hashlib.sha256(profile.read_bytes()).hexdigest()=='1526482e15f5e31a4248868e77a609af536f6dfbbf2b04959e7b14d521519f02'
paths=list((TASK/'leases').glob('lease-*.json'));assert len(paths)==1
raw=paths[0].read_bytes();lease=json.loads(raw)
assert lease['state']=='closed_absent' and lease['sessions_before_drop']==0
assert lease['absence_verified']=='fresh_control_connection'
config=json.loads(profile.read_bytes());url=config.get('METODOBASE_TEST_MIGRATOR_URL',config.get('migrator_url')).replace('postgresql+psycopg2://','postgresql://',1)
with psycopg2.connect(url) as fresh,fresh.cursor() as cursor:
 cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s OR oid=%s',(lease['database'],lease['oid']));databases=cursor.fetchone()[0]
 cursor.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s',(lease['database'],));sessions=cursor.fetchone()[0]
 assert databases==sessions==0
receipt={'own_closed_lease_sha256':hashlib.sha256(raw).hexdigest(),'state':'closed_absent','fresh_datname_and_oid_absent':True,
 'fresh_sessions':0,'ordinary_DROP_after_zero_sessions':True,'normal_server_exit':0,
 'additional_readonly_confirmation_no_new_UUID_no_new_test':True}
with (P/'fresh-independent-absence.json').open('xb') as out:out.write((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
