from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('F:/mb-qa-native37-20261020');MAIN='8d6b18521c719ff789ebd32c493457b6810b2b48'
def sha(data):return hashlib.sha256(data).hexdigest()
def tree(ref):
 raw=subprocess.check_output(['git','--no-replace-objects','ls-tree','-r','-z',ref,'--','api','web','core','config','src','utils'],cwd=ROOT)
 result={}
 for row in raw.split(b'\0'):
  if row:
   metadata,name=row.split(b'\t',1);mode,kind,oid=metadata.decode().split();result[name.decode()]={'mode':mode,'type':kind,'oid':oid}
 return result
ours=tree('HEAD');main=tree(MAIN);assert ours==main and len(ours)==444
entries={
 'tests/e2e/run_native37_qa_v2.py':'Windows host launcher; explicit SQL ACK then Chrome ACK; serial11+4+18, failclosed closure',
 'tests/e2e/native37_postgres_server_qa_v2.py':'Actual current37 restricted-PG hostfixture with private bounded shutdown observations',
 'tests/e2e/native37_account_notifications_qa_v2.cjs':'Own18 new driver; one literal wait framing change plus private frame observer',
 'tests/e2e/native37_environment_qa.py':'Readonly full source/environment snapshots and pipcheck',
 'tests/e2e/native37_session_qa.cjs':'Own actual auth/MFA/cookie setup, factor RAM only',
 'tests/e2e/browser_native_compat37_qa.cjs':'Executable companion37; reads chosen original MFA driver and browser_compat31 function framing',
 'tests/e2e/browser_compat31.cjs':'Read as source text for balanced/assertion framing; entire VM runner not executed here',
 'tests/e2e/browser_native_session31.cjs':'Injected require by companion37 and own session; real MFA/browser helpers',
 'tests/e2e/mfa31_login.cjs':'Read and compiled by browser_native_session31 and native37_session; actual enrollment/recovery helper',
 'tests/e2e/mfa_ui_browser.cjs':'Original11 replay; compiled via companion37 with business assertions unchanged',
 'tests/e2e/mfa_personal_browser.cjs':'Original4 replay; compiled via companion37 with business assertions unchanged',
 'tests/e2e/mobile_heading37_qa.cjs':'Actual require from own18 geometry oracle; no synthetic geometry-driver run',
 'tests/account_security37_owned.py':'Immutable owned UUID CREATE/normalDROP primitive',
 'tests/isolation.py':'Explicit private environment and loopback network fence',
 'tests/integration_schema_migrations.py':'run_migration imported; pytest module dependency is host test tooling only',
 'tests/integration_provider_subjects.py':'application_engine imported; no test collection or unrelated test execution',
 'tests/__init__.py':'Package binding for host test helper imports',
 'db_bootstrap.py':'Explicit revision37 migration subprocess entry',
 'alembic.ini':'Migration configuration; env/versions/contracts are in full web runtime tree',
}
provenance={
 'tests/e2e/native37_account_notifications_qa.cjs':'Immutable original rejected own18 source; not new executable',
 'tests/e2e/native37_postgres_server_qa.py':'Immutable original first fixture',
 'tests/e2e/run_native37_qa.py':'Immutable original first launcher',
 'tests/e2e/mobile_heading37_geometry.cjs':'Separate synthetic DOM mobile16 before/after gate, not imported by native33',
 'tests/e2e/browser_native_compat31.cjs':'Historical derivation reference; current37 executable is companion37',
}
def binding(name,scope):
 path=ROOT/name;assert path.is_file() and not path.is_symlink();raw=path.read_bytes()
 stored=subprocess.run(['git','cat-file','blob','HEAD:'+name],cwd=ROOT,capture_output=True)
 blob=stored.stdout if stored.returncode==0 else raw
 return {'scope':scope,'raw_sha256':sha(raw),'bytes':len(raw),'Git_blob_sha256':sha(blob),
  'Git_blob_oid':subprocess.check_output(['git','hash-object','--stdin'],input=blob,cwd=ROOT,text=False).decode().strip(),
  'RAW_equals_Git':raw==blob,'Git_binding':'HEAD blob' if stored.returncode==0 else 'new RAW expected Git blob; verify after selective commit'}
manifest={'contract':'QA_NATIVE37_REENSAYO_CONTRATO.md','product_reference':MAIN,
 'runtime_mode_path_blob_exact_against_Main':True,'runtime_files':len(ours),
 'executed_direct_and_transitive_helpers':{name:binding(name,scope) for name,scope in entries.items()},
 'provenance_only_not_executed':{name:binding(name,scope) for name,scope in provenance.items()},
 'runtime_complete':{name:{**value,'raw_sha256':sha((ROOT/name).read_bytes())} for name,value in ours.items()},
 'dynamic_edges':[
  ['run_native37_qa_v2.py','native37_postgres_server_qa_v2.py','subprocess hostfixture'],
  ['run_native37_qa_v2.py','browser_native_compat37_qa.cjs','subprocess chooses original MFA11 then personal4'],
  ['run_native37_qa_v2.py','native37_account_notifications_qa_v2.cjs','subprocess own18 after original15'],
  ['browser_native_compat37_qa.cjs','browser_compat31.cjs','source-text balanced framing only'],
  ['browser_native_compat37_qa.cjs','mfa_ui_browser.cjs / mfa_personal_browser.cjs','selected original read/compile'],
  ['browser_native_compat37_qa.cjs','browser_native_session31.cjs','require inserted only by existing explicit companion'],
  ['browser_native_session31.cjs / native37_session_qa.cjs','mfa31_login.cjs','source read/compile original helper'],
  ['native37_account_notifications_qa_v2.cjs','mobile_heading37_qa.cjs','actual required geometry oracle'],
  ['native37_postgres_server_qa_v2.py','db_bootstrap.py','run_migration explicit revision37 subprocess'],
 ],
 'external_readonly_dependencies':{'Node_modules':'157 existing files, playwright-core and axe-core; hash map in preflight',
  'WEB_python':'92 existing distributions and 8084 installed-file scope; host includes pytest, not production image',
  'Python_Node_Chrome_PG_tools_profile':'Pinned by before/after full photograph; no install/copy'},
 'manifest_self_hash':'Bound by outer freeze after source commit; not recursively embedded',
 'not_executed_at_preparation':['PG','Chrome','HTTP services','providers','Redis','VM','images','Actions'],
}
target=ROOT/'tests/e2e/native37_transitive_qa.json';assert not target.exists();target.write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
print(json.dumps({'runtime_files':len(ours),'direct_transitive_helpers':len(entries),'provenance_only':len(provenance),
 'manifest_sha256':sha(target.read_bytes()),'all_runtime_mode_path_blob_exact':True}))
