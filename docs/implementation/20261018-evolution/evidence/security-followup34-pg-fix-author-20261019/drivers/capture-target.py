from pathlib import Path
import copy,hashlib,json,os,sys
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');sys.path.insert(0,str(R));T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-followup34-author-sec-peer-20261019';O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-pg-fix-author-20261019';assert not O.exists();O.mkdir();(O/'.gitattributes').write_bytes(b'* -text\n');sha=lambda b:hashlib.sha256(b).hexdigest()
from tests.isolation import prepare_environment,block_external_sockets
root=prepare_environment(discard_inherited=True);block_external_sockets();profile=json.loads((T/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes());os.environ.update(profile);os.environ['FOLLOWUP34_PRIVATE_LEASES']=str(P/'leases')
from tests.followup34_fixtures import owned_database,PREVIOUS,signature
from tests.integration_schema_migrations import run_migration
from alembic.migration import MigrationContext
from alembic.operations import Operations
import importlib
migration=importlib.import_module('web.database.alembic.versions.20261019_followup_tasks');path=R/'web/database/alembic/schema_targets/20261019_followup_tasks_postgresql.json';old_raw=path.read_bytes();assert sha(old_raw)=='a33dfac87bf379975bbcbfcbb733bc7bd978b7ce122c596d2a8d8710efd14880';old=json.loads(old_raw)
with owned_database('postgresql',root/'own-capture34')as(url,engine):
 run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
 with engine.begin()as db:
  with Operations.context(MigrationContext.configure(db)):migration.create_tables()
  captured=signature(db)
raw=(json.dumps(captured,sort_keys=True,indent=2)+'\n').encode();private=P/'target34-captured.RAW.json'
with private.open('xb')as out:out.write(raw)
inverse=copy.deepcopy(captured);guard=next(x for x in inverse['followup_security']['functions']if x[0]=='r34_event_guard');assert guard[8].count('FOR SHARE NOWAIT;')==1;guard[8]=guard[8].replace('FOR SHARE NOWAIT;','FOR SHARE;',1);assert inverse==old and (json.dumps(inverse,sort_keys=True,indent=2)+'\n').encode()==old_raw
assert path.read_bytes()==old_raw;path.write_bytes(raw)
(O/'target34-capture-inverse.STRUCTURAL.json').write_bytes((json.dumps({'previous_target_SHA256':sha(old_raw),'new_target_SHA256':sha(raw),'actual_own_PostgreSQL_capture':True,'own_capture_closed_before_target_install':True,'only_changed_signature':'r34_event_guard prosrc CLIENT FOR SHARE adds NOWAIT','full_JSON_inverse_exact':True,'full_byte_inverse_exact':True,'predecessor22_to33_targets_changed':False,'new_public_SQL_RPC_or_definer':False},indent=2)+'\n').encode())
print(json.dumps({'new_targetPG34_SHA256':sha(raw),'full_inverse_exact':True,'own_UUIDs':[{'database':v['database'],'state':v['state'],'oid':v.get('oid'),'sessions_before_drop':v.get('sessions_before_drop')}for v in [json.loads(p.read_bytes())for p in(P/'leases').glob('*.json')]]}))
