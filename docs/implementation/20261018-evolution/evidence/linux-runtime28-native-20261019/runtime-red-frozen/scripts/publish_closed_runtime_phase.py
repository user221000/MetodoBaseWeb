from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import quote
import hashlib,json
BASE=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
DEST=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-runtime28-native-20261019/runtime-red-frozen')
private=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-runtime28-roles-private-lwdcn5wd')
payload=json.loads((private/'private.json').read_text())
pointer=json.loads((BASE/'pg55484-instance-pointer.json').read_text())
admin=json.loads(Path(pointer['private_admin_file']).read_text())
secrets=list(payload['runtime_stdin'].values())+list(payload['passwords'].values())+[admin['password']]
secrets=[s for s in secrets if isinstance(s,str) and len(s)>8]
secret_bytes=[v.encode() for s in secrets for v in [s,quote(s,safe='')]]
def copy(source,target):
    assert source.is_file() and not source.is_symlink()
    raw=source.read_bytes()
    assert all(s not in raw for s in secret_bytes),'Private material found; no publication'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==raw
    else:
        with target.open('xb') as f:f.write(raw)
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
copied={}
for directory in ['network-executed','network-retry-v2','network-retry-v3-target55484','network-target55484','pg55484-setup','runtime','closure','scripts']:
    for p in sorted((BASE/directory).rglob('*')):
        if not p.is_file() or p.suffix=='.tar':continue
        relative=p.relative_to(BASE)
        copied[relative.as_posix()]=copy(p,DEST/relative)
for name in ['pg55483-readonly.json','pg55484-instance-pointer.json','producer-v3-preparation-errata.json']:
    copied[name]=copy(BASE/name,DEST/name)
copied['roles-producer-sanitized-report.json']=copy(private/'sanitized-report.json',DEST/'roles-producer-sanitized-report.json')
provenance=[]
for raw,public in [('migrate.stdout.guest.raw.log','migrate.stdout.sanitized.log'),('migrate.stderr.guest.raw.log','migrate.stderr.sanitized.log')]:
    rb=(private/raw).read_bytes();pb=(BASE/'runtime'/public).read_bytes()
    provenance.append({'private_raw_path':str(private/raw),'private_raw_sha256':hashlib.sha256(rb).hexdigest(),
                       'private_raw_bytes':len(rb),'sanitized_derivative_file':'runtime/'+public,
                       'sanitized_derivative_sha256':hashlib.sha256(pb).hexdigest(),
                       'derivative_equals_raw_bytes':rb==pb,'public_label':'SANITIZED derivative; private RAW retained'})
receipt={'published_utc':datetime.now(timezone.utc).isoformat(),'files_copied':len(copied),'copied_files':copied,
         'private_passwords_and_runtime_values_exact_match_checked_absent':True,'private_json_frames_admin_and_raw_logs_not_copied':True,
         'raw_log_provenance':provenance,'actual_private_stdin_attempted_and_product_migration_executed':True,
         'controller_private_stdin_sent_false_is_stale_pre_attempt_journal':True,
         'migration_exit':1,'sqlstate_diagnostic_same_statement':'42501','web_container_created':False,
         'entrypoint_web_main_marker28_migrator_unset_readiness_not_demonstrated':True,
         'qemu_network_proxies_ssh_closed':True,'pg55484_handed_off_to_backend_running':True,
         'native_sec09_symlink_frozen_directories_unchanged':True}
with (DEST/'phase-publication-receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
with (DEST/'.gitattributes').open('x') as f:f.write('* -text\n')
print(json.dumps({'published_phase':str(DEST),'files_copied':len(copied),'private_material_copied':False,'manifest_pending_readme':True}))
