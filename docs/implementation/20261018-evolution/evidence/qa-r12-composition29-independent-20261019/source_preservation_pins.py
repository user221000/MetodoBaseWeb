"""Authenticate backend/UI raw freezes and explicit composition/test deltas."""
from zipfile import ZipFile
from support import *

EVI=ROOT/'docs/implementation/20261018-evolution/evidence'
path=EVI/'backend-r12-api-final-freeze.json'
freeze=json.loads(path.read_bytes());freeze_sha=sha(path.read_bytes().replace(b"\r\n",b"\n"))
assert freeze_sha.startswith('22d2259a')
assert git('show','e6924e192e99850a1044602bc87b2d2c10bae14b:'+path.relative_to(ROOT).as_posix()).replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n')
archive_path=Path(r'C:/Users/Consu/AppData/Local/Temp')/freeze['raw_archive_name']
assert sha(archive_path.read_bytes())==freeze['raw_archive_sha256']=='d574fd0b760f2de9021ccf464c946ee52f7e781864854fa949d7dd224c1de673'
paths=freeze['product_files']+freeze['test_files'];assert len(paths)==23
composition={'api/app.py','web/main_web.py','web/middleware/security_headers.py','tests/integration_client_link_http.py'}
records={}
with ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    for name in paths:
        raw=archive.read(name);blob=git('show',API+':'+name);current=git('show',HEAD+':'+name);work=(ROOT/name).read_bytes()
        assert sha(raw)==freeze['raw_sources'][name] and sha(blob)==freeze['git_lf_sha256'][name]
        assert raw.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n')
        assert work.replace(b'\r\n',b'\n')==current.replace(b'\r\n',b'\n')
        if name not in composition:assert current==blob
        else:
            delta=git('diff',API,HEAD,'--',name)
            destination=OUT/('composition-'+name.replace('/','_')+'.diff')
            if destination.exists():assert destination.read_bytes()==delta
            else:destination.write_bytes(delta)
        records[name]={'raw_sha256':sha(raw),'author_Git_LF_sha256':sha(blob),'composition_Git_sha256':sha(current),
                       'own_checkout_sha256':sha(work),'explicit_composition_delta':name in composition}
before=ast.parse(git('show',API+':tests/integration_client_link_http.py'))
after=ast.parse((ROOT/'tests/integration_client_link_http.py').read_bytes())
function=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='test_privacy_headers_survive_wrong_method_and_missing_page')
parameters=function.decorator_list[0].args[1]
extra=[n for n in parameters.elts if ast.literal_eval(n)==('/auth/accept-client-link','post')]
assert len(extra)==1;parameters.elts.remove(extra[0])
assert isinstance(function.body[1],ast.If) and len(function.body[1].orelse)==1
function.body[1]=function.body[1].orelse[0]
assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
# Exactly one explicit historical28 revision keyword; predecessor contract remains unchanged.
before=ast.parse(git('show','6ec3f04:tests/integration_account_recovery_migrations.py'))
after=ast.parse((ROOT/'tests/integration_account_recovery_migrations.py').read_bytes())
removed=0
for node in ast.walk(after):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='verify_runtime_schema':
        selected=[kw for kw in node.keywords if kw.arg=='expected_revision' and isinstance(kw.value,ast.Name) and kw.value.id=='REVISION']
        # Existing historical calls already used a PREVIOUS constant; only new literal is the reviewed pin.
        for keyword in selected:node.keywords.remove(keyword);removed+=1
assert removed==1 and ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
historical=[name for name in git('ls-tree','-r','--name-only',MAIN_BASE,'web/database/alembic/schema_targets').decode().splitlines() if name.endswith('.json')]
assert len(historical)==16
for name in historical:assert git('show',MAIN_BASE+':'+name)==git('show',HEAD+':'+name)
core_paths=['web/database/models.py','web/database/member_link_policy_v1.py','web/database/member_link_projection_v1.py',
 'web/database/alembic/member_link_ddl/20261019_postgresql.sql','web/database/alembic/schema_targets/20261019_client_account_links_postgresql.json',
 'web/database/alembic/schema_targets/20261019_client_account_links_sqlite.json']
for name in core_paths:assert git('show',CORE+':'+name)==git('show',HEAD+':'+name)
for name in ['tests/integration_diary_restore_review.py','tests/integration_recovery28_restore_review.py',
             'web/database/alembic/schema_contract_v1.py','web/database/alembic/security_contract_v1.py','web/database/tenant_policy.py']:
    assert git('show',MAIN_BASE+':'+name)==git('show',HEAD+':'+name)
ui_layers=['r12-ui/consumer-freeze.json','r12-export/source-freeze.json','r12-publication-cas/source-freeze.json']
latest={};layers=[]
for relative in ui_layers:
    metadata=json.loads((EVI/relative).read_bytes());layers.append({'file':relative,'sha256':sha((EVI/relative).read_bytes())})
    for name,value in metadata['sources'].items():latest[name]={'layer':relative,**value}
ui=[]
for name,expected in latest.items():
    blob=git('show',HEAD+':'+name)
    assert sha(blob)==expected['lf_sha256']
    assert (ROOT/name).read_bytes().replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n')
    ui.append({'path':name,'latest_layer':expected['layer'],'Git_LF_sha256':sha(blob)})
save('source-preservation.json',{'head':HEAD,'backend_freeze_sha256':freeze_sha,'backend_RAW23':records,
 'backend_RAW_archive_sha256':freeze['raw_archive_sha256'],'explicit_composition_paths':sorted(composition),
 'HTTP_test_inverse_delta_exact_author72_AST':True,'historical28_pin_inverse_delta_exact_6ec_AST':True,
 'historical16_targets22_to28_exact':historical,'core_final6ec_paths_exact':core_paths,
 'restores27_28_and_v1_contracts_unchanged':True,'UI_freeze_layers':layers,'latest_UI_sources_exact':ui,
 'scope':'Source authentication only. No500 security acceptance, HTTP/restore/browser/API29 acceptance from hashes alone.'})
print(json.dumps({'backend_RAW_sources':23,'UI_sources':len(ui),'historical_targets':16,'preservation':'PASS'}))
