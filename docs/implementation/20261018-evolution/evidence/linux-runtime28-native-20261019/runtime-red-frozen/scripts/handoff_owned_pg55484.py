"""Drop only attributed failed-attempt UUID objects, then hand off the owned instance."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
import psycopg2
from psycopg2 import sql

BASE=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
OUT=BASE/'closure'
pointer=json.loads((BASE/'pg55484-instance-pointer.json').read_text())
assert pointer['nonce']=='81f03803bc7748c683a4dac4f297b9c3' and pointer['postmaster_pid']==1216
admin=json.loads(Path(pointer['private_admin_file']).read_text())
assert admin['host']=='127.0.0.1' and admin['port']==55484
data=Path(pointer['data_directory'])
assert Path(admin['data_dir']).resolve()==data.resolve()
assert data.resolve().is_relative_to(Path(pointer['private_root']).resolve())
assert int((data/'postmaster.pid').read_text().splitlines()[0])==1216
expected=json.loads((BASE/'pg55484-setup/summary.json').read_text())['process_identity']
command='Get-CimInstance Win32_Process -Filter "ProcessId=1216" | Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress'
actual=json.loads(subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',command],creationflags=subprocess.CREATE_NO_WINDOW))
for key in ['ProcessId','ExecutablePath','CommandLine','CreationDate']:assert actual[key]==expected[key]
assert hashlib.sha256(Path(actual['ExecutablePath']).read_bytes()).hexdigest()==pointer['postgres_executable_sha256']
private=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-runtime28-roles-private-lwdcn5wd')
owned=json.loads((private/'ownership-journal.json').read_text())
nonce='a781deb39fd74441baa6a37c1a0cab40'
assert owned['nonce']==nonce and owned['port']==55484 and owned['host']=='127.0.0.1'
assert owned['database']=='metodobase_test_runtime28_'+nonce
roles=['mb28_m_'+nonce,'mb28_a_'+nonce]
assert set(owned['created_roles'])==set(roles)
hba=data/'pg_hba.conf';hba_hash=hashlib.sha256(hba.read_bytes()).hexdigest()
try:
    c=psycopg2.connect(host=admin['host'],port=admin['port'],dbname='postgres',user=admin['username'],password=admin['password'],connect_timeout=10,application_name='metodobase_runtime28_owned_handoff')
    c.autocommit=True
    with c.cursor() as q:
        q.execute('SHOW data_directory');assert Path(q.fetchone()[0]).resolve()==data.resolve()
        q.execute('SELECT current_user,inet_server_port(),version()');identity=q.fetchone()
        assert identity[0]==admin['username'] and identity[1]==55484 and 'PostgreSQL 17.11' in identity[2]
        q.execute('SELECT datname FROM pg_database ORDER BY datname');before_databases=[r[0] for r in q.fetchall()]
        assert set(before_databases)=={'postgres','template0','template1',owned['database']}
        q.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',('metodobase_app',));assert q.fetchone() is None
        q.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s',(owned['database'],));assert q.fetchone()[0]==0
        q.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(owned['database'])))
        for role in roles:q.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        q.execute('SELECT datname FROM pg_database ORDER BY datname');after_databases=[r[0] for r in q.fetchall()]
        assert set(after_databases)=={'postgres','template0','template1'}
        q.execute('SELECT rolname FROM pg_roles WHERE rolname=ANY(%s)',(roles+['metodobase_app'],));assert q.fetchall()==[]
        q.execute('SELECT auth_method,error FROM pg_hba_file_rules');hba_rows=q.fetchall()
        assert hba_rows and all(method=='scram-sha-256' and error is None for method,error in hba_rows)
        q.execute('SELECT 1');assert q.fetchone()==(1,)
    c.close()
except Exception as exc:
    # No raw exception, SQL parameters, password or DSN in the receipt.
    (OUT/'pg55484-handoff-partial.json').write_text(json.dumps({'failure_type':type(exc).__name__,'sqlstate':getattr(exc,'pgcode',None),'requires_owned_review':True},indent=2)+'\n')
    raise SystemExit(1)
assert hashlib.sha256(hba.read_bytes()).hexdigest()==hba_hash
receipt={'finished_utc':datetime.now(timezone.utc).isoformat(),'instance_ownership_nonce':pointer['nonce'],
         'pid':1216,'process_identity':actual,'postgres_executable_sha256':pointer['postgres_executable_sha256'],
         'host':'127.0.0.1','port':55484,'data_directory':str(data),'pointer_file':str(BASE/'pg55484-instance-pointer.json'),
         'private_admin_file':pointer['private_admin_file'],'private_admin_format_keys':['host','port','username','password','database','data_dir','private_root'],
         'admin_usage':'Read JSON inside child process, psycopg2.connect host/port/dbname/user/password kwargs; never CLI/output/environment/DSN logging.',
         'dropped_database':owned['database'],'dropped_roles':roles,'databases_after':after_databases,
         'legacy_global_metodobase_app_absent':True,'hba_all_scram_and_unchanged':True,'hba_sha256':hba_hash,
         'known_positive_select1_after_cleanup':True,'instance_left_running_for':'Authorized backend regression test; backend owns final shutdown',
         'other_instances_changed':False,'global_role_or_privileges_altered':False,'private_raw_and_datadir_preserved':True}
with (OUT/'pg55484-handoff.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'handoff_ready':True,'pid':1216,'port':55484,'receipt':str(OUT/'pg55484-handoff.json'),'legacy_global_role_absent':True,'passwords_or_dsns_emitted':False}))
