"""Additive recovery photo; original failed launcher and created lease remain immutable."""
from pathlib import Path
import importlib.util
import json
import sys
import hashlib
ROOT=Path('F:/mb-qa-native37-20261020')
TASK=Path(__file__).resolve().parents[1]
P=TASK/'private'
sys.path.insert(0,str(ROOT))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
launch=module('native37_launch_recovery',ROOT/'tests/e2e/run_native37_qa.py')
launch.TASK=TASK;launch.P=P
lib=module('native37_environment_recovery',ROOT/'tests/e2e/native37_environment_qa.py')
final=launch.inventory('after-manual')
history=[json.loads(path.read_bytes()) for path in sorted(P.glob('*-inventory.json'))]
before=json.loads((P/'before-inventory.json').read_bytes())
node_ids={}
for path in P.glob('*-node-identity.json'):
    row=json.loads(path.read_bytes());node_ids[row['pid']]=row['birth']
owned,rejected=launch.own_chrome_rows(history,node_ids)
statuses=[launch.status(row['pid'],row['birth']) for row in owned]
statuses += [launch.status(pid,birth) for pid,birth in node_ids.items()]
statuses += [launch.status(27404,134369530643760054),launch.status(27324,134369530643879639)]
assert all(row['state'] in {'absent','terminated_exact_process_object','original_absent_PID_reused'} for row in statuses)
def browsers(value):
    return {(r['ProcessId'],r['birth']) for r in value['processes'] if r['Name'].lower() in {'chrome.exe','msedge.exe'} and r['birth'] is not None}
def chrome(value):
    return {(r['ProcessId'],r['birth']) for r in value['processes'] if r['Name'].lower()=='chrome.exe' and r['birth'] is not None}
def port(value):
    return {(r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in value['listeners'] if r['LocalPort']==8776}
foreign_missing=browsers(before)-browsers(final)
new_chrome=chrome(final)-chrome(before)
assert not foreign_missing and not new_chrome
assert port(before)==port(final)
assert not any(r['LocalPort']==8802 for r in final['listeners'])
manual=json.loads((P/'manual-owned-close.json').read_bytes())
assert manual['ordinary_DROP_after_zero_sessions'] and manual['fresh_connection_database_absence'] and manual['fresh_connection_sessions']==0
launch.put('resource-closure-manual.json',{
    'process_statuses':statuses,'owned_Chrome_observed':owned,'rejected_generation_attributions':rejected,
    'owned_Chrome_remaining':[],'foreign_browsers_preserved':True,'foreign_listener8776_preserved':True,
    'own_port8802_closed':True,'ordinary_DROP_after_zero_sessions':True,'fresh_database_absence':True,
    'normal_server_exit':False,'manual_server_closure_after_TimeoutExpired':True,
    'original_created_lease_preserved':True,'no_FORCEDROP_no_foreign_cancellation':True})
after=lib.photograph(ROOT,TASK,'after-manual',launch.PROFILE,launch.NODE,launch.CHROME,launch.DEPS)
lib.pipcheck(ROOT,TASK,'after-manual')
initial=json.loads((P/'before-full.json').read_bytes())
stable={key:initial[key]==after[key] for key in initial}
assert all(stable.values()),[key for key,value in stable.items() if not value]
launch.put('recovery-after-summary.json',{
    'source_head':initial['head'],'stable':stable,'source_files':len(initial['source']),
    'packages':len(initial['packages']),'installed_files':len(initial['installed']),'Node_files':len(initial['node_files']),
    'pip_before':0,'pip_after':0,'owned_Chrome_observed':len(owned),'own_Node_drivers':len(node_ids),
    'foreign_browsers_preserved':True,'foreign_listener8776_preserved':True,'own_port8802_closed':True,
    'ordinary_DROP_after_zero_sessions':True,'fresh_database_absence':True,'normal_server_exit':False,
    'combined33_gate':'REJECTED','original_MFA_groups_passed':15,'new_groups_completed':0,
    'new_groups_not_accepted':18,'no_new_trial_or_retry':True})
print(json.dumps({'source_head':initial['head'],'all_photographed_fields_stable':True,
    'source_files':len(initial['source']),'packages':len(initial['packages']),'installed_files':len(initial['installed']),
    'Node_files':len(initial['node_files']),'owned_Chrome_observed':len(owned),'all_owned_processes_closed':True,
    'foreign_browsers_and_8776_preserved':True,'port8802_closed':True,'database_absent':True,'pip_after':0,
    'normal_server_exit':False}))
