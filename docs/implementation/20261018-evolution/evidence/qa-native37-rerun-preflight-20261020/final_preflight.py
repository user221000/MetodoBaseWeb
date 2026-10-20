from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys
ROOT=Path('F:/mb-qa-native37-20261020');PREP=Path(__file__).resolve().parent
TASK=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-account37-author-pg-native-replay-qa-20261020');P=TASK/'private'
PROFILE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe');DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
sha=lambda data:hashlib.sha256(data).hexdigest()
sys.path.insert(0,str(ROOT));spec=importlib.util.spec_from_file_location('native37_final_env',ROOT/'tests/e2e/native37_environment_qa.py');lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
def put(name,value):
 with (P/name).open('xb') as stream:stream.write(value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode())
assert not list((TASK/'leases').iterdir()) and not (P/'startup.json').exists()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head=='cd3d696711a5355df562ef35d883486d7d320d1c'
manifest=json.loads((ROOT/'tests/e2e/native37_transitive_qa.json').read_bytes())
for name,row in manifest['executed_direct_and_transitive_helpers'].items():
 assert sha((ROOT/name).read_bytes())==row['raw_sha256']
 assert sha(subprocess.check_output(['git','cat-file','blob','HEAD:'+name],cwd=ROOT))==row['Git_blob_sha256']
assert manifest['runtime_files']==444
before=lib.photograph(ROOT,TASK,'preparation-before',PROFILE,NODE,CHROME,DEPS);lib.pipcheck(ROOT,TASK,'preparation-before')
compilations={}
for name in ('mfa_ui_browser','mfa_personal_browser'):
 env=os.environ.copy();env['NATIVE31_BROWSER_OUTPUT']=str(P/('compile-only-'+name));env.pop('NATIVE31_PRODUCER_WITNESS',None)
 result=subprocess.run([str(NODE),'tests/e2e/browser_native_compat37_qa.cjs',name,'--compile-only'],cwd=ROOT,env=env,capture_output=True)
 put(name+'-compile.stdout',result.stdout);put(name+'-compile.stderr',result.stderr);assert result.returncode==0
 value=json.loads(result.stdout);assert value['parsed'] is True
 compilations[name]={'parsed':True,'source_sha256':sha((ROOT/'tests/e2e'/ (name+'.cjs')).read_bytes()),
  'stdout_sha256':sha(result.stdout),'business_assertions_before_existing_normative_framing':value['browser_session_composition']['assertion_calls_preserved_before_normative_changes'],
  'no_native_execution':True,'no_producer_witness_fabricated':True}
after=lib.photograph(ROOT,TASK,'preparation-after',PROFILE,NODE,CHROME,DEPS);lib.pipcheck(ROOT,TASK,'preparation-after')
stable={key:before[key]==after[key] for key in before};assert all(stable.values())
assert sha(PROFILE.read_bytes())=='1526482e15f5e31a4248868e77a609af536f6dfbbf2b04959e7b14d521519f02'
preflight={'source_head':head,'source_RAW_sha256':before['source'],'packages':before['packages'],
 'installed_map_sha256':sha(json.dumps(before['installed'],sort_keys=True,separators=(',',':')).encode()),
 'profile_sha256':sha(PROFILE.read_bytes()),
 'launcher_sha256':sha((ROOT/'tests/e2e/run_native37_qa_v2.py').read_bytes()),
 'fixture_sha256':sha((ROOT/'tests/e2e/native37_postgres_server_qa_v2.py').read_bytes()),
 'driver_sha256':sha((ROOT/'tests/e2e/native37_account_notifications_qa_v2.cjs').read_bytes()),
 'transitive_manifest_sha256':sha((ROOT/'tests/e2e/native37_transitive_qa.json').read_bytes()),
 'contract_sha256':sha((ROOT/'docs/implementation/20261018-evolution/QA_NATIVE37_REENSAYO_CONTRATO.md').read_bytes()),
 'product_reference':'8d6b18521c719ff789ebd32c493457b6810b2b48','runtime_blobs_exact':444,
 'expected_groups':[11,4,18],'original15_are_replay':True,'new18_not_accepted_by_preparation':True,
 'planned_UUID_count_this_phase':1,'cumulative_UUID_count_after_future_CREATE':2,
 'database_created':False,'SQL_authorization':False,'Chrome_authorization':False,
 'expected_schema':'20261020_account_security','expected_ORM':41,'expected_physical':42,'expected_FORCE_RLS':32,
 'role_flags_and_owner_membership_expected':[False]*5,'restricted_nonowner_expected':True,
 'pool_size_expected':5,'max_overflow_expected':0,'port':8802,'loopback_only':True,
 'normal_DROP_zero_sessions_fresh_absence_required':True,'new_diagnostics_do_not_change_cancellation_policy':True,
 'no_services_executed':True,'compile_only':compilations,'all_preparation_fields_stable':stable}
target=TASK/'native-preflight.json'
with target.open('xb') as stream:stream.write((json.dumps(preflight,indent=2)+'\n').encode())
put('preparation-final-summary.json',{'source_head':head,'source_files':len(before['source']),
 'packages':len(before['packages']),'installed_files':len(before['installed']),'Node_files':len(before['node_files']),
 'stable':stable,'pip_before':0,'pip_after':0,'native_preflight_sha256':sha(target.read_bytes()),
 'planned_UUIDs':1,'cumulative_UUIDs_after_future_CREATE':2,'database_created':False,'Chrome_started':False,
 'compile_only':compilations,'offline_checks_producer':str(PREP/'private/offline-summary.json'),
 'offline_checks_scope':'Source1320 before adding maintained transitive JSON only; identical three V2 sources and runtime',
 'SQL_Chrome_need_explicit_ROOT_ACK':True})
print(json.dumps({'source_head':head,'native_preflight_sha256':sha(target.read_bytes()),
 'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),
 'Node_files':len(before['node_files']),'all_fields_stable':True,'pip':0,'database_created':False,'Chrome_started':False}))
